#!/usr/bin/env bash
set -euo pipefail
cd /home/seanf/deadlygraphics/ai/apps/DG_collect_dataset
python3 DG_collect_dataset.py "Barack Obama" --limit 10
cd /home/seanf/deadlygraphics
find ai/apps/musubi-tuner -maxdepth 3 -type f -name 'train_Barack_Obama*' -print > /home/seanf/deadlygraphics/train_script_paths.txt
