#!/usr/bin/env bash
set -euo pipefail

LOG=/mnt/c/Users/seanf/Documents/GitHub/DeadlyLinux/mamba_install.log

echo "=== FINALIZE ENV START ===" | tee -a "$LOG"

echo "Installing mamba from conda-forge (override channels)" | tee -a "$LOG"
"$HOME/mambaforge/bin/conda" install -n base -c conda-forge mamba -y --override-channels 2>&1 | tee -a "$LOG" || true

if [ -x "$HOME/mambaforge/bin/mamba" ]; then
  echo "Using mamba to create deadlygraphics env" | tee -a "$LOG"
  "$HOME/mambaforge/bin/mamba" create -n deadlygraphics python=3.11 -y 2>&1 | tee -a "$LOG" || true
else
  echo "Falling back to conda to create deadlygraphics env" | tee -a "$LOG"
  "$HOME/mambaforge/bin/conda" create -n deadlygraphics -c conda-forge python=3.11 -y --override-channels 2>&1 | tee -a "$LOG" || true
fi

if [ -f "$HOME/deadlygraphics/requirements.txt" ]; then
  echo "Installing pip requirements from deadlygraphics" | tee -a "$LOG"
  "$HOME/mambaforge/bin/conda" run -n deadlygraphics pip install -r "$HOME/deadlygraphics/requirements.txt" 2>&1 | tee -a "$LOG" || true
else
  echo "No requirements found in deadlygraphics" | tee -a "$LOG"
fi

echo "=== FINALIZE ENV END ===" | tee -a "$LOG"
