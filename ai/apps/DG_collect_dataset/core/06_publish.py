import os
import sys
import shutil
from pathlib import Path

# --- BOOTSTRAP ---
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path: sys.path.append(current_dir)
import utils

def generate_toml_content(img_dir, res=256):
    return f"""[general]
caption_extension = ".txt"
batch_size = 1
enable_bucket = true

[[datasets]]
image_directory = "{img_dir}"
cache_directory = "{img_dir}_cache"
resolution = [{res},{res}]
"""

def generate_bat_content(slug, win_toml_path):
    # Minimal BAT file for Musubi Tuner, referencing the TOML config
    # You can expand this template as needed
    return f"""@echo off
setlocal enabledelayedexpansion

:: --- PATH CONFIGURATION ---
set "WAN_ROOT=C:\\AI\\apps\\musubi-tuner"
set "CFG=%WAN_ROOT%\\files\\tomls\\{slug}_win.toml"
set "DIT_LOW=C:\\AI\\models\\diffusion_models\\Wan\\Wan2.2\\14B\\Wan_2_2_T2V\\bf16\\Wan-2.2-T2V-Low-Noise-BF16.safetensors"
set "DIT_HIGH=C:\\AI\\models\\diffusion_models\\Wan\\Wan2.2\\14B\\Wan_2_2_T2V\\bf16\\Wan-2.2-T2V-High-Noise-BF16.safetensors"
set "VAE=C:\\AI\\models\\vae\\WAN\\Wan2.1_VAE.pth"
set "T5=C:\\AI\\models\\clip\\models_t5_umt5-xxl-enc-bf16.pth"
set "OUT=%WAN_ROOT%\\outputs\\{slug}"
set "OUTNAME={slug}"
set "LOGDIR=%WAN_ROOT%\\logs"

:: --- ENVIRONMENT ACTIVATION ---
cd /d "%WAN_ROOT%"
call ".\\venv\\Scripts\\activate.bat"

:: --- MEMORY OPTIMIZATION ---
set PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True

:: --- EXECUTION (Single-Model Block Swap Protocol) ---
python -m accelerate.commands.launch --num_processes 1 "wan_train_network.py" ^
    --dataset_config "%CFG%" ^
    --discrete_flow_shift 3 ^
    --dit "%DIT_LOW%" ^
    --dit_high_noise "%DIT_HIGH%" ^
    --fp8_base ^
    --fp8_scaled ^
    --fp8_t5 ^
    --gradient_accumulation_steps 1 ^
    --gradient_checkpointing ^
    --img_in_txt_in_offloading ^
    --learning_rate 0.0001 ^
    --max_grad_norm 1.0 ^
    --log_with tensorboard ^
    --logging_dir "%LOGDIR%" ^
    --lr_scheduler cosine ^
    --lr_warmup_steps 200 ^
    --max_data_loader_n_workers 4 ^
    --max_timestep 1000 ^
    --max_train_epochs 10 ^
    --min_timestep 0 ^
    --mixed_precision bf16 ^
    --network_alpha 128 ^
    --network_args "verbose=True" "exclude_patterns=[]" ^
    --network_dim 128 ^
    --network_module networks.lora_wan ^
    --blocks_to_swap 24 ^
    --optimizer_type AdamW8bit ^
    --output_dir "%OUT%" ^
    --output_name "%OUTNAME%" ^
    --persistent_data_loader_workers ^
    --save_every_n_epochs 5 ^
    --seed 42 ^
    --t5 "%T5%" ^
    --task t2v-A14B ^
    --timestep_boundary 875 ^
    --timestep_sampling logsnr ^
    --vae "%VAE%" ^
    --vae_cache_cpu ^
    --vae_dtype bfloat16 ^
    --sdpa

pause
"""

def run(slug):
    config = utils.load_config(slug)
    path = utils.get_project_path(slug)
    
    src_dir = path / utils.DIRS['caption']
    publish_root = path / utils.DIRS['publish']
    if publish_root.exists(): shutil.rmtree(publish_root)
    
    print(f"🚀 [06_publish] Cross-Environment Deployment for {slug}...")

    # 1. Resize & Organize
    res_list = [256, 512, 1024]
    for res in res_list:
        res_dir = publish_root / str(res)
        res_dir.mkdir(parents=True, exist_ok=True)
        
        # Copy/Resize would happen here (using simple copy for speed/fidelity as per brief)
        for f in os.listdir(src_dir):
            shutil.copy2(src_dir / f, res_dir / f)

    # 2. Path Translation (The Critical Fix)
    # Windows needs: //wsl.localhost/Ubuntu/home/seanf/...
    # Python Path .absolute() returns /home/seanf/...
    raw_linux_path = str(publish_root.absolute())
    
    # Force forward slashes and preppend UNC
    win_unc_path = f"//wsl.localhost/Ubuntu{raw_linux_path}/256"
    linux_path = f"{raw_linux_path}/256"

    # 3. Generate TOMLs
    toml_win = generate_toml_content(win_unc_path)
    toml_linux = generate_toml_content(linux_path)
    
    with open(publish_root / f"{slug}_win.toml", "w") as f: f.write(toml_win)
    with open(publish_root / f"{slug}_linux.toml", "w") as f: f.write(toml_linux)

    # 4. Deploy to Musubi (Windows & Linux)
    # Windows Destination
    # --- WINDOWS (C:) PATHS ---
    win_root = Path("/mnt/c/AI/apps/musubi-tuner")
    win_dataset = win_root / "files" / "datasets" / slug / "256"
    win_toml = win_root / "files" / "tomls" / f"{slug}_win.toml"
    win_bat = win_root / f"train_{slug}_256.bat"

    # Copy dataset
    if win_dataset.exists(): shutil.rmtree(win_dataset)
    shutil.copytree(publish_root / "256", win_dataset)

    # Copy TOML
    shutil.copy2(publish_root / f"{slug}_win.toml", win_toml)

    # Generate and copy BAT
    bat_content = generate_bat_content(slug, f"files/tomls/{slug}_win.toml")
    bat_filename = f"train_{slug}_256.bat"
    bat_path = publish_root / bat_filename
    with open(bat_path, "w") as f:
        f.write(bat_content)
    shutil.copy2(bat_path, win_bat)

    # 6. Cloud Log
    utils.log_trigger_to_sheet(config['name'], config['trigger'])
    print(f"✅ Deployment Complete.\n   Windows Path: {win_unc_path}\n   BAT Path: {bat_dest}")

if __name__ == "__main__":
    if len(sys.argv) > 1: run(sys.argv[1])