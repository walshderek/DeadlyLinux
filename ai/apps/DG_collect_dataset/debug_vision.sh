#!/bin/bash

IMG="/home/seanf/workspace/deadlygraphics/ai/apps/DG_collect_dataset/outputs/edmilliband/01_cropped/edmilliband_000.jpg"

echo "1. Checking Ollama connection..."
curl -s http://127.0.0.1:11434/
echo ""

echo "2. Preparing payload..."
echo -n '{"model": "moondream", "prompt": "Describe this image", "stream": false, "images": ["' > payload.json
base64 -w 0 "$IMG" >> payload.json
echo -n '"]}' >> payload.json

echo "3. Sending Request (RAW OUTPUT):"
echo "---------------------------------------------------"
# -v for verbose to see connection issues
# No grep, so we see the actual error message
curl -v -X POST http://127.0.0.1:11434/api/generate -d @payload.json
echo ""
echo "---------------------------------------------------"
rm payload.json
