#!/bin/bash
set -e

# =============================================================================
# reset_and_run_all.sh - Full Pipeline with Mandatory 07_summary Step
# =============================================================================
# This script enforces the Paper Trail by creating local 07_summary artifacts
# BEFORE copying to Windows.
# =============================================================================

BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Use proper names with spaces - the orchestrator will convert to snake_case slug
SUBJECTS=("Angela Merkel")

cd /home/seanf/deadlygraphics/ai/apps/DG_collect_dataset
source .venv/bin/activate

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}🚀 FULL PIPELINE (with 07_summary enforcement)${NC}"
echo -e "${BLUE}========================================${NC}"

for display_name in "${SUBJECTS[@]}"; do
    # Convert to snake_case slug for filesystem paths
    slug=$(echo "$display_name" | tr '[:upper:]' '[:lower:]' | tr ' ' '_' | tr '-' '_')
    
    echo -e "\n${BLUE}=== PROCESSING: $display_name (slug: $slug) ===${NC}"
    
    # 1. Clean previous outputs & Scrape (150 limit for 100 target)
    echo -e "${YELLOW}[Step 1] Cleaning and Scraping...${NC}"
    rm -rf "outputs/$slug"
    python DG_collect_dataset.py "$display_name" --limit 150 --count 100 --only-step 1
    
    # 2-6. Standard Pipeline Steps
    for i in {2..6}; do
        echo -e "${YELLOW}[Step $i] Running...${NC}"
        python DG_collect_dataset.py "$slug" --only-step $i
    done
    
    # 7. MANDATORY LOCAL SUMMARY (Paper Trail)
    echo -e "${YELLOW}[Step 7] Creating Local Summary (Paper Trail)...${NC}"
    LOCAL_CROP="outputs/$slug/02_crop"      # Square images for contact sheet
    LOCAL_CAP="outputs/$slug/05_caption"    # Captions
    LOCAL_SUM="outputs/$slug/07_summary"
    
    # Force creation of 07_summary directory
    mkdir -p "$LOCAL_SUM"
    
    # Run v4.3 Summary Script - uses 02_crop for 64x64 thumbnails, captions from 05_caption
    python DG_dataset_summary.py "$LOCAL_CROP" --output-dir "$LOCAL_SUM" --caption-dir "$LOCAL_CAP"
    
    # Verify artifacts exist (now .jpg not .png)
    if [ ! -f "$LOCAL_SUM/${slug}_contact_sheet.jpg" ] || [ ! -f "$LOCAL_SUM/${slug}_captions.txt" ]; then
        echo -e "${RED}❌ FAILED: Summary artifacts not created!${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}✅ Local 07_summary created with:${NC}"
    ls -la "$LOCAL_SUM/"
    
    # Sync to Windows destination
    echo -e "${YELLOW}--> Syncing to Windows...${NC}"
    WIN_DEST="/mnt/c/AI/apps/musubi-tuner/files/datasets/$slug"
    mkdir -p "$WIN_DEST"
    cp "$LOCAL_SUM"/* "$WIN_DEST/"
    
    echo -e "${GREEN}✅ COMPLETE: $display_name${NC}"
    echo "   📁 Local:   $LOCAL_SUM/"
    echo "   📁 Windows: $WIN_DEST/"
done

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}🎉 ALL SUBJECTS COMPLETE${NC}"
echo -e "${GREEN}========================================${NC}"
echo "Check outputs/<subject>/07_summary/ for Paper Trail artifacts."