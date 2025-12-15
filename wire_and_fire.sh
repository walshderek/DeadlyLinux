#!/usr/bin/env bash
set -e

# --- CONFIG ---
AI_ROOT="$HOME/deadlygraphics/ai"
MODEL_HOARD="/mnt/c/AI/models"
MAMBA_PIP="$HOME/mambaforge/envs/deadlygraphics/bin/pip"

echo "💎 DIAMOND SMASHING: WIRE AND FIRE PROTOCOL 💎"

# --- 1. SAFE DEPENDENCY INSTALL (FILTERED) ---
install_safe() {
    local dir=$1
    local name=$2
    if [ -d "$dir" ]; then
        echo "Processing $name..."
        if [ -f "$dir/requirements.txt" ]; then
            # FILTER: Remove heavy packages (torch, nvidia, cuda) to protect env
            grep -Ev "^(\\s*#|\\s*$|torch|tensorflow|triton|torchvision|torchaudio|xformers|sage-attention|nvidia-|cuda|cupy)" "$dir/requirements.txt" > "/tmp/req_$name.txt"
            "$MAMBA_PIP" install --no-deps -r "/tmp/req_$name.txt" || echo "Warning: Minor install error in $name"
        else
            echo "No requirements.txt. Attempting editable install..."
            cd "$dir" && "$MAMBA_PIP" install --no-deps -e . || echo "Skipping."
            cd - > /dev/null
        fi
    fi
}

install_safe "$AI_ROOT/ComfyUI" "ComfyUI"
install_safe "$AI_ROOT/ai-toolkit" "AI-Toolkit"
install_safe "$AI_ROOT/OneTrainer" "OneTrainer"
install_safe "$AI_ROOT/apps/musubi-tuner" "Musubi Tuner"

# --- 2. RE-PATHING (THE DIAMOND RULE) ---
echo "--- Wiring Paths to $MODEL_HOARD ---"

# A. ComfyUI
COMFY_DIR="$AI_ROOT/ComfyUI"
if [ -d "$COMFY_DIR" ]; then
    cp -n "$COMFY_DIR/extra_model_paths.yaml.example" "$COMFY_DIR/extra_model_paths.yaml" || true
    # FORCE base_path update
    sed -i "s|^base_path:.*|base_path: $MODEL_HOARD|g" "$COMFY_DIR/extra_model_paths.yaml" || true
    echo "ComfyUI wired to C: drive."
fi

# --- 3. GENERATE POC LAUNCHER ---
echo "--- Generating Launcher ---"
cat > "$HOME/deadlygraphics/run_poc.sh" <<EOF
#!/usr/bin/env bash
echo "💎 STARTING POC 💎"
source \$HOME/mambaforge/bin/activate deadlygraphics

echo "1. ACCELERATION CHECK:"
python -c "import torch; print(f'Torch: {torch.__version__} (CUDA: {torch.cuda.is_available()})')"
python -c "import xformers; print('Xformers: INSTALLED')" || echo "Xformers: NOT FOUND"

echo "2. LAUNCHING COMFYUI (Listen Mode)..."
echo "Open Browser to: http://localhost:8188"
cd "$COMFY_DIR"
python main.py --listen --port 8188
EOF
chmod +x "$HOME/deadlygraphics/run_poc.sh"

echo "✅ DONE. Run ./run_poc.sh now."
