@echo off
setlocal enabledelayedexpansion

:: --- PATH CONFIGURATION ---
set "WAN_ROOT=C:\AI\apps\musubi-tuner"
set "CFG=C:\AI\apps\musubi-tuner\files\tomls\theresa_may_win.toml"
set "DIT_LOW=C:/AI/models/diffusion_models/Wan/Wan2.2/14B/Wan_2_2_T2V/bf16/Wan-2.2-T2V-Low-Noise-BF16.safetensors"
set "DIT_HIGH=C:/AI/models/diffusion_models/Wan/Wan2.2/14B/Wan_2_2_T2V/bf16/Wan-2.2-T2V-High-Noise-BF16.safetensors"
set "VAE=C:/AI/models/vae/WAN/Wan2.1_VAE.pth"
set "T5=C:/AI/models/clip/models_t5_umt5-xxl-enc-bf16.pth"
set "OUT=C:\AI\apps\musubi-tuner\outputs\theresa_may"
set "OUTNAME=theresa_may"
set "LOGDIR=C:\AI\apps\musubi-tuner\logs"

:: --- ENVIRONMENT ---
cd /d "%WAN_ROOT%"
if exist "venv\Scripts\activate.bat" (
    call "venv\Scripts\activate.bat"
) else (
    echo WARNING: venv not found, using system Python
)

:: --- START TRAINING ---
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
    --max_train_epochs 35 ^
    --min_timestep 0 ^
    --mixed_precision bf16 ^
    --network_alpha 16 ^
    --network_dim 16 ^
    --network_module "networks.lora_wan" ^
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
