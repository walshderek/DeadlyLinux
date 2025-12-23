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
    out_dir = path / utils.DIRS.get('scrape', '01_setup_scrape')
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"📂 [01_setup_scrape] Initializing for {slug}...")
    print(f"   Target Folder: {out_dir}")
    
    # Check if images already exist
    existing = [f for f in os.listdir(out_dir) if f.lower().endswith(('.jpg', '.png', '.jpeg', '.webp'))]
    
    if existing:
        print(f"✅ Found {len(existing)} images already in scrape folder.")
    else:
        print(f"⚠️  Folder is empty.")
        print(f"   ACTION REQUIRED: Drop your raw images into '{out_dir}'")
        print(f"   (or run your external scraper tool now)")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        run(sys.argv[1])
