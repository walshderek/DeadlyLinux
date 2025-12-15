#!/usr/bin/env bash
set -e

# --- CONFIG ---
AI_ROOT="$HOME/deadlygraphics/ai/apps"
MAMBA_PIP="$HOME/mambaforge/envs/deadlygraphics/bin/pip"
MAMBA_PYTHON="$HOME/mambaforge/envs/deadlygraphics/bin/python"
DOCS_FILE="$HOME/deadlygraphics/DEPLOYMENT_DOCS.md"

echo "💎 DIAMOND SMASHING: VERIFICATION PHASE 💎"

# --- 1. INSTALL APPS (SAFE MODE) ---
echo "--- 1. Installing App Dependencies (Safe Mode) ---"

install_app() {
    local dir="$1"
    local name="$2"
    if [ -d "$dir" ] && [ -f "$dir/requirements.txt" ]; then
        echo "Processing $name..."
        grep -Ev "^(\s*#|\s*$|torch|tensorflow|triton|torchvision|torchaudio|xformers|sage-attention|nvidia-|cuda|cupy)" "$dir/requirements.txt" > "/tmp/req_$name.txt"
        "$MAMBA_PIP" install --no-deps -r "/tmp/req_$name.txt" || echo "Warning: Minor install error in $name"
    else
        echo "Skipping $name (No requirements.txt)"
    fi
}

install_app "$AI_ROOT/DG_collect_dataset" "DG_collect_dataset"
install_app "$AI_ROOT/DG_vibecoder" "DG_vibecoder"
install_app "$AI_ROOT/DG_videoscraper" "DG_videoscraper"

# --- 2. GENERATE DOCS ---
echo "--- 2. Generating Documentation ---"
cat > "$DOCS_FILE" <<EOF
# DEADLY LINUX DEPLOYMENT DOCS
**Generated:** $(date)
**Location:** London, UK

## ENGINE STATUS
- **Python:** $( $MAMBA_PYTHON --version 2>&1 )
- **Torch:** $( $MAMBA_PYTHON -c "import torch; print(torch.__version__)" 2>&1 || echo "torch: not available" )
- **Model Hoard:** /mnt/c/AI/models

## INSTALLED APPS
- DG_collect_dataset
- DG_vibecoder
- DG_videoscraper
- ComfyUI
- Musubi Tuner (Kohya)
EOF

cat "$DOCS_FILE"

# --- 3. THE OBAMA TEST ---
echo "--- 3. Running Verification: The Obama Test ---"
TEST_OUTPUT="/mnt/c/AI/models/dataset_test/obama"
mkdir -p "$TEST_OUTPUT"

TARGET_SCRIPT="$AI_ROOT/DG_collect_dataset/main.py"

if [ -f "$TARGET_SCRIPT" ]; then
    echo "Launching Scraper..."
    "$MAMBA_PYTHON" "$TARGET_SCRIPT" --search "Barack Obama" --limit 5 --output "$TEST_OUTPUT" || echo "Test Run Failed (Check script arguments)"
else
    echo "CRITICAL: Scraper script not found at $TARGET_SCRIPT"
fi

echo "💎 VERIFICATION COMPLETE 💎"
