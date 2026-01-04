"""
STEP 5: RESIZE IMAGES
Resize cleaned images to training resolutions: 1024, 512, 256
Caption will run on 256x256 for speed.
"""

import os
import shutil
from pathlib import Path
from PIL import Image
from tqdm import tqdm

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
import utils

RESOLUTIONS = [1024, 512, 256]


def run(slug: str):
    """Resize images from 04_clean to multiple resolutions."""
    print(f"\n{'='*70}")
    print("STEP 5: RESIZE IMAGES")
    print(f"{'='*70}")
    
    config = utils.load_config(slug)
    if not config:
        print(f"❌ Error: Config not found for {slug}")
        return
    
    path = utils.get_project_path(slug)
    src_dir = path / utils.DIRS.get('clean', '04_clean')
    
    if not src_dir.exists() or not list(src_dir.glob("*.jpg")):
        print(f"❌ No images in {src_dir}")
        return
    
    image_files = sorted(src_dir.glob("*.jpg"))
    print(f"\n📊 Found {len(image_files)} images to resize")
    print(f"🎯 Resolutions: {RESOLUTIONS}\n")
    
    for resolution in RESOLUTIONS:
        out_dir = path / f"05_resize_{resolution}x{resolution}"
        out_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"\n🔄 Resizing to {resolution}x{resolution}...")
        
        for img_file in tqdm(image_files, desc=f"  {resolution}x{resolution}", unit="img"):
            try:
                img = Image.open(img_file).convert('RGB')
                img.thumbnail((resolution, resolution), Image.Resampling.LANCZOS)
                
                # Create square with padding
                square = Image.new('RGB', (resolution, resolution), (255, 255, 255))
                offset = ((resolution - img.width) // 2, (resolution - img.height) // 2)
                square.paste(img, offset)
                
                output_path = out_dir / img_file.name
                square.save(output_path, quality=95)
                
            except Exception as e:
                print(f"  ⚠️  {img_file.name}: {e}")
    
    print(f"\n✅ Resize Complete!")
    print(f"   📁 Images resized to: {', '.join([f'{r}x{r}' for r in RESOLUTIONS])}")
