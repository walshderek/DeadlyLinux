#!/usr/bin/env bash
set -euo pipefail

REQ=/mnt/c/Users/seanf/Documents/GitHub/DeadlyLinux/requirements.txt
if [ -f "$REQ" ]; then
  echo "Installing repo-level requirements from $REQ"
  "$HOME/mambaforge/bin/mamba" run -n deadlygraphics pip install -r "$REQ"
else
  echo "No repo-level requirements.txt found"
fi
