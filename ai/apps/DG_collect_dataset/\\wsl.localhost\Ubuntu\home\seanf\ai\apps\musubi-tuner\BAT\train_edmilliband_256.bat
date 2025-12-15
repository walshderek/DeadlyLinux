@echo off
set "WAN_ROOT=C:\AI\apps\musubi-tuner"
set "CFG=C:\AI\apps\musubi-tuner\TOML\edmilliband_256_win.toml"
set "OUT=%WAN_ROOT%\outputs\edmilliband"
set "LOGDIR=%WAN_ROOT%\logs"
set "C_MODEL_BASE=\\wsl.localhost\Ubuntu\home\seanf\ai\models"
set "DIT_LOW=%C_MODEL_BASE%\diffusion-models\Wan\Wan2.2\14B\Wan_2_2_I2V\fp16\wan2.2_t2v_low_noise_14B_fp16.safetensors"
set "DIT_HIGH=%C_MODEL_BASE%\diffusion-models\Wan\Wan2.2\14B\Wan_2_2_I2V\fp16\wan2.2_t2v_high_noise_14B_fp16.safetensors"
set "VAE=%C_MODEL_BASE%\vae\wan_2.1_vae.pth"
set "T5=%C_MODEL_BASE%\clip\models_t5_umt5-xxl-enc-bf16.pth"
call %WAN_ROOT%\venv\scripts\activate
python wan_cache_latents.py --dataset_config "%CFG%" --vae "%VAE%" --vae_dtype float16 --vae_cache_cpu
python wan_cache_text_encoder_outputs.py --dataset_config "%CFG%" --t5 "%T5%" --batch_size 16 --fp8_t5
accelerate launch --num_processes 1 "wan_train_network.py" ^
  --dataset_config "%CFG%" ^
  --output_dir "%OUT%" ^
  --output_name "edmilliband" ^
  --dit "%DIT_LOW%" ^
  --dit_high_noise "%DIT_HIGH%" ^
  --fp8_base ^
  --fp8_scaled ^
  --fp8_t5 ^
  --gradient_accumulation_steps 1 ^
  --learning_rate 0.0001 ^
  --optimizer_type AdamW8bit ^
  --max_train_epochs 35 ^
  --save_every_n_epochs 5 ^
  --t5 "%T5%" ^
  --vae "%VAE%" ^
  --vae_dtype float16 ^
  --timestep_boundary 875 ^
  --timestep_sampling logsnr ^
  --vae_cache_cpu ^
  --persistent_data_loader_workers ^
  --sdpa
pause
