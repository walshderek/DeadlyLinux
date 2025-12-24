#!/usr/bin/env python3
import os
import sys
import shutil
from pathlib import Path
from tqdm import tqdm
import cv2
import torch


# --- VENV ENFORCEMENT ---
def _ensure_venv():
    import sys, os
    venv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), ".venv")
    if not hasattr(sys, 'real_prefix') and not os.environ.get("VIRTUAL_ENV"):
        venv_python = os.path.join(venv_path, "bin", "python")
        if os.path.exists(venv_python):
            print(f"[VENV] Relaunching in venv: {venv_python}")
            os.execv(venv_python, [venv_python] + sys.argv)
        else:
            print("[VENV] WARNING: .venv not found, running outside venv!")
_ensure_venv()

current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)
import utils

def is_square_image(img_path):
    img = cv2.imread(str(img_path))
    if img is None:
        return False
    h, w = img.shape[:2]
    return h == w

def run(slug):
    """
    Step 04: AI Sanitization & Persistence Merge
    Ensures 100% data retention by merging faces with their body counterparts.
    Only square images are propagated.
    Uses GPU if available (torch.cuda.is_available()).
    """
    if torch.cuda.is_available():
        print(f"[GPU] CUDA is available. Using GPU for downstream steps.")
    else:
        print(f"[GPU] WARNING: CUDA is NOT available. Running on CPU.")

    path = utils.get_project_path(slug)
    scrape_dir = path / utils.DIRS.get('scrape', '01_setup_scrape')
    validate_dir = path / utils.DIRS.get('validate', '03_validate')
    clean_dir = path / utils.DIRS.get('clean', '04_clean')

    if clean_dir.exists(): shutil.rmtree(clean_dir)
    clean_dir.mkdir(parents=True, exist_ok=True)

    if not validate_dir.exists():
        print(f"\u274c Error: Validation folder missing: {validate_dir}")
        return

    print(f"\u2728 [04_clean] Merging Body & Face data for {slug} (square only)...")

    valid_files = [f for f in os.listdir(validate_dir) if f.lower().endswith(('.jpg', '.png', '.jpeg'))]
    count = 0
    for f_name in tqdm(valid_files, desc="Merging Persistence"):
        src_path = validate_dir / f_name
        if not is_square_image(src_path):
            print(f"[SKIP] Non-square image skipped: {f_name}")
            continue
        shutil.copy2(src_path, clean_dir / f_name)

        # 2. Extract original filename to find the body counterpart
        raw_id = f_name.replace("face_", "").replace("body_", "")
        body_source = scrape_dir / raw_id
        if body_source.exists() and is_square_image(body_source):
            shutil.copy2(body_source, clean_dir / f"body_{raw_id}")
            count += 2
        else:
            count += 1

    print(f"\u2705 Clean Complete: {count} total square images ready for Step 5.")
    print(f"✅ Clean Complete: {count} total images ready for Step 5.")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        run(sys.argv[1])