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
    """
    Calculates square coordinates with specific styling rules.
   
    """
    h, w, _ = img_shape
    x1, y1, x2, y2 = map(int, bbox)
    cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
    fw, fh = x2 - x1, y2 - y1

    if mode == "face":
        size = int(max(fw, fh) * 2.2)
        cy = int(cy + (fh * 0.12))
    else:
        size = int(max(fw, fh) * 6.0)
        size = min(size, min(h, w))

    # Ensure the crop size does not exceed image bounds
    size = min(size, h, w)

    half = size // 2
    # Clamp center so crop stays within image
    cx = max(half, min(cx, w - half))
    cy = max(half, min(cy, h - half))

    ny1, ny2 = cy - half, cy + half
    nx1, nx2 = cx - half, cx + half

    return int(ny1), int(ny2), int(nx1), int(nx2)

def run(slug):
    """
    Dual-Mode Cropping Pass.
    Generates [body_...] and [face_...] square crops using InsightFace.
    """
    path = utils.get_project_path(slug)
    in_dir = path / utils.DIRS['scrape']
    out_dir = path / utils.DIRS['crop']
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"✂️  [02_crop] Loading InsightFace Buffalo_L for {slug}...")
    # Initialize InsightFace with GPU support
    app = FaceAnalysis(name='buffalo_l', root='/mnt/c/AI/models/insightface')
    app.prepare(ctx_id=0, det_size=(640, 640))

    files = sorted([f for f in os.listdir(in_dir) if f.lower().endswith(('.jpg', '.png', '.jpeg'))])
    if not files:
        print(f"❌ No images found in {in_dir}")
        return

    count = 0
    for f in tqdm(files, desc="Dual-Cropping"):
        img = cv2.imread(str(in_dir / f))
        if img is None: continue

        faces = app.get(img)
        base_name = os.path.splitext(f)[0]

        if not faces:
            # Fallback: Copy original as body variant to prevent data loss
            cv2.imwrite(str(out_dir / f"body_{f}"), img)
            count += 1
            continue

        # Rule: Target the most prominent face (largest area)
        primary = max(faces, key=lambda x: (x.bbox[2]-x.bbox[0]) * (x.bbox[3]-x.bbox[1]))

        # 1. Body Crop (Wide Context)
        by1, by2, bx1, bx2 = get_crop_coords(img.shape, primary.bbox, "body")
        cv2.imwrite(str(out_dir / f"body_{base_name}.jpg"), img[by1:by2, bx1:bx2])

        # 2. Face Crop (Grooming Detail: Hair + Neck)
        fy1, fy2, fx1, fx2 = get_crop_coords(img.shape, primary.bbox, "face")
        cv2.imwrite(str(out_dir / f"face_{base_name}.jpg"), img[fy1:fy2, fx1:fx2])
        
        count += 2

    print(f"✅ Generated {count} images (Body + Face) in {out_dir}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        run(sys.argv[1])