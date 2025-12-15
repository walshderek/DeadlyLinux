#!/bin/bash
WAN_DIR="/home/seanf/ai/apps/musubi-tuner"
CFG="/home/seanf/ai/apps/musubi-tuner/TOML/edmilliband_256_wsl.toml"
OUT="${WAN_DIR}/outputs/edmilliband"

source ${WAN_DIR}/venv/bin/activate

accelerate launch --num_processes 1 "wan_train_network.py" \
  --dataset_config "${CFG}" \
  --output_dir "${OUT}" \
  --output_name "edmilliband" \
  --discrete_flow_shift 3 \
  --fp8_base \
  --fp8_scaled \
  --fp8_t5 \
  --gradient_accumulation_steps 1 \
  --learning_rate 0.0001 \
  --optimizer_type AdamW8bit \
  --max_train_epochs 35 \
  --save_every_n_epochs 5 \
  --timestep_boundary 875 \
  --timestep_sampling logsnr \
  --vae_cache_cpu \
  --persistent_data_loader_workers \
  --vae_dtype float16 \
  --sdpa
