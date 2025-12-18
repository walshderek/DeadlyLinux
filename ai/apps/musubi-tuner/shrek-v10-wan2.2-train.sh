#!/bin/bash
set -e

# --- PATHS ---
WAN_ROOT="/home/seanf/deadlygraphics/ai/apps/musubi-tuner"
CFG="/home/seanf/deadlygraphics/ai/apps/musubi-tuner/shrek-v10-wan2.2-wsl.toml"

# --- OUTPUTS ---
OUT="$WAN_ROOT/outputs/shrek-v10-wan2.2"
LOGDIR="$WAN_ROOT/logs"
OUTNAME="shrek-v10-wan2.2"

# --- MODELS (WSL paths to Windows models) ---
DIT_LOW="/mnt/c/AI/models/diffusion_models/Wan/Wan2.2/14B/Wan_2_2_T2V/fp16/wan2.2_t2v_low_noise_14B_fp16.safetensors"
DIT_HIGH="/mnt/c/AI/models/diffusion_models/Wan/Wan2.2/14B/Wan_2_2_T2V/fp16/wan2.2_t2v_high_noise_14B_fp16.safetensors"
VAE="/mnt/c/AI/models/vae/WAN/wan_2.1_vae.pth"
T5="/mnt/c/AI/models/clip/models_t5_umt5-xxl-enc-bf16.pth"

# --- EXECUTION ---
cd "$WAN_ROOT"

# Activate virtual environment
source venv/bin/activate

# Create output directories
mkdir -p "$OUT"
mkdir -p "$LOGDIR"

echo "============================================"
echo "Starting VAE Latent Cache..."
echo "============================================"
python wan_cache_latents.py --dataset_config "$CFG" --vae "$VAE" --vae_dtype float16

echo "============================================"
echo "Starting T5 Text Encoder Cache..."
echo "============================================"
python wan_cache_text_encoder_outputs.py --dataset_config "$CFG" --t5 "$T5" --batch_size 16 --fp8_t5

echo "============================================"
echo "Starting LoRA Training..."
echo "============================================"
accelerate launch --num_processes 1 "wan_train_network.py" \
  --dataset_config "$CFG" \
  --discrete_flow_shift 3 \
  --dit "$DIT_LOW" \
  --dit_high_noise "$DIT_HIGH" \
  --fp8_base \
  --fp8_scaled \
  --fp8_t5 \
  --gradient_accumulation_steps 1 \
  --gradient_checkpointing \
  --img_in_txt_in_offloading \
  --learning_rate 0.0001 \
  --log_with tensorboard \
  --logging_dir "$LOGDIR" \
  --lr_scheduler cosine \
  --lr_warmup_steps 100 \
  --max_data_loader_n_workers 6 \
  --max_train_epochs 35 \
  --max_timestep 1000 \
  --min_timestep 0 \
  --mixed_precision fp16 \
  --network_alpha 8 \
  --network_args "verbose=True" "exclude_patterns=[]" \
  --network_dim 8 \
  --network_module networks.lora_wan \
  --offload_inactive_dit \
  --optimizer_type AdamW8bit \
  --output_dir "$OUT" \
  --output_name "$OUTNAME" \
  --persistent_data_loader_workers \
  --save_every_n_epochs 5 \
  --seed 42 \
  --t5 "$T5" \
  --task t2v-A14B \
  --timestep_boundary 875 \
  --timestep_sampling logsnr \
  --vae "$VAE" \
  --vae_cache_cpu \
  --vae_dtype float16 \
  --sdpa

echo "============================================"
echo "Training Complete!"
echo "============================================"
