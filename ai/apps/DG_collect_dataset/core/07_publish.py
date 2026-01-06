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
TEMPLATE_DIR = Path(__file__).parent / "templates"


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
    win_toml_dir = win_mount_app / "files" / "tomls" if win_mount_app.exists() else None
    
    # Create toml directory
    if win_toml_dir:
        win_toml_dir.mkdir(parents=True, exist_ok=True)

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
            # Try tier-separated structure first, then legacy
            caption_file = caption_dir / "final_captions" / "final_captions_raw" / txt
            if not caption_file.exists():
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
        
        # Generate config.toml from template - place in central toml directory
        config_template = TEMPLATE_DIR / "config_template.toml"
        if config_template.exists():
            template_content = config_template.read_text(encoding='utf-8')
            dataset_path = f"C:/AI/apps/musubi-tuner/files/datasets/{slug}/{res}"
            cache_path = f"C:/AI/apps/musubi-tuner/files/datasets/{slug}/{res}_cache"
            
            toml_content = template_content.replace("@DATASET_PATH@", dataset_path)
            toml_content = toml_content.replace("@CACHE_PATH@", cache_path)
        else:
            # Fallback to inline generation
            dataset_path = f"C:/AI/apps/musubi-tuner/files/datasets/{slug}/{res}"
            cache_path = f"C:/AI/apps/musubi-tuner/files/datasets/{slug}/{res}_cache"
            toml_content = f'''[general]
caption_extension = ".txt"
batch_size = 1
enable_bucket = true
bucket_no_upscale = false
[[datasets]]
image_directory = "{dataset_path}"
cache_directory = "{cache_path}"
num_repeats = 1
resolution = [{res},{res}]
'''
        
        # Write to central toml directory - only write once for 256 resolution
        if res == 256 and win_toml_dir:
            with open(win_toml_dir / f"{slug}_win.toml", 'w', encoding='utf-8') as f:
                f.write(toml_content)
        
        # Generate per-resolution training script from template
        bat_template = TEMPLATE_DIR / "train_template.bat"
        if bat_template.exists():
            template_content = bat_template.read_text(encoding='utf-8')
            
            wan_root = "C:\\AI\\apps\\musubi-tuner"
            cfg_path = f"C:\\AI\\apps\\musubi-tuner\\files\\tomls\\{slug}_win.toml"
            dit_low = "C:/AI/models/diffusion_models/Wan/Wan2.2/14B/Wan_2_2_T2V/bf16/Wan-2.2-T2V-Low-Noise-BF16.safetensors"
            dit_high = "C:/AI/models/diffusion_models/Wan/Wan2.2/14B/Wan_2_2_T2V/bf16/Wan-2.2-T2V-High-Noise-BF16.safetensors"
            vae = "C:/AI/models/vae/WAN/Wan2.1_VAE.pth"
            t5 = "C:/AI/models/clip/models_t5_umt5-xxl-enc-bf16.pth"
            out_dir = f"C:\\AI\\apps\\musubi-tuner\\outputs\\{slug}"
            out_name = slug
            log_dir = "C:\\AI\\apps\\musubi-tuner\\logs"
            
            bat_content = template_content.replace("@WAN@", wan_root)
            bat_content = bat_content.replace("@CFG@", cfg_path)
            bat_content = bat_content.replace("@DIT_LOW@", dit_low)
            bat_content = bat_content.replace("@DIT_HIGH@", dit_high)
            bat_content = bat_content.replace("@VAE@", vae)
            bat_content = bat_content.replace("@T5@", t5)
            bat_content = bat_content.replace("@OUT@", out_dir)
            bat_content = bat_content.replace("@OUTNAME@", out_name)
            bat_content = bat_content.replace("@LOGDIR@", log_dir)
            bat_content = bat_content.replace("@LEARNING_RATE@", "5e-5")
            bat_content = bat_content.replace("@NETWORK_ALPHA@", "32")
            bat_content = bat_content.replace("@NETWORK_DIM@", "64")
            bat_content = bat_content.replace("@N_WORKERS@", "2")
            bat_content = bat_content.replace("@EPOCHS@", "10")
            bat_content = bat_content.replace("@GRAD_ACCUM@", "1")
            
            # Write per-resolution bat to dataset directories
            if win_dataset_root:
                with open(win_dataset_root / str(res) / f"train_{slug}_{res}.bat", 'w', encoding='utf-8') as f:
                    f.write(bat_content)
                    
                # For 256 resolution, also write the main training script at root
                if res == 256:
                    with open(win_mount_app / f"train_{slug}.bat", 'w', encoding='utf-8') as f:
                        f.write(bat_content)
        
        print(f"   ✅ {res}x{res}: {len(image_files)} images published")

    print(f"\n✅ Publish Complete!")
    print(f"   📁 {publish_root}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        run(sys.argv[1])
