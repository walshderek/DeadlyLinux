#!/bin/bash
#===============================================================================
# GRAND RESET & FULL PIPELINE EXECUTION
#===============================================================================
# This script:
# 1. Completely deletes all output folders for the three test subjects
# 2. Runs the FULL pipeline (Steps 1-6) for each subject
# 3. Uses the correct .venv environment
#
# MUST run as user: seanf (never root)
#===============================================================================

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PATH="${SCRIPT_DIR}/.venv"
OUTPUTS_DIR="${SCRIPT_DIR}/outputs"

# Test subjects with their genders
declare -A SUBJECTS
SUBJECTS["Angela Merkel"]="f"
SUBJECTS["Stan Lee"]="m"
SUBJECTS["Ed Miliband"]="m"

#===============================================================================
# SAFETY CHECKS
#===============================================================================

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  GRAND RESET & FULL PIPELINE          ${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check we're not root
if [ "$EUID" -eq 0 ]; then
    echo -e "${RED}[ERROR] Do NOT run this script as root!${NC}"
    echo -e "${RED}        Run as user 'seanf' instead.${NC}"
    exit 1
fi

# Check user
CURRENT_USER=$(whoami)
echo -e "${GREEN}[OK] Running as: $CURRENT_USER${NC}"
echo -e "${GREEN}[OK] Script dir: $SCRIPT_DIR${NC}"

# Check venv exists
if [ ! -d "$VENV_PATH" ]; then
    echo -e "${RED}[ERROR] Virtual environment not found: $VENV_PATH${NC}"
    echo -e "${YELLOW}[HINT] Create it with: python3 -m venv $VENV_PATH${NC}"
    exit 1
fi
echo -e "${GREEN}[OK] Venv path:  $VENV_PATH${NC}"
echo ""

#===============================================================================
# PHASE 1: GRAND RESET
#===============================================================================

echo -e "${YELLOW}========================================${NC}"
echo -e "${YELLOW}  PHASE 1: GRAND RESET                 ${NC}"
echo -e "${YELLOW}========================================${NC}"
echo ""

for subject in "${!SUBJECTS[@]}"; do
    subject_dir="${OUTPUTS_DIR}/${subject}"
    
    if [ -d "$subject_dir" ]; then
        echo -e "${RED}[DELETE] Removing: $subject_dir${NC}"
        rm -rf "$subject_dir"
        echo -e "${GREEN}[OK] Deleted: $subject${NC}"
    else
        echo -e "${BLUE}[SKIP] Does not exist: $subject_dir${NC}"
    fi
done

echo ""
echo -e "${GREEN}[RESET COMPLETE] All output folders cleared.${NC}"
echo ""

#===============================================================================
# PHASE 2: ACTIVATE VIRTUAL ENVIRONMENT
#===============================================================================

echo -e "${YELLOW}========================================${NC}"
echo -e "${YELLOW}  PHASE 2: ACTIVATE ENVIRONMENT        ${NC}"
echo -e "${YELLOW}========================================${NC}"
echo ""

source "${VENV_PATH}/bin/activate"
echo -e "${GREEN}[OK] Activated: $VIRTUAL_ENV${NC}"
echo -e "${GREEN}[OK] Python: $(which python)${NC}"

# Check CUDA availability
echo ""
echo -e "${BLUE}[CHECK] Testing CUDA availability...${NC}"
python -c "import torch; cuda_available = torch.cuda.is_available(); print(f'CUDA Available: {cuda_available}'); exit(0 if cuda_available else 1)" && \
    echo -e "${GREEN}[OK] GPU acceleration enabled!${NC}" || \
    echo -e "${YELLOW}[WARN] No GPU - will use CPU (slower)${NC}"
echo ""

#===============================================================================
# PHASE 3: FULL PIPELINE EXECUTION
#===============================================================================

run_pipeline() {
    local subject="$1"
    local gender="$2"
    
    echo ""
    echo -e "${BLUE}================================================================${NC}"
    echo -e "${BLUE}  PROCESSING: $subject (gender: $gender)${NC}"
    echo -e "${BLUE}================================================================${NC}"
    echo ""
    
    cd "$SCRIPT_DIR"
    
    # Run full pipeline using DG_collect_dataset.py
    echo -e "${YELLOW}[PIPELINE] Running full pipeline for: $subject${NC}"
    python DG_collect_dataset.py "$subject" --limit 50 --gender "$gender" || {
        echo -e "${RED}[ERROR] Pipeline failed for $subject${NC}"
        return 1
    }
    
    echo -e "${GREEN}[SUCCESS] Pipeline complete for: $subject${NC}"
    return 0
}

echo -e "${YELLOW}========================================${NC}"
echo -e "${YELLOW}  PHASE 3: FULL PIPELINE EXECUTION     ${NC}"
echo -e "${YELLOW}========================================${NC}"

# Track results
SUCCEEDED=()
FAILED=()

for subject in "${!SUBJECTS[@]}"; do
    gender="${SUBJECTS[$subject]}"
    if run_pipeline "$subject" "$gender"; then
        SUCCEEDED+=("$subject")
    else
        FAILED+=("$subject")
    fi
done

#===============================================================================
# FINAL SUMMARY
#===============================================================================

echo ""
echo -e "${BLUE}================================================================${NC}"
echo -e "${BLUE}  FINAL SUMMARY                                                ${NC}"
echo -e "${BLUE}================================================================${NC}"
echo ""

echo -e "${GREEN}SUCCEEDED (${#SUCCEEDED[@]}):${NC}"
for s in "${SUCCEEDED[@]}"; do
    echo -e "  ✓ $s"
done

if [ ${#FAILED[@]} -gt 0 ]; then
    echo ""
    echo -e "${RED}FAILED (${#FAILED[@]}):${NC}"
    for f in "${FAILED[@]}"; do
        echo -e "  ✗ $f"
    done
fi

echo ""
echo -e "${BLUE}Output directories:${NC}"
for subject in "${!SUBJECTS[@]}"; do
    subject_dir="${OUTPUTS_DIR}/${subject}"
    if [ -d "$subject_dir" ]; then
        stage_count=$(ls -d "$subject_dir"/*/ 2>/dev/null | wc -l)
        echo -e "  📁 $subject: $stage_count stages"
    fi
done

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  GRAND RESET COMPLETE                 ${NC}"
echo -e "${GREEN}========================================${NC}"
