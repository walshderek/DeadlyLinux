@echo off
SETLOCAL enabledelayedexpansion

REM --- DIAMOND SMASHING MACHINE: AUTOMATED RUN ---
set "WAN_ROOT=C:\AI\apps\musubi-tuner"
set "C_MODEL_BASE=C:\AI\models"
set "CFG=%WAN_ROOT%\dataset_Barack_Obama.toml"
set "OUT=%WAN_ROOT%\outputs\Barack_Obama"
set "LOGDIR=%WAN_ROOT%\logs"
set "OUTNAME=Barack_Obama"

REM --- MODEL PATHS (CORRECTED T2V) ---
set "DIT_LOW=%C_MODEL_BASE%\diffusion_models\Wan\Wan2.2\14B\Wan_2_2_T2V\fp16\wan2.2_t2v_low_noise_14B_fp16.safetensors"
set "DIT_HIGH=%C_MODEL_BASE%\diffusion_models\Wan\Wan2.2\14B\Wan_2_2_T2V\fp16\wan2.2_t2v_high_noise_14B_fp16.safetensors"
set "VAE=%C_MODEL_BASE%\vae\WAN\wan_2.1_vae.pth"
set "T5=%C_MODEL_BASE%\clip\models_t5_umt5-xxl-enc-bf16.pth"

REM --- ACTIVATE VENV ---
cd /d "%WAN_ROOT%"
call venv\scripts\activate

REM --- CREATE DIRS ---
if not exist "%OUT%" mkdir "%OUT%"
if not exist "%LOGDIR%" mkdir "%LOGDIR%"

REM --- 1. CACHE LATENTS ---
echo Starting VAE Latent Cache...
python wan_cache_latents.py ^
  --dataset_config "%CFG%" ^
  --vae "%VAE%" ^
  --vae_dtype float16

REM --- 2. CACHE TEXT ---
echo Starting T5 Text Cache...
python wan_cache_text_encoder_outputs.py ^
  --dataset_config "%CFG%" ^
  --t5 "%T5%" ^
  --batch_size 16 ^
  --fp8_t5

REM --- 3. TRAIN (BF16 SAFETY MODE) ---
echo Starting Training...
accelerate launch --num_processes 1 "wan_train_network.py" ^
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
  --log_with tensorboard ^
  --logging_dir "%LOGDIR%" ^
  --lr_scheduler cosine ^
  --lr_warmup_steps 100 ^
  --max_data_loader_n_workers 2 ^
  --max_train_epochs 35 ^
  --max_timestep 1000 ^
  --min_timestep 0 ^
  --mixed_precision bf16 ^
  --network_alpha 8 ^
  --network_args "verbose=True" "exclude_patterns=[]" ^
  --network_dim 8 ^
  --network_module networks.lora_wan ^
  --offload_inactive_dit ^
  --optimizer_type AdamW8bit ^
  --output_dir "%OUT%" ^
  --output_name "%OUTNAME%" ^
  --save_every_n_epochs 5 ^
  --seed 42 ^
  --t5 "%T5%" ^
  --task t2v-A14B ^
  --timestep_boundary 875 ^
  --timestep_sampling logsnr ^
  --vae "%VAE%" ^
  --vae_cache_cpu ^
  --vae_dtype float16 ^
  --sdpa

echo 💎 DIAMOND SMASHED. TRAINING COMPLETE. 💎
pause
ENDLOCAL
