#!/bin/bash

# 1. Define image
IMG="/home/seanf/workspace/deadlygraphics/ai/apps/DG_collect_dataset/outputs/edmilliband/01_cropped/edmilliband_000.jpg"

if [ ! -f "$IMG" ]; then
    echo "❌ Image not found!"
    exit 1
fi

# 2. Check if Ollama is running. If not, START IT.
if ! curl -s http://127.0.0.1:11434/ > /dev/null; then
    echo "🔄 Ollama is DOWN. Restarting it in the background..."
    nohup ollama serve > ollama.log 2>&1 &
    
    # Wait loop for server to wake up
    echo "⏳ Waiting for Ollama to initialize..."
    for i in {1..10}; do
        if curl -s http://127.0.0.1:11434/ > /dev/null; then
            echo "✅ Ollama is now UP."
            break
        fi
        sleep 2
    done
else
    echo "✅ Ollama is already running."
fi

# 3. Prepare Payload
echo "📦 Encoding image..."
echo -n '{"model": "moondream", "prompt": "Describe this image", "stream": false, "images": ["' > payload.json
base64 -w 0 "$IMG" >> payload.json
echo -n '"]}' >> payload.json

# 4. SEND REQUEST
echo "🚀 Sending request..."
echo "---------------------------------------------------"
curl -s -X POST http://127.0.0.1:11434/api/generate -d @payload.json
echo ""
echo "---------------------------------------------------"

# Cleanup
rm payload.json
