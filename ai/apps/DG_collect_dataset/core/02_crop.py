import os
import sys
import cv2
import numpy as np
from pathlib import Path
from tqdm import tqdm
from insightface.app import FaceAnalysis

# --- BOOTSTRAP ---
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)
import utils

def get_crop_coords(img_shape, bbox, mode="face"):
    h, w, _ = img_shape
    x1, y1, x2, y2 = map(int, bbox)
    
    face_cx, face_cy = (x1 + x2) // 2, (y1 + y2) // 2
    fw, fh = x2 - x1, y2 - y1

    if mode == "face":
        # Face: Hair-to-Chin (Shift UP)
        size = int(max(fw, fh) * 1.6)
        final_cy = int(face_cy - (fh * 0.15))
        final_cx = face_cx
    else:
        # Body: Upper Third (Shift DOWN)
        size = int(max(fw, fh) * 6.0)
        size = min(size, min(h, w))
        shift_amount = int(size * 0.20)
        final_cy = face_cy + shift_amount
        final_cx = face_cx

    # Ensure square stays within image bounds
    size = min(size, h, w)
    half = size // 2
    
    final_cy = max(half, min(final_cy, h - half))
    final_cx = max(half, min(final_cx, w - half))

    ny1, ny2 = final_cy - half, final_cy + half
    nx1, nx2 = final_cx - half, final_cx + half

    return int(ny1), int(ny2), int(nx1), int(nx2)

def force_center_square(img):
    """
    Fallback: Creates a perfect square crop from the center of the image.
    Used when no face is detected to ensure dataset consistency.
    """
    h, w, _ = img.shape
    size = min(h, w)
    
    cy, cx = h // 2, w // 2
    half = size // 2
    
    # Calculate coords
    y1, y2 = cy - half, cy + half
    x1, x2 = cx - half, cx + half
    
    return img[y1:y2, x1:x2]

def run(slug):
    path = utils.get_project_path(slug)
    in_dir = path / utils.DIRS['scrape']
    out_dir = path / utils.DIRS['crop']
    
    if out_dir.exists():
        import shutil
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"✂️  [02_crop] Running logic: Face (Hair-to-Chin) & Body (Upper Third)...")
    
    try:
        app = FaceAnalysis(name='buffalo_l', root='/mnt/c/AI/models/insightface')
        app.prepare(ctx_id=0, det_size=(640, 640))
    except Exception as e:
        print(f"❌ InsightFace Error: {e}")
        return

    files = sorted([f for f in os.listdir(in_dir) if f.lower().endswith(('.jpg', '.png', '.jpeg'))])
    
    count = 0
    for f in tqdm(files, desc="Cropping"):
        img = cv2.imread(str(in_dir / f))
        if img is None: continue

        faces = app.get(img)
        base_name = os.path.splitext(f)[0]

        # --- FALLBACK LOGIC ---
        if not faces:
            # FIX: If no face found, force a Center Square Crop.
            # Never save a non-square image.
            square_img = force_center_square(img)
            cv2.imwrite(str(out_dir / f"body_{base_name}.jpg"), square_img)
            count += 1
            continue

        primary = max(faces, key=lambda x: (x.bbox[2]-x.bbox[0]) * (x.bbox[3]-x.bbox[1]))

        # 1. Body Crop
        by1, by2, bx1, bx2 = get_crop_coords(img.shape, primary.bbox, "body")
        cv2.imwrite(str(out_dir / f"body_{base_name}.jpg"), img[by1:by2, bx1:bx2])

        # 2. Face Crop
        fy1, fy2, fx1, fx2 = get_crop_coords(img.shape, primary.bbox, "face")
        cv2.imwrite(str(out_dir / f"face_{base_name}.jpg"), img[fy1:fy2, fx1:fx2])
        
        count += 2

    print(f"✅ Generated {count} images in {out_dir}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        run(sys.argv[1])