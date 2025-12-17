#!/bin/bash
set -e

DATASET_ROOT="/home/seanf/deadlygraphics/ai/apps/DG_collect_dataset"
VENV="$DATASET_ROOT/.venv"

cd "$DATASET_ROOT"
source "$VENV/bin/activate"

echo "=== RESTARTING ANGELA MERKEL PIPELINE ==="
echo ""

# Step 1: Delete bad dataset
echo "🗑️ Cleaning old Angela Merkel dataset..."
rm -rf "outputs/Angela Merkel"
echo "✅ Deleted"
echo ""

# Step 2: Run full pipeline
echo "🚀 Running complete Angela Merkel pipeline..."
python DG_collect_dataset.py "Angela Merkel" \
    --limit 50 \
    --trigger "4N9314M3RK31993"

echo ""
echo "✅ Angela Merkel dataset complete!"
echo ""

# Step 3: Check if 256x256 images exist
PUBLISHED_DIR="/mnt/c/AI/apps/musubi-tuner/files/datasets/Angela Merkel/256"
if [ -d "$PUBLISHED_DIR" ]; then
    IMG_COUNT=$(ls "$PUBLISHED_DIR"/*.jpg 2>/dev/null | wc -l)
    echo "📊 Found $IMG_COUNT images in 256x256 folder"
    echo ""
    
    if [ "$IMG_COUNT" -gt 0 ]; then
        echo "🎯 Ready to train! Run this command in Windows PowerShell:"
        echo ""
        echo "    cd C:\\AI\\apps\\musubi-tuner"
        echo "    .\\BAT\\train_angela_merkel_256.bat"
        echo ""
    else
        echo "⚠️ No images found in 256 folder"
    fi
else
    echo "⚠️ Published 256 folder not found at: $PUBLISHED_DIR"
fi

echo ""
echo "=== PIPELINE COMPLETE ==="
