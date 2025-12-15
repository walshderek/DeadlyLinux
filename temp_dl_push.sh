#!/usr/bin/env bash
set -euo pipefail

TEMP_DIR=/home/seanf/temp_deadlylinux_fix
rm -rf "$TEMP_DIR"
mkdir -p "$TEMP_DIR"

# Copy workspace excluding git metadata and virtualenvs
rsync -a \
  --exclude='.git' \
  --exclude='.venv' \
  --exclude='.DS_Store' \
  /mnt/c/Users/seanf/Documents/GitHub/DeadlyLinux/ "$TEMP_DIR/"

cd "$TEMP_DIR"
git init -b main
git remote add origin git@github.com:walshderek/DeadlyLinux.git
git config user.name "seanf"
git config user.email "seanf@example.com"
git add -A
git commit -m "Final Sync: DG tools and briefing (linux clean copy)" --allow-empty
GIT_SSH_COMMAND="ssh -i /home/seanf/.ssh/id_rsa -o StrictHostKeyChecking=no" git push -f origin main
