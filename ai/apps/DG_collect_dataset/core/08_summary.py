import os
import sys
import math
from PIL import Image, ImageDraw, ImageFont

# --- BOOTSTRAP ---
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)
import utils

def run(slug):
    """
    Step 07: Dataset Visual Reporting
    Generates a high-density 64x64 contact sheet and text summary.
    """
    config = utils.load_config(slug)
    path = utils.get_project_path(slug)
    
    # Input: The final 256px dataset sent to training
    in_dir = path / "06_publish" / "256"
    
    # Output: The summary folder
    out_dir = path / utils.DIRS['summary']
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"📊 [07_summary] Generating v4.3-Compact Report for {slug}...")
    
    if not in_dir.exists():
        print(f"❌ Error: Publish folder not found: {in_dir}")
        return

    files = sorted([f for f in os.listdir(in_dir) if f.lower().endswith(('.jpg', '.png', '.jpeg'))])
    if not files:
        print("⚠️  No images found to summarize.")
        return

    # --- COMPACT LAYOUT LOGIC ---
    THUMB_W = 64
    THUMB_H = 84  # 64px image + 20px for text label
    PADDING = 4
    
    # Calculate Grid
    count = len(files)
    cols = math.ceil(math.sqrt(count))
    rows = math.ceil(count / cols)
    
    sheet_w = (cols * THUMB_W) + ((cols + 1) * PADDING)
    sheet_h = (rows * THUMB_H) + ((rows + 1) * PADDING)
    
    # Create Canvas
    sheet = Image.new('RGB', (sheet_w, sheet_h), (30, 30, 30))
    draw = ImageDraw.Draw(sheet)
    
    # Load Font (Fallback if necessary)
    try:
        font = ImageFont.load_default()
    except:
        font = None

    print(f"   Grid: {rows}x{cols} | Total Images: {count}")

    for i, f in enumerate(files):
        row, col = divmod(i, cols)
        
        x = PADDING + (col * (THUMB_W + PADDING))
        y = PADDING + (row * (THUMB_H + PADDING))
        
        try:
            # Load and Resize
            img = Image.open(in_dir / f).convert("RGB")
            img = img.resize((THUMB_W, THUMB_W), Image.Resampling.LANCZOS)
            
            # Paste Image
            sheet.paste(img, (x, y))
            
            # Draw Filename (Truncated)
            # e.g. "face_001..."
            label = f[:8]
            if font:
                draw.text((x + 2, y + 66), label, fill=(200, 200, 200), font=font)
                
        except Exception as e:
            print(f"   Error processing thumbnail {f}: {e}")

    # Save JPG (Compact Quality)
    save_path = out_dir / f"{slug}_compact_summary.jpg"
    sheet.save(save_path, quality=50, optimize=True)
    
    # Generate Text Summary (Full Audit Log)
    txt_path = out_dir / f"{slug}_caption_summary.txt"
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(f"--- DATASET REPORT: {config.get('name', slug)} ---\n")
        f.write(f"Trigger: {config.get('trigger', 'Unknown')}\n")
        f.write(f"Total Images: {count}\n")
        f.write("-" * 30 + "\n\n")
        
        for filename in files:
            # Try to find matching text file
            txt_name = os.path.splitext(filename)[0] + ".txt"
            caption = "[No Caption Found]"
            if (in_dir / txt_name).exists():
                with open(in_dir / txt_name, 'r', encoding='utf-8') as cf:
                    caption = cf.read().strip()
            
            f.write(f"IMAGE: {filename}\nCAPTION: {caption}\n\n")

    print(f"✅ Summary Saved:\n   Visual: {save_path}\n   Text:   {txt_path}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        run(sys.argv[1])