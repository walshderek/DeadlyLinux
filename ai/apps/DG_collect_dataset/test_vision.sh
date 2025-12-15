#!/bin/bash

# 1. Define image
IMG="/home/seanf/workspace/deadlygraphics/ai/apps/DG_collect_dataset/outputs/edmilliband/01_cropped/edmilliband_000.jpg"

if [ ! -f "$IMG" ]; then
    echo "❌ Image not found at $IMG"
    exit 1
fi

echo "✅ Image found."
echo "⏳ Constructing payload file (avoiding shell limits)..."

# 2. Build the JSON file piece by piece to avoid "Argument list too long"
# Write the start of the JSON
echo -n '{"model": "moondream", "prompt": "Describe this image", "stream": false, "images": ["' > payload.json

# Append the base64 image directly to the file
base64 -w 0 "$IMG" >> payload.json

# Append the closing JSON syntax
echo -n '"]}' >> payload.json

echo "🚀 Sending payload to Ollama..."

# 3. Send using @ syntax (reads from file)
curl -s -X POST http://127.0.0.1:11434/api/generate -d @payload.json | grep -o '"response":"[^"]*"'

echo ""
echo "---------------------------------------------------"
echo "If you see a response above, OLLAMA IS WORKING."

# Cleanup
rm payload.json
