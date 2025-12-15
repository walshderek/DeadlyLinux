#!/usr/bin/env bash
set -euo pipefail

HOME_DIR="$HOME"
DEADLY="$HOME_DIR/deadlygraphics"
AI_APPS="$DEADLY/ai/apps"
PY="$HOME_DIR/mambaforge/envs/deadlygraphics/bin/python"
PIP="$HOME_DIR/mambaforge/envs/deadlygraphics/bin/pip"
LOG="$DEADLY/secure_and_verify.log"
DOC="$DEADLY/DEPLOYMENT_DOCS.md"
MODEL_HOARD="/mnt/c/AI/models"

exec > >(tee -a "$LOG") 2>&1

echo "[secure_and_verify] Starting at $(date)"

echo "\n[STEP 1] Git secure"
REPO_ROOT="/mnt/c/Users/seanf/Documents/GitHub/DeadlyLinux"
# STEP 1: GIT SECURE
echo "\n[STEP 1] Git secure (repo root: $REPO_ROOT)"
if [ -d "$REPO_ROOT/.git" ]; then
  pushd "$REPO_ROOT" >/dev/null || true
  # mark Windows-mounted repo as safe for git operations
  git config --global --add safe.directory "$REPO_ROOT" || true
  if ! git config --global user.name >/dev/null 2>&1; then
    echo "git user.name missing — setting default (global)"
    git config --global user.name "Diamond Smasher" || true
  fi
  if ! git config --global user.email >/dev/null 2>&1; then
    echo "git user.email missing — setting default (global)"
    git config --global user.email "diamond@deadly.linux" || true
  fi

  changed=$(git status --porcelain || true)
  if [ -n "$changed" ]; then
    echo "Staging changes..."
    git add . || echo "git add failed"
    git commit -m "feat: Diamond Smashing complete - Infrastructure & Apps wired" || echo "git commit failed or no changes"
    echo "Attempting git push origin main..."
    if git rev-parse --abbrev-ref --symbolic-full-name @{u} >/dev/null 2>&1; then
      git push origin main || echo "git push failed — check remote/upstream"
    else
      echo "No upstream set for current branch; skipping push"
    fi
  else
    echo "No repo changes detected; skipping add/commit/push"
  fi
  popd >/dev/null || true
else
  echo "Git repo not found at $REPO_ROOT — skipping git steps"
fi

# STEP 2: APP INSTALLATION (Diamond Filter)
echo "\n[STEP 2] App installation (filtered)"
apps=("DG_collect_dataset" "DG_vibecoder" "DG_videoscraper")
for app in "${apps[@]}"; do
  appdir="$AI_APPS/$app"
  echo "\nProcessing $app -> $appdir"
  if [ -d "$appdir" ]; then
    if [ -f "$appdir/requirements.txt" ]; then
      echo "Found requirements.txt, applying Diamond Filter"
      grep -Ev '^(\s*#|\s*$|torch|tensorflow|nvidia|cuda)' "$appdir/requirements.txt" > "/tmp/req_$app.txt" || true
      "$PIP" install --no-deps -r "/tmp/req_$app.txt" || echo "Warning: install issues for $app"
    else
      echo "No requirements.txt found for $app; attempting editable install if pyproject or setup exists"
      if [ -f "$appdir/pyproject.toml" ] || [ -f "$appdir/setup.py" ]; then
        (cd "$appdir" && "$PIP" install --no-deps -e .) || echo "Warning: editable install failed for $app"
      else
        echo "No install entry found for $app; skipping"
      fi
    fi
  else
    echo "App folder missing: $appdir"
  fi
done

# STEP 3: DOCUMENTATION & LOGS
echo "\n[STEP 3] Generating $DOC"
{
  echo "# DEPLOYMENT DOCS"
  echo "Generated: $(date -u)"
  echo ""
  echo "## Environment"
  if [ -x "$PY" ]; then
    "$PY" -c "import sys,torch
print('- Python: {}'.format(sys.version.split()[0]))
try:
    print('- PyTorch: {} (CUDA: {})'.format(torch.__version__, torch.cuda.is_available()))
except Exception:
    print('- PyTorch: import failed')
" || true
  else
    echo "- Python binary not found at $PY"
  fi
  echo ""
  echo "## Installed Apps"
  for app in "${apps[@]}"; do
    appdir="$AI_APPS/$app"
    if [ -d "$appdir" ]; then
      echo "- $app: present at $appdir"
    else
      echo "- $app: MISSING"
    fi
  done
  echo ""
  echo "## Model Hoard"
  echo "- $MODEL_HOARD"
} > "$DOC"

cat "$DOC"

# STEP 4: OBAMA TEST
echo "\n[STEP 4] Obama Test"
SCRAPER="$AI_APPS/DG_collect_dataset"
if [ -d "$SCRAPER" ]; then
  mainpy=""
  # find plausible main script
  if [ -f "$SCRAPER/main.py" ]; then
    mainpy="$SCRAPER/main.py"
  else
    # try to find any file containing argparse or a main invocation
    mainpy=$(grep -RIl "if __name__ == '\\_\\_main\\_\\_'" "$SCRAPER" | head -n1 || true)
  fi
  if [ -n "$mainpy" ] && [ -f "$mainpy" ]; then
    echo "Found scraper main: $mainpy"
    echo "Showing help to validate flags..."
    "$PY" "$mainpy" --help || true
    echo "Running scraper (limit 100)"
    mkdir -p "$MODEL_HOARD/dataset_test/obama"
    "$PY" "$mainpy" --search "Barack Obama" --limit 100 --output_dir "$MODEL_HOARD/dataset_test/obama" || echo "Scraper execution failed or flags differ. Check help above."
  else
    echo "Could not find a runnable main script for DG_collect_dataset. Skipping Obama test."
  fi
else
  echo "Scraper folder missing: $SCRAPER"
fi

echo "\n[secure_and_verify] Completed at $(date)"
