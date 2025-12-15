#!/usr/bin/env bash
set -euo pipefail

# CONFIG
PY="$HOME/mambaforge/envs/deadlygraphics/bin/python"
PIP="$HOME/mambaforge/envs/deadlygraphics/bin/pip"
WORKDIR="$HOME/deadlygraphics/ai"
LOG_DIR="$HOME/deadlygraphics/deployment_logs"

mkdir -p "$LOG_DIR"
STATUS="$LOG_DIR/deployment_status.md"
CONFLICTS="$LOG_DIR/deployment_conflicts.log"

# RESET LOGS
: > "$STATUS"
: > "$CONFLICTS"

echo "# Deployment Status Report" > "$STATUS"
echo "Generated on $(date)" >> "$STATUS"

# 1. CHECK ENGINE (TORCH/TF)
echo "## 1. Engine Room Check" | tee -a "$STATUS"
if [ -x "$PY" ]; then
    echo "Python path: $PY" >> "$STATUS"
    "$PY" -c "import sys; print(f'- Python: {sys.version.split()[0]}')" >> "$STATUS" 2>&1 || true
    "$PY" -c "import torch; print(f'- PyTorch: {torch.__version__} (CUDA: {torch.cuda.is_available()})')" >> "$STATUS" 2>&1 || echo "- PyTorch: MISSING" >> "$STATUS"
    "$PY" -c "import tensorflow as tf; print(f'- TensorFlow: {tf.__version__}')" >> "$STATUS" 2>&1 || echo "- TensorFlow: MISSING" >> "$STATUS"
else
    echo "CRITICAL: Python binary not found at $PY" | tee -a "$STATUS"
    exit 1
fi

# 2. AUDIT REPOS
echo -e "\n## 2. Repo Audit" | tee -a "$STATUS"
repos=("ai-toolkit" "musubi-tuner" "OneTrainer" "ComfyUI")

for r in "${repos[@]}"; do
    repo_path="$WORKDIR/$r"
    echo -e "\n### Repo: $r" >> "$STATUS"
    
    if [ -d "$repo_path" ]; then
        echo "- **Status**: FOUND at $repo_path" >> "$STATUS"
        
        # REQUIREMENTS INSTALL (FILTERED)
        if [ -f "$repo_path/requirements.txt" ]; then
            echo "- requirements.txt: FOUND" >> "$STATUS"
            tmp_req="/tmp/filtered_${r}_requirements.txt"
            
            # THE DIAMOND FILTER: Removes torch, tf, nvidia, etc. to prevent downgrades
            grep -Ev "^(\s*#|\s*$|torch|tensorflow|triton|torchvision|torchaudio|xformers|sage-attention|nvidia-|cuda|cupy)" "$repo_path/requirements.txt" > "$tmp_req" || true
            
            echo "- Installing filtered requirements..." >> "$STATUS"
            if "$PIP" install --no-deps -r "$tmp_req" >> "$repo_path/install.log" 2>&1; then
                echo "- **Install**: SUCCESS (Filtered)" >> "$STATUS"
            else
                echo "- **Install**: FAILED (See $repo_path/install.log)" >> "$STATUS"
                echo "FAILED: $r" >> "$CONFLICTS"
            fi
        else
            echo "- requirements.txt: MISSING" >> "$STATUS"
        fi

        # ACCELERATION CHECK (Xformers/Sage)
        echo "- **Acceleration Check**:" >> "$STATUS"
        if "$PIP" show xformers > /dev/null 2>&1; then
            echo "  - xformers: INSTALLED" >> "$STATUS"
        else
            echo "  - xformers: MISSING" >> "$STATUS"
        fi
        if "$PIP" show "sage-attention" > /dev/null 2>&1; then
            echo "  - sage-attention: INSTALLED" >> "$STATUS"
        else
            echo "  - sage-attention: MISSING" >> "$STATUS"
        fi

        # Runtime import checks
        echo "- **Runtime import checks**:" >> "$STATUS"
        "$PY" - <<PY_EOF >> "$STATUS" 2>&1 || true
import sys
for mod,name in [("xformers","xformers"),("sage_attention","sage-attention"),("sage","sage-attention")]:
    try:
        __import__(mod)
        print(name, 'import_ok')
    except Exception as e:
        print(name, 'import_fail', repr(e))
PY_EOF

    else
        echo "- **Status**: MISSING (Folder not found)" >> "$STATUS"
    fi
done

# Copy logs to repo root for Windows access if mount exists
if [ -d "/mnt/c/Users/seanf/Documents/GitHub/DeadlyLinux" ]; then
    cp -a "$LOG_DIR" /mnt/c/Users/seanf/Documents/GitHub/DeadlyLinux/ || true
fi

echo -e "\nAudit Complete. Logs saved to: $STATUS"
