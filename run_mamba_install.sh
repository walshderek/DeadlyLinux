#!/usr/bin/env bash
set -euo pipefail

LOG_WIN="/mnt/c/Users/seanf/Documents/GitHub/DeadlyLinux/mamba_install.log"
rm -f "$LOG_WIN"

echo "=== START MAMBA INSTALL ===" | tee -a "$LOG_WIN"

echo "Downloading Mambaforge installer..." | tee -a "$LOG_WIN"
wget -O /tmp/Mambaforge.sh "https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh" 2>&1 | tee -a "$LOG_WIN"

if [ -f /tmp/Mambaforge.sh ]; then
  echo "Installer downloaded. size: $(stat -c%s /tmp/Mambaforge.sh) bytes" | tee -a "$LOG_WIN"
  echo "Running installer (silent)..." | tee -a "$LOG_WIN"
  bash /tmp/Mambaforge.sh -b -p "$HOME/mambaforge" 2>&1 | tee -a "$LOG_WIN"
  rm -f /tmp/Mambaforge.sh
else
  echo "Download failed" | tee -a "$LOG_WIN"
  exit 1
fi

echo "Initializing conda and installing mamba..." | tee -a "$LOG_WIN"
"$HOME/mambaforge/bin/conda" init bash 2>&1 | tee -a "$LOG_WIN" || true
"$HOME/mambaforge/bin/conda" install -n base -c conda-forge mamba -y 2>&1 | tee -a "$LOG_WIN" || true

echo "Creating deadlygraphics env..." | tee -a "$LOG_WIN"
"$HOME/mambaforge/bin/mamba" create -n deadlygraphics python=3.11 -y 2>&1 | tee -a "$LOG_WIN" || true

echo "Installing pip requirements from cloned repo (if present)..." | tee -a "$LOG_WIN"
if [ -f "$HOME/deadlygraphics/requirements.txt" ]; then
  "$HOME/mambaforge/bin/mamba" run -n deadlygraphics pip install -r "$HOME/deadlygraphics/requirements.txt" 2>&1 | tee -a "$LOG_WIN" || true
elif [ -f "/mnt/c/Users/seanf/Documents/GitHub/DeadlyLinux/requirements.txt" ]; then
  "$HOME/mambaforge/bin/mamba" run -n deadlygraphics pip install -r "/mnt/c/Users/seanf/Documents/GitHub/DeadlyLinux/requirements.txt" 2>&1 | tee -a "$LOG_WIN" || true
else
  echo "No requirements found; skipping." | tee -a "$LOG_WIN"
fi

echo "=== FINISHED MAMBA INSTALL ===" | tee -a "$LOG_WIN"
