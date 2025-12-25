@echo off
setlocal enabledelayedexpansion

:: ============================================
:: MUSUBI-TUNER TEMPLATE PIPELINE
:: ============================================

:: --- PATH CONFIGURATION ---
set "WAN_ROOT=@WAN@"
set "CFG=@CFG@"
set "DIT_LOW=@DIT_LOW@"
set "DIT_HIGH=@DIT_HIGH@"
set "VAE=@VAE@"
set "T5=@T5@"
set "OUT=@OUT@"
set "OUTNAME=@OUTNAME@"
set "LOGDIR=@LOGDIR@"

:: --- ENVIRONMENT ---
set "PYTHON_EXE=%WAN_ROOT%\venv\Scripts\python.exe"
cd /d "%WAN_ROOT%"
call "venv\Scripts\activate.bat"

:: ============================================
:: STEP 1: CACHE VAE LATENTS
:: ============================================
echo STEP 1/3: Caching Image Latents (VAE)

"%PYTHON_EXE%" "wan_cache_latents.py" ^
    --dataset_config "%CFG%" ^
    --vae "%VAE%" ^
    --vae_dtype bfloat16 ^
    --vae_cache_cpu

if %ERRORLEVEL% neq 0 goto :error

:: ============================================
:: STEP 2: CACHE TEXT ENCODER OUTPUTS
:: ============================================
echo STEP 2/3: Caching Text Encoder Outputs (T5)

"%PYTHON_EXE%" "wan_cache_text_encoder_outputs.py" ^
    --dataset_config "%CFG%" ^
    --t5 "%T5%" ^
    --fp8_t5 ^
    --batch_size 16

if %ERRORLEVEL% neq 0 goto :error

:: ============================================
:: STEP 3: START TRAINING
:: ============================================
echo STEP 3/3: Starting Training

"%PYTHON_EXE%" -m accelerate.commands.launch --num_processes 1 "wan_train_network.py" ^
    --dataset_config "%CFG%" ^
    --discrete_flow_shift 3 ^
    --dit "%DIT_LOW%" ^
    --dit_high_noise "%DIT_HIGH%" ^
    --fp8_base ^
    --fp8_scaled ^
    --fp8_t5 ^
    --gradient_accumulation_steps @GRAD_ACCUM@ ^
    --gradient_checkpointing ^
    --img_in_txt_in_offloading ^
    --learning_rate @LEARNING_RATE@ ^
    --max_grad_norm 1.0 ^
    --log_with tensorboard ^
    --logging_dir "%LOGDIR%" ^
    --lr_scheduler cosine ^
    --lr_warmup_steps 200 ^
    --max_data_loader_n_workers @N_WORKERS@ ^
    --max_timestep 1000 ^
    --max_train_epochs @EPOCHS@ ^
    --min_timestep 0 ^
    --mixed_precision bf16 ^
    --network_alpha @NETWORK_ALPHA@ ^
    --network_dim @NETWORK_DIM@ ^
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

if %ERRORLEVEL% neq 0 goto :error

echo TRAINING COMPLETE
pause
exit /b 0

:error
echo [!] AN ERROR OCCURRED
pause
exit /b 1