# core/06_publish.py
import sys
import os
import shutil
from pathlib import Path
from PIL import Image

# --- BOOTSTRAP ---
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)
import utils

# --- CONFIGURATION ---
RESOLUTIONS = [256, 512, 1024]
TEMPLATE_DIR = Path(current_dir) / "templates"

def read_template(filename):
    """Reads a training script template file in full."""
    with open(TEMPLATE_DIR / filename, 'r', encoding='utf-8') as f:
        return f.read()

def generate_toml(image_dir_path, cache_dir_path, resolution):
    """
    Generates the training configuration for Musubi-Tuner.
    Fix: Separates image and cache directories to allow latent generation.
    Paths are enforced as Windows-style with forward slashes.
    """
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
    Step 06: Publish & Cache-Fix Deployment.
    Prepares images, ensures matching captions exist, and isolates the cache dir.
    """
    print(f"🚀 [06_publish] STARTING DEPLOYMENT FOR: {slug}")
    config = utils.load_config(slug)
    if not config:
        print(f"❌ Error: Config not found for {slug}")
        return
    
    path = utils.get_project_path(slug)
    # Target source directories from Step 5 (Captions) or 4 (Cleaned)
    src_dir = path / utils.DIRS.get('caption', '05_caption')
    if not src_dir.exists() or not os.listdir(src_dir):
        src_dir = path / utils.DIRS.get('clean', '04_clean')

    # Prepare the project-local publish root
    publish_root = path / utils.DIRS.get('publish', '06_publish')
    if publish_root.exists():
        shutil.rmtree(publish_root)
    publish_root.mkdir(parents=True, exist_ok=True)

    # Musubi destination paths (both WSL and Windows mount)
    musubi_wsl_app = Path(utils.MUSUBI_PATHS['wsl_app'])
    musubi_dataset_root = musubi_wsl_app / "files" / "datasets" / slug
    
    # Windows C: drive mount point
    win_mount_app = Path("/mnt/c/AI/apps/musubi-tuner")
    win_dataset_root = win_mount_app / "files" / "datasets" / slug if win_mount_app.exists() else None

    # 1. Multi-Resolution Image Loop
    files = sorted([f for f in os.listdir(src_dir) if f.lower().endswith(('.jpg', '.png', '.jpeg'))])
    if not files:
        print(f"❌ Error: No images found in source {src_dir}")
        return

    for res in RESOLUTIONS:
        print(f"   -> Processing {res}px resolution and isolating cache subfolder...")
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
        
        for f in files:
            # Sync Image: Resize and save to project then copy to Musubi locations
            with Image.open(src_dir / f) as img:
                img = img.convert("RGB")
                img.resize((res, res), Image.LANCZOS).save(local_res_dir / f, quality=95)
            
            # Deploy to WSL location
            shutil.copy2(local_res_dir / f, musubi_res_dir / f)
            
            # Deploy to Windows mount if accessible
            if win_dataset_root:
                shutil.copy2(local_res_dir / f, win_res_dir / f)
            
            # Caption Sync (Critical: Every image MUST have a .txt for batches to initialize)
            txt = os.path.splitext(f)[0] + ".txt"
            if (src_dir / txt).exists():
                shutil.copy2(src_dir / txt, local_res_dir / txt)
                shutil.copy2(src_dir / txt, musubi_res_dir / txt)
                if win_dataset_root:
                    shutil.copy2(src_dir / txt, win_res_dir / txt)
            else:
                # Force fallback caption if missing to avoid "No training items" error
                fallback_cap = config.get('trigger', 'Scottington')
                with open(musubi_res_dir / txt, 'w', encoding='utf-8') as tf:
                    tf.write(fallback_cap)
                if win_dataset_root:
                    with open(win_res_dir / txt, 'w', encoding='utf-8') as tf:
                        tf.write(fallback_cap)

    # 2. TOML Generation (Both Linux and Windows)
    # Windows paths with forward slashes for TOML compatibility
    win_base = utils.MUSUBI_PATHS['win_app'].replace("\\", "/")
    win_image_path = f"{win_base}/files/datasets/{slug}/256"
    win_cache_path = f"{win_image_path}_cache"
    
    # Linux paths 
    linux_image_path = str(musubi_dataset_root / "256")
    linux_cache_path = f"{linux_image_path}_cache"
    
    # Generate both TOML files
    toml_win = generate_toml(win_image_path, win_cache_path, 256)
    toml_linux = generate_toml(linux_image_path, linux_cache_path, 256)
    
    # Write to Musubi App and Local Backup
    musubi_toml_dir = musubi_wsl_app / "files" / "tomls"
    musubi_toml_dir.mkdir(parents=True, exist_ok=True)
    
    with open(musubi_toml_dir / f"{slug}_win.toml", "w", encoding='utf-8') as f:
        f.write(toml_win)
    
    with open(musubi_toml_dir / f"{slug}_linux.toml", "w", encoding='utf-8') as f:
        f.write(toml_linux)
    
    # Also deploy TOML files to Windows mount if accessible
    if win_mount_app.exists():
        win_toml_dir = win_mount_app / "files" / "tomls"
        win_toml_dir.mkdir(parents=True, exist_ok=True)
        
        with open(win_toml_dir / f"{slug}_win.toml", "w", encoding='utf-8') as f:
            f.write(toml_win)
        
        with open(win_toml_dir / f"{slug}_linux.toml", "w", encoding='utf-8') as f:
            f.write(toml_linux)
        
        print(f"✅ TOML files deployed to C:\\AI\\apps\\musubi-tuner\\files\\tomls\\")

    # 3. Training Script Generation (Full Token Replacement)
    try:
        bat_template = read_template("train_template.bat")
        
        replacements = {
            "@WAN@": utils.MUSUBI_PATHS['win_app'],
            "@CFG@": f"{utils.MUSUBI_PATHS['win_app']}/files/tomls/{slug}_win.toml".replace("/", "\\"),
            "@OUT@": f"{utils.MUSUBI_PATHS['win_app']}/outputs/{slug}".replace("/", "\\"),
            "@OUTNAME@": slug,
            "@LOGDIR@": f"{utils.MUSUBI_PATHS['win_app']}/logs".replace("/", "\\"),
            "@DIT_LOW@": "C:/AI/models/diffusion_models/Wan/Wan2.2/14B/Wan_2_2_T2V/bf16/Wan-2.2-T2V-Low-Noise-BF16.safetensors",
            "@DIT_HIGH@": "C:/AI/models/diffusion_models/Wan/Wan2.2/14B/Wan_2_2_T2V/bf16/Wan-2.2-T2V-High-Noise-BF16.safetensors",
            "@VAE@": "C:/AI/models/vae/WAN/Wan2.1_VAE.pth",
            "@T5@": "C:/AI/models/clip/models_t5_umt5-xxl-enc-bf16.pth",
            "@GRAD_ACCUM@": "1",
            "@LEARNING_RATE@": "0.0001",
            "@EPOCHS@": "35",
            "@NETWORK_ALPHA@": "16",
            "@NETWORK_DIM@": "16",
            "@N_WORKERS@": "4"
        }
        
        bat_final = bat_template
        for k, v in replacements.items():
            bat_final = bat_final.replace(k, v)
            
        # Deploy to both WSL location and Windows C: drive mount
        with open(musubi_wsl_app / f"train_{slug}.bat", "w", encoding='utf-8') as f:
            f.write(bat_final)
        
        # Also deploy to Windows mount point (/mnt/c/AI/apps/musubi-tuner/)
        win_mount_path = Path("/mnt/c/AI/apps/musubi-tuner")
        if win_mount_path.exists():
            with open(win_mount_path / f"train_{slug}.bat", "w", encoding='utf-8') as f:
                f.write(bat_final)
            print(f"✅ Training script deployed to C:\\AI\\apps\\musubi-tuner\\train_{slug}.bat")
        else:
            print(f"⚠️ Windows mount not accessible at /mnt/c/AI/apps/musubi-tuner/")
            
    except Exception as e:
        print(f"⚠️ Warning: Script generation error: {e}")

    print(f"✅ SUCCESS: Project '{slug}' published with isolated cache.")
    print(f"👉 DATASET PATH: {win_image_path}")
    print(f"👉 CACHE PATH: {win_cache_path}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        run(sys.argv[1])
