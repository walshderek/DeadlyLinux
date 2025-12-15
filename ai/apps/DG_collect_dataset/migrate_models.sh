#!/bin/bash

# --- CONFIGURATION ---
# Source is inside the 'models' subdirectory
SOURCE_DIR="./models"

# Destination (Windows Path via WSL)
DEST_ROOT="/mnt/c/AI/models/LLM"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Starting Model Migration to ${DEST_ROOT}...${NC}"

# 1. Verify Destination
if [ ! -d "$DEST_ROOT" ]; then
    echo -e "${RED}❌ Error: Destination $DEST_ROOT does not exist.${NC}"
    echo "   Please create 'C:\AI\models\LLM' on Windows first."
    exit 1
fi

# 2. Create Organization Structure
echo "📂 Creating folder structure..."
mkdir -p "$DEST_ROOT/QWEN"
mkdir -p "$DEST_ROOT/LLAMA"
mkdir -p "$DEST_ROOT/Florence"

# 3. Move Qwen-VL (HuggingFace format)
# We look for models/qwen-vl
QWEN_SOURCE="$SOURCE_DIR/qwen-vl"
QWEN_DEST="$DEST_ROOT/QWEN/qwen-vl"

if [ -d "$QWEN_SOURCE" ]; then
    if [ -d "$QWEN_DEST" ]; then
        echo -e "${YELLOW}⚠️  Destination $QWEN_DEST already exists. Skipping move.${NC}"
        # Optional: Rename/Backup local copy if destination exists so we don't redownload
        # mv "$QWEN_SOURCE" "$QWEN_SOURCE.bak"
    else
        echo -e "📦 Moving local Qwen-VL to Windows drive..."
        mv "$QWEN_SOURCE" "$DEST_ROOT/QWEN/"
        
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}✅ Qwen-VL moved successfully.${NC}"
        else
            echo -e "${RED}❌ Failed to move Qwen-VL.${NC}"
        fi
    fi
else
    echo -e "${RED}ℹ️  No local Qwen-VL found at $QWEN_SOURCE.${NC}"
    echo "   (Current dir: $(pwd))"
fi

# 4. Ollama Configuration Reminder
echo ""
echo -e "${YELLOW}ℹ️  Ollama Note:${NC}"
echo "   Your updated Python scripts have been configured to automatically"
echo "   point Ollama to: $DEST_ROOT"
echo ""
echo -e "${GREEN}✅ Migration Script Complete.${NC}"
