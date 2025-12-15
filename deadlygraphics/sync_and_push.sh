#!/usr/bin/env bash
set -e

# --- PATHS (CRYSTAL CLEAR) ---
SANDBOX_DIR="$HOME/deadlygraphics/ai"
REPO_DIR="/mnt/c/Users/seanf/Documents/GitHub/DeadlyLinux"
CRED_FILE="/mnt/c/AI/credentials.json"

echo "DIAMOND SMASH: SYNC & PUSH PROTOCOL"

# --- 1. AUTO-AUTH (NO INTERACTIVE PROMPTS) ---
if [ -f "$CRED_FILE" ]; then
    echo "Reading Credentials from C: Drive..."
    # Python extraction to handle JSON safely
    read -r GH_USER GH_TOKEN <<< $(python3 -c "import json; d=json.load(open('$CRED_FILE')); print(f\"{d['github']['user']} {d['github']['token']}\")")
    
    if [ ! -z "$GH_TOKEN" ]; then
        git config --global credential.helper store
        echo "https://$GH_USER:$GH_TOKEN@github.com" > ~/.git-credentials
        chmod 600 ~/.git-credentials
        echo "Auth Configured."
    else
        echo "Token extraction failed."
    fi
else
    echo "Credentials file not found at $CRED_FILE. Push might fail."
fi

# --- 2. THE SYNC (SANDBOX -> REPO) ---
echo "Syncing Apps to Windows Repo..."
mkdir -p "$REPO_DIR/ai"

# Rsync flags: -a (archive), -v (verbose).
# We EXCLUDE the venv and hidden git files to avoid corruption.
rsync -av --delete \
    --exclude 'venv' \
    --exclude '__pycache__' \
    --exclude '*.pyc' \
    --exclude '.git' \
    "$SANDBOX_DIR/" "$REPO_DIR/ai/"

echo "Files Synced."

# --- 3. THE PUSH (FROM THE REPO ROOT) ---
echo "Initiating Git Push..."
cd "$REPO_DIR"

echo "Current Status:"
git status

git add .
git commit -m "feat: Diamond Smash Sync - Apps & Infrastructure" || echo "Nothing to commit"
git push origin main

echo "MISSION COMPLETE. CHECK GITHUB."
