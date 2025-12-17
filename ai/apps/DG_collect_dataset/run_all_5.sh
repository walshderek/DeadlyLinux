#!/bin/bash
# Grand Factory Reset - Run pipeline for all 5 subjects
# Then run training via musubi-tuner

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# Activate venv
source .venv/bin/activate

# Clean outputs
rm -rf outputs/*

SUBJECTS=("Angela Merkel" "Stan Lee" "Ed Miliband" "Barack Obama" "Elon Musk")

echo "=========================================="
echo "🏭 GRAND FACTORY RESET - ALL 5 SUBJECTS"
echo "=========================================="

for subject in "${SUBJECTS[@]}"; do
    echo ""
    echo "=========================================="
    echo "🔥 Processing: $subject"
    echo "=========================================="
    
    # Run the full pipeline for this subject
    python DG_collect_dataset.py "$subject"
    
    echo "✅ Completed: $subject"
    echo ""
done

echo "=========================================="
echo "🎉 ALL SUBJECTS COMPLETE!"
echo "=========================================="

# Show what was created
echo ""
echo "📂 Generated datasets:"
ls -la /mnt/c/AI/apps/musubi-tuner/files/datasets/

echo ""
echo "📜 Generated training scripts:"
ls -la /mnt/c/AI/apps/musubi-tuner/*.bat 2>/dev/null || echo "No BAT files found"
ls -la /mnt/c/AI/apps/musubi-tuner/*.sh 2>/dev/null || echo "No SH files found"

echo ""
echo "=========================================="
echo "🚀 READY FOR TRAINING"
echo "To train, run from musubi-tuner:"
echo "  cd /mnt/c/AI/apps/musubi-tuner"
echo "  source venv/bin/activate  # or use Windows venv"
echo "  ./train_angela_merkel_256.sh"
echo "=========================================="
