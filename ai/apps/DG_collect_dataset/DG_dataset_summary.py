#!/usr/bin/env python3
"""
DG_dataset_summary.py - v4.3-compact
Generates contact sheet (64x64 thumbnails, JPG 40%) and caption summary.
Uses 02_crop folder for square images.
"""
import os
import sys
import argparse
import math
from PIL import Image

# --- VERSION v4.3 (COMPACT CONTACT SHEET) ---
SCRIPT_VERSION = "v4.3-compact"
THUMB_SIZE = 64          # 64x64 thumbnails
PADDING = 2              # Minimal padding
BG_COLOR = (30, 30, 30)  # Dark background
JPG_QUALITY = 40         # 40% quality

def main():
    parser = argparse.ArgumentParser(description="Generate contact sheet and caption summary")
    parser.add_argument('input_dir', help="Path to folder containing images (e.g., 02_crop for square images)")
    parser.add_argument('--output-dir', required=True, help="Path to output folder (e.g., 07_summary)")
    parser.add_argument('--caption-dir', help="Path to captions folder (e.g., 05_caption) - optional")
    args = parser.parse_args()

    print(f"--- DG_dataset_summary {SCRIPT_VERSION} ---")
    print(f"Input:  {args.input_dir}")
    print(f"Output: {args.output_dir}")
    
    if not os.path.exists(args.input_dir):
        print(f"❌ Input directory does not exist: {args.input_dir}")
        sys.exit(1)
    
    if not os.path.exists(args.output_dir):
        os.makedirs(args.output_dir)
        print(f"📁 Created output directory: {args.output_dir}")
    
    # Find all images
    files = sorted([
        os.path.join(args.input_dir, f) 
        for f in os.listdir(args.input_dir) 
        if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))
    ])
    
    if not files:
        print("❌ No images found in input directory.")
        sys.exit(1)

    print(f"📸 Processing {len(files)} images as {THUMB_SIZE}x{THUMB_SIZE} thumbnails...")
    
    # Load all thumbnails
    thumbs = []
    for p in files:
        try:
            img = Image.open(p)
            # Resize to 64x64 (images from 02_crop are already square)
            img = img.resize((THUMB_SIZE, THUMB_SIZE), Image.LANCZOS)
            thumbs.append({'img': img, 'name': os.path.splitext(os.path.basename(p))[0]})
        except Exception as e:
            print(f"Warning: Could not load {p}: {e}")

    if not thumbs:
        print("❌ No valid images could be loaded.")
        sys.exit(1)

    # Calculate grid layout
    N = len(thumbs)
    cols = math.ceil(math.sqrt(N))
    rows = math.ceil(N / cols)
    
    # Create contact sheet
    W = cols * THUMB_SIZE + (cols + 1) * PADDING
    H = rows * THUMB_SIZE + (rows + 1) * PADDING
    
    sheet = Image.new('RGB', (W, H), BG_COLOR)
    
    for i, t in enumerate(thumbs):
        c, r = i % cols, i // cols
        x = PADDING + c * (THUMB_SIZE + PADDING)
        y = PADDING + r * (THUMB_SIZE + PADDING)
        sheet.paste(t['img'], (x, y))

    # Derive name from parent folder
    name = os.path.basename(os.path.dirname(os.path.normpath(args.input_dir)))
    
    # Save contact sheet as JPG at 40% quality
    out_img = os.path.join(args.output_dir, f"{name}_contact_sheet.jpg")
    sheet.convert('RGB').save(out_img, 'JPEG', quality=JPG_QUALITY, optimize=True)
    print(f"✅ Contact Sheet: {out_img} ({W}x{H}, {JPG_QUALITY}% quality)")
    
    # Load captions from caption_dir if provided, otherwise try to find them
    caption_dir = args.caption_dir
    if not caption_dir:
        # Try to find 05_caption in same parent
        parent = os.path.dirname(os.path.normpath(args.input_dir))
        caption_dir = os.path.join(parent, "05_caption")
    
    # Save caption summary
    out_txt = os.path.join(args.output_dir, f"{name}_captions.txt")
    with open(out_txt, 'w', encoding='utf-8') as f:
        for t in thumbs:
            cap = ""
            if caption_dir and os.path.exists(caption_dir):
                txt_path = os.path.join(caption_dir, t['name'] + ".txt")
                if os.path.exists(txt_path):
                    with open(txt_path, 'r', encoding='utf-8') as cf:
                        cap = cf.read().strip()
            f.write(f"=== {t['name']} ===\n{cap}\n\n")
    print(f"✅ Caption Summary: {out_txt}")
    
    print(f"\n📊 Summary: {len(thumbs)} images processed")

if __name__ == '__main__':
    main()
