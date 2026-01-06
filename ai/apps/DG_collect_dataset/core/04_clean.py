#!/usr/bin/env python3
# File: /home/seanf/deadlygraphics/ai/apps/DG_collect_dataset/core/04_clean.py
import os
import sys
import shutil
import cv2
import torch
import numpy as np
from pathlib import Path
from tqdm import tqdm
from simple_lama_inpainting import SimpleLama
import easyocr

# --- VENV ENFORCEMENT ---
def _ensure_venv():
    venv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".venv")
    if not hasattr(sys, 'real_prefix') and not os.environ.get("VIRTUAL_ENV"):
        venv_python = os.path.join(venv_path, "bin", "python")
        if os.path.exists(venv_python):
            os.execv(venv_python, [venv_python] + sys.argv)
    # NOTE: Do NOT re-exec the venv at import time (this causes the main
    # pipeline to be restarted when this module is imported). The venv
    # re-exec is only necessary when this file is run directly as a script.

import utils

# --- CONFIGURATION ---
DEVICE_BOOL = True if torch.cuda.is_available() else False
DEVICE_STR = 'cuda' if DEVICE_BOOL else 'cpu'

# High pass count to verify progressive cleaning
MAX_PASSES = 12 

print(f"⏳ [Init] Loading AI Models on {DEVICE_STR}...")

# 1. LOAD MODELS
simple_lama = SimpleLama()
reader = easyocr.Reader(['en'], gpu=DEVICE_BOOL)

# 2. SETUP FACE SHIELD
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

def get_face_shield_mask(img_bgr):
    """
    Creates a mask where faces are White (255).
    """
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
    
    shield = np.zeros(img_bgr.shape[:2], dtype=np.uint8)
    
    for (x, y, w, h) in faces:
        # Protect slightly more than just the box to save glasses/hair
        pad_x = int(w * 0.05)
        pad_y = int(h * 0.05)
        
        pt1 = (max(0, x - pad_x), max(0, y - pad_y))
        pt2 = (min(img_bgr.shape[1], x + w + pad_x), min(img_bgr.shape[0], y + h + pad_y))
        
        cv2.rectangle(shield, pt1, pt2, 255, -1)
        
    return shield

def enhance_contrast_for_detection(img_bgr):
    """
    Applies CLAHE (Contrast Limited Adaptive Histogram Equalization) to 
    make faint watermark residues pop out for the detector.
    """
    lab = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    
    # High clipLimit (3.0) forces hidden details to become visible
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
    cl = clahe.apply(l)
    
    limg = cv2.merge((cl,a,b))
    return cv2.cvtColor(limg, cv2.COLOR_LAB2BGR)

def get_text_mask(img_bgr, aggressive=False):
    """
    Uses EasyOCR to find text regions. 
    If 'aggressive' is True, it checks the contrast-boosted image too.
    """
    mask = np.zeros(img_bgr.shape[:2], dtype=np.uint8)
    
    # 1. Standard Detection
    results = reader.readtext(img_bgr, low_text=0.2, text_threshold=0.4)
    
    # 2. Aggressive Detection (Ghost Hunting)
    # Use the enhanced image to find what the first pass missed
    if aggressive:
        enhanced_img = enhance_contrast_for_detection(img_bgr)
        results_enhanced = reader.readtext(enhanced_img, low_text=0.25, text_threshold=0.35)
        results.extend(results_enhanced)

    for (bbox, text, prob) in results:
        try:
            pts = np.array(bbox, dtype=np.int32)
            cv2.fillPoly(mask, [pts], 255)
        except Exception:
            continue

    if cv2.countNonZero(mask) > 0:
        kernel = np.ones((7,7), np.uint8)
        mask = cv2.dilate(mask, kernel, iterations=2)
        
    return mask

def process_image(img, pass_num):
    # Enable aggressive ghost hunting for passes 2 and beyond (index 1+)
    is_aggressive = (pass_num > 0)
    
    # 1. Find Text
    text_mask = get_text_mask(img, aggressive=is_aggressive)
    
    # 2. Find Face Shield
    face_mask = get_face_shield_mask(img)
    
    # 3. Apply Shield (Text - Face)
    safe_mask = cv2.bitwise_and(text_mask, cv2.bitwise_not(face_mask))
    
    # Safety Checks
    if cv2.countNonZero(safe_mask) == 0:
        return img
    
    total_pixels = img.shape[0] * img.shape[1]
    if cv2.countNonZero(safe_mask) / total_pixels > 0.25:
        # If mask is huge, it's likely a mistake. Skip this pass.
        return img

    # 4. Inpaint
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    try:
        result_rgb = simple_lama(img_rgb, safe_mask)
        return cv2.cvtColor(np.array(result_rgb), cv2.COLOR_RGB2BGR)
    except Exception as e:
        print(f"Error inpaint: {e}")
        return img

def run(slug):
    path = utils.get_project_path(slug)
    validate_dir = path / "03_validate"
    clean_dir = path / "04_clean"

    # Reset clean directory
    if clean_dir.exists(): shutil.rmtree(clean_dir)
    clean_dir.mkdir(parents=True, exist_ok=True)

    # Create folders for each pass (but don't save intermediate results)
    # Just keep for tracking if needed later
    pass_dirs = []
    for i in range(1, MAX_PASSES + 1):
        pass_dir = clean_dir / f"pass_{i:02d}"
        pass_dir.mkdir(exist_ok=True)
        pass_dirs.append(pass_dir)

    if not validate_dir.exists():
        print(f"❌ Error: Validation folder missing")
        return

    files = [f for f in os.listdir(validate_dir) if f.lower().endswith(('.jpg', '.png'))]
    
    print(f"🚀 [04_clean] {MAX_PASSES}-Pass Progressive Cleaning for {slug}...")
    
    for f_name in tqdm(files, desc="Processing"):
        src_path = validate_dir / f_name
        img = cv2.imread(str(src_path))
        if img is None: continue

        # Enforce Square check
        if img.shape[0] != img.shape[1]:
            continue
        
        working_img = img.copy()
        
        for pass_num in range(MAX_PASSES):
            # Try to process
            new_img = process_image(working_img, pass_num)

            # Ensure dims match (safety for OpenCV saving)
            if new_img.shape != img.shape:
                new_img = cv2.resize(new_img, (img.shape[1], img.shape[0]))

            # Update working image for next pass (no per-pass output printing)
            working_img = new_img

        # After all passes, save the final cleaned image into the root clean_dir
        final_out = clean_dir / f_name
        cv2.imwrite(str(final_out), working_img)
    
    print(f"✅ Clean Complete: All images processed through {MAX_PASSES} passes")

if __name__ == "__main__":
    # Only enforce venv re-exec when this file is executed directly.
    _ensure_venv()

    if len(sys.argv) > 1:
        run(sys.argv[1])
    else:
        print("Usage: python core/04_clean.py <slug>")