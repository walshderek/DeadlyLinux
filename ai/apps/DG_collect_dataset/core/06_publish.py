import sys
import os
import shutil
from pathlib import Path
from PIL import Image

# --- BOOTSTRAP ---
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path: sys.path.append(current_dir)
import utils

# --- CONFIG ---
RESOLUTIONS = [256, 512, 1024]
TEMPLATE_DIR = Path(current_dir) / "templates"

def read_template(filename):
    with open(TEMPLATE_DIR / filename, 'r') as f:
        return f.read()

def generate_toml(clean_path_unc, resolution):
    """
    Generates the high-fidelity Musubi dataset config.
    Note: clean_path_unc must use //wsl.localhost/Ubuntu/... for Windows usage.
    """
    return f'''[general]
caption_extension = ".txt"
batch_size = 1
enable_bucket = true
bucket_no_upscale = false
[[datasets]]
image_directory = "{clean_path_unc}"
cache_directory = "{clean_path_unc}_cache"
num_repeats = 1
resolution = [{resolution},{resolution}]
'''

def run(slug):
    print(f"=== PUBLISHING {slug} ===")
    config = utils.load_config(slug)
    if not config: return
    
    path = utils.get_project_path(slug)
    caption_dir = path / utils.DIRS.get('caption', '05_caption')
    clean_dir = path / utils.DIRS.get('clean', '04_clean')
    
    # 1. Source Selection
    if caption_dir.exists() and os.listdir(caption_dir):
        src_dir = caption_dir
    else:
        src_dir = clean_dir
        print("⚠️  Warning: Using uncaptioned source data.")

    # 2. Directory Preparation
    publish_root = path / utils.DIRS.get('publish', '06_publish')
    if publish_root.exists(): shutil.rmtree(publish_root)
    publish_root.mkdir(parents=True, exist_ok=True)
    
    musubi_wsl_app = Path(utils.MUSUBI_PATHS['wsl_app'])
    musubi_dataset_root = musubi_wsl_app / "files" / "datasets" / slug
    
    # 3. Multi-Resolution Image Loop
    files = [f for f in os.listdir(src_dir) if f.lower().endswith(('.jpg', '.png', '.jpeg'))]
    
    for res in RESOLUTIONS:
        print(f"   -> Processing {res}px resolution...")
        res_dir = publish_root / str(res)
        musubi_res_dir = musubi_dataset_root / str(res)
        res_dir.mkdir(parents=True, exist_ok=True)
        musubi_res_dir.mkdir(parents=True, exist_ok=True)
        
        for f in files:
            # Resize and Save
            with Image.open(src_dir / f) as img:
                img = img.convert("RGB")
                img.resize((res, res), Image.LANCZOS).save(res_dir / f, quality=95)
            
            # Sync to Musubi app folder
            shutil.copy2(res_dir / f, musubi_res_dir / f)
            
            # Copy matching caption
            txt = os.path.splitext(f)[0] + ".txt"
            if (src_dir / txt).exists():
                shutil.copy2(src_dir / txt, res_dir / txt)
                shutil.copy2(src_dir / txt, musubi_res_dir / txt)

    # 4. Generate TOMLs (The Path Translation Fix)
    # Win TOML points to the 256 dataset via UNC path
    win_unc_path = utils.get_windows_unc_path(publish_root / "256")
    linux_dataset_path = str(musubi_dataset_root / "256")
    
    toml_win = generate_toml(win_unc_path, 256)
    toml_linux = generate_toml(linux_dataset_path, 256)
    
    toml_dir = musubi_wsl_app / "files" / "tomls"
    toml_dir.mkdir(parents=True, exist_ok=True)
    
    with open(toml_dir / f"{slug}_win.toml", "w") as f: f.write(toml_win)
    with open(toml_dir / f"{slug}_linux.toml", "w") as f: f.write(toml_linux)
    
    # Also backup to local project folder
    with open(publish_root / f"{slug}_win.toml", "w") as f: f.write(toml_win)

    # 5. Training Script Generation (Full Template Token Replacement)
    try:
        bat_content = read_template("train_template.bat")
        sh_content = read_template("train_template.sh")
        
        # Token mapping for Windows
        win_map = {
            "@WAN@": utils.MUSUBI_PATHS['win_app'],
            "@CFG@": f"{utils.MUSUBI_PATHS['win_app']}\\files\\tomls\\{slug}_win.toml",
            "@OUT@": f"{utils.MUSUBI_PATHS['win_app']}\\outputs\\{slug}",
            "@OUTNAME@": slug,
            "@LOGDIR@": f"{utils.MUSUBI_PATHS['win_app']}\\logs",
            "@DIT_LOW@": f"{utils.MUSUBI_PATHS['win_models']}\\diffusion-models\\Wan\\Wan2.2\\14B\\Wan_2_2_I2V\\fp16\\wan2.2_t2v_low_noise_14B_fp16.safetensors",
            "@DIT_HIGH@": f"{utils.MUSUBI_PATHS['win_models']}\\diffusion-models\\Wan\\Wan2.2\\14B\\Wan_2_2_I2V\\fp16\\wan2.2_t2v_high_noise_14B_fp16.safetensors",
            "@VAE@": f"{utils.MUSUBI_PATHS['win_models']}\\vae\\wan_2.1_vae.pth",
            "@T5@": f"{utils.MUSUBI_PATHS['win_models']}\\clip\\models_t5_umt5-xxl-enc-bf16.pth",
            "@GRAD_ACCUM@": "1", "@LEARNING_RATE@": "0.0001", "@N_WORKERS@": "8", "@EPOCHS@": "35", "@NETWORK_ALPHA@": "16"
        }
        
        # Token mapping for Linux
        linux_map = {
            "@WAN@": utils.MUSUBI_PATHS['wsl_app'],
            "@CFG@": f"{utils.MUSUBI_PATHS['wsl_app']}/files/tomls/{slug}_linux.toml",
            "@OUT@": f"{utils.MUSUBI_PATHS['wsl_app']}/outputs/{slug}",
            "@OUTNAME@": slug,
            "@LOGDIR@": f"{utils.MUSUBI_PATHS['wsl_app']}/logs",
            "@DIT_LOW@": f"{utils.MUSUBI_PATHS['wsl_models']}/diffusion-models/Wan/Wan2.2/14B/Wan_2_2_I2V/fp16/wan2.2_t2v_low_noise_14B_fp16.safetensors",
            "@DIT_HIGH@": f"{utils.MUSUBI_PATHS['wsl_models']}/diffusion-models/Wan/Wan2.2/14B/Wan_2_2_I2V/fp16/wan2.2_t2v_high_noise_14B_fp16.safetensors",
            "@VAE@": f"{utils.MUSUBI_PATHS['wsl_models']}/vae/wan_2.1_vae.pth",
            "@T5@": f"{utils.MUSUBI_PATHS['wsl_models']}/clip/models_t5_umt5-xxl-enc-bf16.pth",
            "@GRAD_ACCUM@": "1", "@LEARNING_RATE@": "0.0001", "@N_WORKERS@": "8", "@EPOCHS@": "35", "@NETWORK_ALPHA@": "16"
        }

        for k, v in win_map.items(): bat_content = bat_content.replace(k, v)
        for k, v in linux_map.items(): sh_content = sh_content.replace(k, v)

        with open(musubi_wsl_app / f"train_{slug}.bat", "w") as f: f.write(bat_content)
        with open(musubi_wsl_app / f"train_{slug}.sh", "w") as f: f.write(sh_content)
        os.chmod(musubi_wsl_app / f"train_{slug}.sh", 0o755)
        
        # Backup to project folder
        with open(publish_root / f"train_{slug}.bat", "w") as f: f.write(bat_content)
        
    except Exception as e:
        print(f"⚠️  Script generation error: {e}")

    # 6. Final Logging
    desc_path = path / "characterDesc" / f"{slug}_desc.txt"
    desc = desc_path.read_text() if desc_path.exists() else ""
    utils.log_trigger_to_sheet(config.get('name', slug), config.get('trigger', ''), desc)

    print(f"✅ Dataset and Training Scripts published correctly for {slug}!")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        run(sys.argv[1])