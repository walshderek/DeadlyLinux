import sys
import os
import shutil
from pathlib import Path

# Bootstrap utils
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path: sys.path.append(current_dir)
import utils

# --- CONFIG ---
TARGET_RES = 256
TEMPLATE_DIR = Path(current_dir) / "templates"

def read_template(filename):
    with open(TEMPLATE_DIR / filename, 'r') as f:
        return f.read()

def generate_toml(clean_path_unc, resolution):
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
    
    # 1. Source Selection (Paper Trail)
    caption_dir = path / utils.DIRS.get('caption', '05_caption')
    clean_dir = path / utils.DIRS.get('clean', '04_clean')
    
    if caption_dir.exists() and os.listdir(caption_dir):
        src_dir = caption_dir
    elif clean_dir.exists():
        src_dir = clean_dir
        print("⚠️  Warning: Using uncaptioned images (04_clean)")
    else:
        print("❌ Error: No images found.")
        return

    # 2. Prepare Directories
    publish_root = path / utils.DIRS.get('publish', '06_publish')
    publish_res = publish_root / "256"
    
    if publish_root.exists(): shutil.rmtree(publish_root)
    publish_res.mkdir(parents=True, exist_ok=True)
    
    # Musubi Destination (WSL Path)
    musubi_root_wsl = Path(utils.MUSUBI_PATHS['wsl_app'])
    dest_dataset_dir = musubi_root_wsl / "files" / "datasets" / slug / "256"
    
    # 3. Copy Images
    print(f"📂 Copying to {dest_dataset_dir}...")
    if dest_dataset_dir.exists(): shutil.rmtree(dest_dataset_dir)
    dest_dataset_dir.mkdir(parents=True, exist_ok=True)
    
    files = [f for f in os.listdir(src_dir) if f.lower().endswith(('.jpg', '.png'))]
    for f in files:
        # Copy to local publish folder
        shutil.copy2(src_dir / f, publish_res / f)
        # Copy to Musubi folder
        shutil.copy2(src_dir / f, dest_dataset_dir / f)
        
        # Handle captions
        txt = os.path.splitext(f)[0] + ".txt"
        if (src_dir / txt).exists():
            shutil.copy2(src_dir / txt, publish_res / txt)
            shutil.copy2(src_dir / txt, dest_dataset_dir / txt)

    # 4. Generate TOMLs
    # Windows path for the BAT file execution
    win_dataset_path = f"{utils.MUSUBI_PATHS['win_app']}/files/datasets/{slug}/256"
    # Linux path for the SH file execution
    linux_dataset_path = f"{utils.MUSUBI_PATHS['wsl_app']}/files/datasets/{slug}/256"
    
    toml_win = generate_toml(win_dataset_path, TARGET_RES)
    toml_linux = generate_toml(linux_dataset_path, TARGET_RES)
    
    toml_dir = musubi_root_wsl / "files" / "tomls"
    toml_dir.mkdir(parents=True, exist_ok=True)
    
    with open(toml_dir / f"{slug}_win.toml", "w") as f: f.write(toml_win)
    with open(toml_dir / f"{slug}_linux.toml", "w") as f: f.write(toml_linux)

    # 5. Fill Templates
    replacements = {
        "@WAN@": utils.MUSUBI_PATHS['win_app'], # For BAT
        "@WAN_WSL@": utils.MUSUBI_PATHS['wsl_app'], # For SH
        "@CFG@": f"{utils.MUSUBI_PATHS['win_app']}\\files\\tomls\\{slug}_win.toml",
        "@CFG_WSL@": f"{utils.MUSUBI_PATHS['wsl_app']}/files/tomls/{slug}_linux.toml",
        "@OUT@": f"{utils.MUSUBI_PATHS['win_app']}\\outputs\\{slug}",
        "@OUT_WSL@": f"{utils.MUSUBI_PATHS['wsl_app']}/outputs/{slug}",
        "@OUTNAME@": slug,
        "@LOGDIR@": f"{utils.MUSUBI_PATHS['win_app']}\\logs",
        "@LOGDIR_WSL@": f"{utils.MUSUBI_PATHS['wsl_app']}/logs",
        "@DIT_LOW@": f"{utils.MUSUBI_PATHS['win_models']}\\diffusion-models\\Wan\\Wan2.2\\14B\\Wan_2_2_I2V\\fp16\\wan2.2_t2v_low_noise_14B_fp16.safetensors",
        "@DIT_HIGH@": f"{utils.MUSUBI_PATHS['win_models']}\\diffusion-models\\Wan\\Wan2.2\\14B\\Wan_2_2_I2V\\fp16\\wan2.2_t2v_high_noise_14B_fp16.safetensors",
        "@VAE@": f"{utils.MUSUBI_PATHS['win_models']}\\vae\\wan_2.1_vae.pth",
        "@T5@": f"{utils.MUSUBI_PATHS['win_models']}\\clip\\models_t5_umt5-xxl-enc-bf16.pth",
        # Hyperparams
        "@GRAD_ACCUM@": "1",
        "@LEARNING_RATE@": "0.0001",
        "@N_WORKERS@": "8",
        "@EPOCHS@": "35",
        "@NETWORK_ALPHA@": "16",
        "@NETWORK_DIM@": "16"
    }
    
    # WSL Specific replacements for the .sh file
    replacements_sh = replacements.copy()
    replacements_sh["@WAN@"] = utils.MUSUBI_PATHS['wsl_app']
    replacements_sh["@CFG@"] = replacements["@CFG_WSL@"]
    replacements_sh["@OUT@"] = replacements["@OUT_WSL@"]
    replacements_sh["@LOGDIR@"] = replacements["@LOGDIR_WSL@"]
    # Convert Win paths to WSL paths for models
    for key in ["@DIT_LOW@", "@DIT_HIGH@", "@VAE@", "@T5@"]:
        replacements_sh[key] = replacements_sh[key].replace(utils.MUSUBI_PATHS['win_models'], utils.MUSUBI_PATHS['wsl_models']).replace("\\", "/")

    # Generate BAT
    bat_content = read_template("train_template.bat")
    for k, v in replacements.items():
        bat_content = bat_content.replace(k, v)
    
    # Generate SH
    sh_content = read_template("train_template.sh")
    for k, v in replacements_sh.items():
        sh_content = sh_content.replace(k, v)

    # Write Scripts
    with open(musubi_root_wsl / f"train_{slug}.bat", "w") as f: f.write(bat_content)
    with open(musubi_root_wsl / f"train_{slug}.sh", "w") as f: f.write(sh_content)
    os.chmod(musubi_root_wsl / f"train_{slug}.sh", 0o755)

    # Backup to publish folder
    with open(publish_root / f"train_{slug}.bat", "w") as f: f.write(bat_content)
    with open(publish_root / f"train_{slug}.sh", "w") as f: f.write(sh_content)
    
    # Log Trigger
    trigger = config.get('trigger', '')
    with open(publish_root / "trigger.txt", "w") as f: f.write(trigger)
    utils.log_trigger_to_sheet(slug, trigger)
    
    print(f"✅ Published! Run training with:")
    print(f"   Windows: {utils.MUSUBI_PATHS['win_app']}\\train_{slug}.bat")
    print(f"   WSL:     {utils.MUSUBI_PATHS['wsl_app']}/train_{slug}.sh")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        run(sys.argv[1])