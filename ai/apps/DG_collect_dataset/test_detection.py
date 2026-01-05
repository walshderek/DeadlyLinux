#!/usr/bin/env python3
import cv2
import torch
import numpy as np
import easyocr
from pathlib import Path

DEVICE_BOOL = True if torch.cuda.is_available() else False
print(f"Loading EasyOCR on {'GPU' if DEVICE_BOOL else 'CPU'}...")
reader = easyocr.Reader(['en'], gpu=DEVICE_BOOL)

# Test on first image
test_img_path = Path("/home/seanf/deadlygraphics/ai/apps/DG_collect_dataset/outputs/michael_gove/03_validate")
files = list(test_img_path.glob("*.jpg"))[:3]

for f in files:
    print(f"\n{'='*60}")
    print(f"Testing: {f.name}")
    img = cv2.imread(str(f))
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    
    # Test with different thresholds
    print("\n--- Testing with low_text=0.3, text_threshold=0.60 ---")
    results = reader.readtext(img_rgb, low_text=0.3, text_threshold=0.60)
    print(f"Found {len(results)} text regions:")
    for (bbox, text, prob) in results:
        print(f"  '{text}' (confidence: {prob:.2f})")
    
    print("\n--- Testing with low_text=0.2, text_threshold=0.4 ---")
    results2 = reader.readtext(img_rgb, low_text=0.2, text_threshold=0.4)
    print(f"Found {len(results2)} text regions:")
    for (bbox, text, prob) in results2:
        print(f"  '{text}' (confidence: {prob:.2f})")
