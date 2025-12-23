import sys
import os
import shutil

try:
    import utils
except ImportError:
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    import utils

def run(slug):
    path = utils.get_project_path(slug)
    
    in_dir = path / utils.DIRS.get('crop', '02_crop')
    out_dir = path / utils.DIRS.get('validate', '03_validate')
    out_dir.mkdir(parents=True, exist_ok=True)
    
    if not in_dir.exists():
        print(f"❌ Step 2 (Crop) folder missing: {in_dir}")
        return

    print(f"🧐 Preparing Validation Folder: {out_dir}")
    
    files = [f for f in os.listdir(in_dir) if f.lower().endswith(('.jpg', '.png'))]
    
    if not files:
        print("⚠️  No cropped images found.")
        return

    # Check if we already populated this
    existing = len(os.listdir(out_dir))
    if existing > 0:
        print(f"ℹ️  Validation folder already has {existing} images.")
        print("   Skipping overwrite to preserve manual deletions.")
        return

    # Initial Population
    count = 0
    for f in files:
        shutil.copy2(in_dir / f, out_dir / f)
        count += 1
        
    print(f"✅ Moved {count} images to 03_validate.")
    print("👉 ACTION: Go to that folder and delete any bad/blurry images NOW.")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        run(sys.argv[1])
