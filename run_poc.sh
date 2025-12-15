#!/usr/bin/env bash
echo "💎 STARTING POC 💎"
source $HOME/mambaforge/bin/activate deadlygraphics

echo "1. ACCELERATION CHECK:"
python -c "import torch; print(f'Torch: {torch.__version__} (CUDA: {torch.cuda.is_available()})')"
python -c "import xformers; print('Xformers: INSTALLED')" || echo "Xformers: NOT FOUND"

echo "2. LAUNCHING COMFYUI (Listen Mode)..."
echo "Open Browser to: http://localhost:8188"
cd "/home/seanf/deadlygraphics/ai/ComfyUI"
python main.py --listen --port 8188
