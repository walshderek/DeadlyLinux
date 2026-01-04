"""
STEP 7: PUBLISH RESIZED IMAGES & CAPTIONS
Images are pre-resized from Step 5.
Captions are from Step 6.
"""

import sys
import os
import shutil
from pathlib import Path

# --- BOOTSTRAP ---
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)
import utils

# --- CONFIGURATION ---
RESOLUTIONS = [256, 512, 1024]


def generate_toml(image_dir_path, cache_dir_path, resolution):
    """Generates training configuration for Musubi-Tuner."""
    return f'''[general]
caption_extension = ".txt"
batch_size = 1
enable_bucket = true
bucket_no_upscale = false
[[datasets]]
image_directory = "{image_dir_path}"
cache_directory = "{cache_dir_path}"
num_repeats = 1
resolution = [{resolution},{resolution}]
'''


def run(slug):
    """
    Step 7: Publish resized images & captions.
    Images are pre-resized from Step 5.
    Captions are from Step 6.
    """
    print(f"\n{'='*70}")
    print("STEP 7: PUBLISH")
    print(f"{'='*70}")
    
    config = utils.load_config(slug)
    if not config:
        print(f"❌ Error: Config not found for {slug}")
        return
    
    path = utils.get_project_path(slug)
    
    # Source: Pre-resized images from step 05, captions from step 06
    caption_dir = path / utils.DIRS.get('caption', '06_caption')
    
    if not caption_dir.exists():
        print(f"❌ No captions found in {caption_dir}")
        return

    # Prepare the project-local publish root
    publish_root = path / utils.DIRS.get('publish', '07_publish')
    if publish_root.exists():
        shutil.rmtree(publish_root)
    publish_root.mkdir(parents=True, exist_ok=True)

    # Musubi destination paths
    musubi_wsl_app = Path(utils.MUSUBI_PATHS['wsl_app'])
    musubi_dataset_root = musubi_wsl_app / "files" / "datasets" / slug
    
    # Windows C: drive mount point
    win_mount_app = Path("/mnt/c/AI/apps/musubi-tuner")
    win_dataset_root = win_mount_app / "files" / "datasets" / slug if win_mount_app.exists() else None

    print(f"\n📁 Caption source: {caption_dir}")
    print(f"📊 Publishing to: {publish_root}\n")

    # Multi-Resolution Image Loop
    for res in RESOLUTIONS:
        print(f"🔄 Processing {res}x{res}...")
        
        # Source: Pre-resized folder
        src_res_dir = path / "05_resize" / str(res)
        if not src_res_dir.exists():
            print(f"   ⚠️  Skipping {res} - folder not found")
            continue
        
        local_res_dir = publish_root / str(res)
        musubi_res_dir = musubi_dataset_root / str(res)
        musubi_cache_dir = musubi_dataset_root / f"{res}_cache"
        
        local_res_dir.mkdir(parents=True, exist_ok=True)
        musubi_res_dir.mkdir(parents=True, exist_ok=True)
        musubi_cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Also create Windows mount directories if accessible
        if win_dataset_root:
            win_res_dir = win_dataset_root / str(res)
            win_cache_dir = win_dataset_root / f"{res}_cache"
            win_res_dir.mkdir(parents=True, exist_ok=True)
            win_cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Copy resized images
        image_files = sorted(src_res_dir.glob("*.jpg"))
        for img_file in image_files:
            shutil.copy2(img_file, local_res_dir / img_file.name)
            shutil.copy2(img_file, musubi_res_dir / img_file.name)
            
            if win_dataset_root:
                shutil.copy2(img_file, win_dataset_root / str(res) / img_file.name)
            
            # Caption Sync (Critical: Every image MUST have a .txt)
            txt = img_file.stem + ".txt"
            caption_file = caption_dir / "phase_3_final" / txt
            
            if caption_file.exists():
                shutil.copy2(caption_file, local_res_dir / txt)
                shutil.copy2(caption_file, musubi_res_dir / txt)
                if win_dataset_root:
                    shutil.copy2(caption_file, win_dataset_root / str(res) / txt)
            else:
                # Force fallback caption if missing
                fallback_cap = config.get('trigger', 'Scottington')
                with open(musubi_res_dir / txt, 'w', encoding='utf-8') as tf:
                    tf.write(fallback_cap)
                if win_dataset_root:
                    with open(win_dataset_root / str(res) / txt, 'w', encoding='utf-8') as tf:
                        tf.write(fallback_cap)
        
        # Generate config.toml
        win_img_path = f"C:/AI/apps/musubi-tuner/files/datasets/{slug}/{res}" if win_dataset_root else str(musubi_res_dir)
        toml_content = generate_toml(win_img_path, str(musubi_cache_dir), res)
        
        for toml_path in [local_res_dir / "config.toml", musubi_res_dir / "config.toml"]:
            with open(toml_path, 'w', encoding='utf-8') as f:
                f.write(toml_content)
        
        if win_dataset_root:
            with open(win_dataset_root / str(res) / "config.toml", 'w', encoding='utf-8') as f:
                f.write(toml_content)
        
        print(f"   ✅ {res}x{res}: {len(image_files)} images published")

    print(f"\n✅ Publish Complete!")
    print(f"   📁 {publish_root}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        run(sys.argv[1])
