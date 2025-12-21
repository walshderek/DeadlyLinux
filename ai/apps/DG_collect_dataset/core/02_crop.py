
import sys
import os
import cv2
import numpy as np
from PIL import Image, ImageOps
import utils

# Use insightface for face detection
from insightface.app import FaceAnalysis

# Initialize insightface app (global for performance)
face_app = FaceAnalysis()
face_app.prepare(ctx_id=0 if cv2.cuda.getCudaEnabledDeviceCount() > 0 else -1)

# GPU check - warn but don't fail (WSL doesn't have direct GPU access)
try:
    import tensorflow as tf
    gpus = tf.config.list_physical_devices('GPU')
    if not gpus:
        print("⚠️  WARNING: GPU not detected. Running on CPU (slow).")
        print("   For GPU acceleration, run this pipeline in Windows PowerShell instead.")
except:
    pass

def run(slug):
    path = utils.get_project_path(slug)
    in_dir = path / utils.DIRS['scrape']
    out_dir = path / utils.DIRS['crop']
    out_dir.mkdir(parents=True, exist_ok=True)
    
    files = [f for f in os.listdir(in_dir) if f.lower().endswith(('.jpg', '.png', '.jpeg', '.webp'))]
    print(f"--> [02_crop] Processing {len(files)} images...")
    
    count = 0
    for i, f in enumerate(files):
        try:
            img_path = in_dir / f
            img_pil = Image.open(img_path)
            img_pil = ImageOps.exif_transpose(img_pil).convert("RGB")
            img_np = np.array(img_pil)
            faces = face_app.get(img_np)
            if not faces:
                continue
            # Use the largest face
            face = max(faces, key=lambda x: x.bbox[2]*x.bbox[3])
            x1, y1, x2, y2 = [int(v) for v in face.bbox]
            # Add 20% margin to each side, then make square crop centered on face
            w = x2 - x1
            h = y2 - y1
            margin = int(0.2 * max(w, h))
            # Center of the face bbox
            cx = (x1 + x2) // 2
            cy = (y1 + y2) // 2
            # Side length for square crop
            side = max(w, h) + 2 * margin
            # Calculate square crop box
            x1s = max(0, cx - side // 2)
            y1s = max(0, cy - side // 2)
            x2s = min(img_np.shape[1], x1s + side)
            y2s = min(img_np.shape[0], y1s + side)
            # Adjust if crop goes out of bounds
            if x2s - x1s != side:
                x1s = max(0, x2s - side)
            if y2s - y1s != side:
                y1s = max(0, y2s - side)
            crop = img_np[y1s:y2s, x1s:x2s]
            crop_pil = Image.fromarray(crop)
            # If still not square (edge case), pad
            if crop_pil.width != crop_pil.height:
                max_side = max(crop_pil.size)
                crop_pil = ImageOps.pad(crop_pil, (max_side, max_side), color=(0,0,0), centering=(0.5, 0.5))
            save_path = out_dir / f"{os.path.splitext(f)[0]}.jpg"
            crop_pil.save(save_path, quality=95)
            count += 1
            if i % 5 == 0:
                print(f"    Cropped {i}/{len(files)}...")
        except Exception as e:
            print(f"[02_crop] Error processing {f}: {e}")
    print(f"--> [02_crop] Cropped {count} faces.")