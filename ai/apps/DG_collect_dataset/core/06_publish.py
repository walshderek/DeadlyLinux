# core/06_publish.py
import sys
import os
import shutil
from pathlib import Path
from PIL import Image

# --- BOOTSTRAP ---
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path: sys.path.append(current_dir)
import utils

# --- CONFIGURATION ---
# Target resolutions for Wan 2.2 bucketed learning
RESOLUTIONS = [256, 512, 1024]
TEMPLATE_DIR = Path(os.path.dirname(os.path.abspath(__file__))) / "templates"

def read_template(filename):
    """Reads a template file from the core/templates directory."""
    with open(TEMPLATE_DIR / filename, 'r') as f: return f.read()

def generate_toml(image_dir_path, cache_dir_path, resolution):
    """
    Generates the training configuration for Musubi-Tuner.
    Ensures absolute Windows paths with forward slashes are used.
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
    Step 06: Publish & Deployment.
    Deploys dataset to local Musubi folders and generates Windows training scripts.
    """
    print(f"🚀 [06_publish] Cross-Environment Deployment for {slug}...")
    config = utils.load_config(slug)
    if not config: return
    
    path = utils.get_project_path(slug)
    # Source caption or cleaned images
    src_dir = path / utils.DIRS.get('caption', '05_caption')
    if not src_dir.exists(): src_dir = path / utils.DIRS.get('clean', '04_clean')

    # Prep local project publish root
    publish_root = path / utils.DIRS.get('publish', '06_publish')
    if publish_root.exists(): shutil.rmtree(publish_root)
    publish_root.mkdir(parents=True, exist_ok=True)

    # Musubi Destination Paths (WSL Mount mapping to Windows C:/)
    musubi_wsl_app = Path(utils.MUSUBI_PATHS['wsl_app'])
    musubi_dataset_root = musubi_wsl_app / "files" / "datasets" / slug

    # 1. Image Resizing and Data Sync Loop
    files = sorted([f for f in os.listdir(src_dir) if f.lower().endswith(('.jpg', '.png', '.jpeg'))])
    
    for res in RESOLUTIONS:
        print(f"   -> Deploying {res}px dataset...")
        local_res_dir = publish_root / str(res)
        musubi_res_dir = musubi_dataset_root / str(res)
        
        local_res_dir.mkdir(parents=True, exist_ok=True)
        musubi_res_dir.mkdir(parents=True, exist_ok=True)
        
        for f in files:
            with Image.open(src_dir / f) as img:
                img = img.convert("RGB")
                # Downscale for training efficiency
                img.resize((res, res), Image.LANCZOS).save(local_res_dir / f, quality=95)
            
            # Sync to C:/AI/apps/musubi-tuner/files/datasets/... via WSL mount
            shutil.copy2(local_res_dir / f, musubi_res_dir / f)
            
            # Sync matching caption for trainer verification
            txt = os.path.splitext(f)[0] + ".txt"
            if (src_dir / txt).exists():
                shutil.copy2(src_dir / txt, local_res_dir / txt)
                shutil.copy2(src_dir / txt, musubi_res_dir / txt)

    # 2. TOML Generation (Local Windows Path with Forward Slashes)
    # Target: C:/AI/apps/musubi-tuner/files/datasets/slug/256
    win_image_path = utils.get_windows_forward_path(slug, "256")
    win_cache_path = f"{win_image_path}_cache" 
    
    linux_local_dataset = str(musubi_dataset_root / "256")
    linux_cache_path = f"{linux_local_dataset}_cache"
    
    toml_win = generate_toml(win_image_path, win_cache_path, 256)
    toml_linux = generate_toml(linux_local_dataset, linux_cache_path, 256)
    
    musubi_toml_dir = musubi_wsl_app / "files" / "tomls"
    musubi_toml_dir.mkdir(parents=True, exist_ok=True)
    
    with open(musubi_toml_dir / f"{slug}_win.toml", "w") as f: f.write(toml_win)
    with open(musubi_toml_dir / f"{slug}_linux.toml", "w") as f: f.write(toml_linux)

    # 3. Training Script Generation (Full Token Replacement)
    try:
        bat_template = read_template("train_template.bat")
        sh_template = read_template("train_template.sh")
        
        # Token mapping for Windows execution
        win_map = {
            "@WAN@": utils.MUSUBI_PATHS['win_app'],
            "@CFG@": f"{utils.MUSUBI_PATHS['win_app']}/files/tomls/{slug}_win.toml".replace("\\", "/"),
            "@OUT@": f"{utils.MUSUBI_PATHS['win_app']}/outputs/{slug}".replace("\\", "/"),
            "@OUTNAME@": slug,
            "@LOGDIR@": f"{utils.MUSUBI_PATHS['win_app']}/logs".replace("\\", "/"),
            "@DIT_LOW@": "C:/AI/models/diffusion_models/Wan/Wan2.2/14B/Wan_2_2_T2V/bf16/Wan-2.2-T2V-Low-Noise-BF16.safetensors",
            "@DIT_HIGH@": "C:/AI/models/diffusion_models/Wan/Wan2.2/14B/Wan_2_2_T2V/bf16/Wan-2.2-T2V-High-Noise-BF16.safetensors",
            "@VAE@": "C:/AI/models/vae/WAN/Wan2.1_VAE.pth",
            "@T5@": "C:/AI/models/clip/models_t5_umt5-xxl-enc-bf16.pth",
            "@GRAD_ACCUM@": "1", "@LEARNING_RATE@": "0.0001", "@EPOCHS@": "35", "@NETWORK_ALPHA@": "16", "@N_WORKERS@": "4"
        }
        
        bat_final = bat_template
        for k, v in win_map.items(): bat_final = bat_final.replace(k, v)
        with open(musubi_wsl_app / f"train_{slug}.bat", "w") as f: f.write(bat_final)
        
        # Linux Token Mapping
        linux_map = {
            "@WAN@": utils.MUSUBI_PATHS['wsl_app'],
            "@CFG@": f"{utils.MUSUBI_PATHS['wsl_app']}/files/tomls/{slug}_linux.toml",
            "@OUT@": f"{utils.MUSUBI_PATHS['wsl_app']}/outputs/{slug}",
            "@OUTNAME@": slug,
            "@LOGDIR@": f"{utils.MUSUBI_PATHS['wsl_app']}/logs",
            "@DIT_LOW@": "/home/seanf/ai/models/diffusion-models/Wan/Wan2.2/14B/Wan_2_2_T2V/bf16/Wan-2.2-T2V-Low-Noise-BF16.safetensors",
            "@VAE@": "/home/seanf/ai/models/vae/WAN/Wan2.1_VAE.pth",
            "@T5@": "/home/seanf/ai/models/clip/models_t5_umt5-xxl-enc-bf16.pth",
            "@GRAD_ACCUM@": "1", "@LEARNING_RATE@": "0.0001", "@EPOCHS@": "35", "@NETWORK_ALPHA@": "16", "@N_WORKERS@": "4"
        }

        sh_final = sh_template
        for k, v in linux_map.items(): sh_final = sh_final.replace(k, v)
        with open(musubi_wsl_app / f"train_{slug}.sh", "w") as f: f.write(sh_final)
        os.chmod(musubi_wsl_app / f"train_{slug}.sh", 0o755)
        
        # Backup to project
        with open(publish_root / f"train_{slug}.bat", "w") as f: f.write(bat_final)
        
    except Exception as e:
        print(f"⚠️  Script generation error: {e}")

    # 4. Sheets Logging
    desc_f = path / "characterDesc" / f"{slug}_desc.txt"
    desc = desc_f.read_text() if desc_f.exists() else ""
    utils.log_trigger_to_sheet(config.get('name', slug), config.get('trigger', 'Scottington'), desc)

    print(f"✅ Success. Project '{slug}' published with forward-slash Windows paths.")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        run(sys.argv[1])