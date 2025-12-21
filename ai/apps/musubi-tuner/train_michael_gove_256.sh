#!/usr/bin/env bash
set -euo pipefail

WAN_ROOT="/home/seanf/ai/apps/musubi-tuner"
CFG="/home/seanf/deadlygraphics/ai/apps/musubi-tuner/files/tomls/michael_gove_256_linux.toml"

OUT="${WAN_ROOT}/outputs/michael_gove"
LOGDIR="${WAN_ROOT}/logs"

DIT_LOW="C:\AI\models\diffusion_models\Wan\Wan2.2\14B\Wan_2_2_T2V\fp16\wan2.2_t2v_low_noise_14B_fp16.safetensors"
DIT_HIGH="C:\AI\models\diffusion_models\Wan\Wan2.2\14B\Wan_2_2_T2V\fp16\wan2.2_t2v_high_noise_14B_fp16.safetensors"
VAE="C:\AI\models\vae\WAN\Wan2.1_VAE.pth"
T5="C:\AI\models\clip\models_t5_umt5-xxl-enc-bf16.pth"

cd "${WAN_ROOT}"
source venv/bin/activate

mkdir -p "${OUT}" "${LOGDIR}"

python wan_cache_latents.py --dataset_config "${CFG}" --vae "${VAE}" --vae_dtype float16

python wan_cache_text_encoder_outputs.py --dataset_config "${CFG}" --t5 "${T5}" --batch_size 16 --fp8_t5

accelerate launch --num_processes 1 \
    wan_train_network.py \
    --dataset_config "${CFG}" \
    --discrete_flow_shift 3 \
    --dit "${DIT_LOW}" \
    --dit_high_noise "${DIT_HIGH}" \
    --fp8_base \
    --fp8_scaled \
    --fp8_t5 \
    --gradient_accumulation_steps 1 \
    --gradient_checkpointing \
    --img_in_txt_in_offloading \
    --learning_rate 0.00001 \
    --logging_dir "${LOGDIR}" \
    --lr_scheduler cosine \
    --lr_warmup_steps 100 \
    --max_data_loader_n_workers 6 \
    --max_train_epochs 35 \
    --save_every_n_epochs 5 \
    --seed 42 \
    --t5 "${T5}" \
    --task t2v-A14B \
    --timestep_boundary 875 \
    --timestep_sampling logsnr \
    --vae "${VAE}" \
    --vae_cache_cpu \
    --vae_dtype float16 \
    --network_module networks.lora_wan \
    --network_dim 16 \
    --network_alpha 16 \
    --mixed_precision fp16 \
    --min_timestep 0 \
    --max_timestep 1000 \
    --offload_inactive_dit \
    --optimizer_type AdamW8bit \
    --sdpa
