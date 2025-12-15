#!/usr/bin/env bash
set -euo pipefail

# Linux bootstrap: installs Mambaforge, creates env, clones DeadlyGraphics, installs requirements
REPO_DIR="/mnt/c/Users/seanf/Documents/GitHub/DeadlyLinux"
INSTALL_PREFIX="$HOME/mambaforge"
ENV_NAME="deadlygraphics"

echo "Starting Linux bootstrap inside DeadlyLinux..."

sudo apt-get update -y
sudo apt-get install -y curl wget git sudo ca-certificates build-essential

if [ -f "$REPO_DIR/mambaforge.sh" ]; then
  echo "Running bundled mambaforge installer..."
  bash "$REPO_DIR/mambaforge.sh" -b -p "$INSTALL_PREFIX"
else
  echo "Downloading Mambaforge installer..."
  wget -qO /tmp/Mambaforge.sh "https://github.com/conda-forge/miniforge/releases/latest/download/Mambaforge-Linux-x86_64.sh"
  bash /tmp/Mambaforge.sh -b -p "$INSTALL_PREFIX"
fi

export PATH="$INSTALL_PREFIX/bin:$PATH"

if ! command -v mamba >/dev/null 2>&1; then
  echo "mamba not found; trying conda..."
fi

# Setup pip cache for offline/faster installs
PIP_CACHE="/mnt/c/linuxdownloads"
mkdir -p "$PIP_CACHE"
export PIP_FIND_LINKS="$PIP_CACHE"

echo "Creating conda environment: $ENV_NAME (python 3.11)"
mamba create -n "$ENV_NAME" python=3.11 -y || true

if [ ! -d "$HOME/deadlygraphics" ]; then
  if [ -d "$REPO_DIR/DeadlyGraphics" ]; then
    echo "Copying local DeadlyGraphics into home directory..."
    cp -r "$REPO_DIR/DeadlyGraphics" "$HOME/deadlygraphics"
  else
    echo "Cloning DeadlyGraphics from GitHub..."
    git clone https://github.com/walshderek/DeadlyGraphics.git "$HOME/deadlygraphics" || echo "Clone failed or repo private; skipping clone."
  fi
fi

if [ -f "$HOME/deadlygraphics/requirements.txt" ]; then
  echo "Installing Python requirements from deadlygraphics requirements.txt"
  echo "Checking cache at $PIP_CACHE first..."
  mamba run -n "$ENV_NAME" pip install --find-links "$PIP_CACHE" -r "$HOME/deadlygraphics/requirements.txt"
  # Save wheels to cache for next time
  mamba run -n "$ENV_NAME" pip download --dest "$PIP_CACHE" -r "$HOME/deadlygraphics/requirements.txt" || true
elif [ -f "$REPO_DIR/requirements.txt" ]; then
  echo "Installing Python requirements from repo requirements.txt"
  echo "Checking cache at $PIP_CACHE first..."
  mamba run -n "$ENV_NAME" pip install --find-links "$PIP_CACHE" -r "$REPO_DIR/requirements.txt"
  mamba run -n "$ENV_NAME" pip download --dest "$PIP_CACHE" -r "$REPO_DIR/requirements.txt" || true
else
  echo "No requirements.txt found; skipping pip installs."
fi

echo "Bootstrap complete. To start coding inside WSL:"
echo "  wsl -d DeadlyLinux"
echo "Then inside WSL:"
echo "  source $INSTALL_PREFIX/bin/activate"
echo "  mamba activate $ENV_NAME"
echo "Done."
