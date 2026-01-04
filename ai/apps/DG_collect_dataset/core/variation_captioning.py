"""
TIER 2: VARIATION CAPTIONING
Lightweight vision model (LLaVA-7B, BLIP, Florence-2) on ALL images.

Single-stream execution (no parallelization).
Prompt explicitly excludes identity traits (face, hair, eyes, build).
Outputs: variations.csv, variations_raw/*.txt
"""

import os
import csv
import json
import base64
from pathlib import Path
from typing import List, Dict
from PIL import Image
import io
import ollama
from tqdm import tqdm

# Import utils
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
import utils

# Configuration
OLLAMA_VARIATION_MODEL = "llava:7b"  # Lightweight vision model (or BLIP, Florence-2)
OLLAMA_HOST = "127.0.0.1:11434"


def verify_ollama():
    """Check Ollama connectivity."""
    try:
        models = ollama.list()
        model_names = [m.get('name', m.get('model', 'unknown')) for m in models.get('models', [])]
        print(f"✅ Connected to Ollama")
        print(f"📦 Models: {', '.join(model_names)}")
        return True
    except Exception as e:
        print(f"❌ Cannot connect to Ollama: {e}")
        return False


def get_variation_prompt(trigger_word: str) -> str:
    """
    Prompt for variation captioning: scene-specific context only.
    
    Explicitly excludes identity traits to avoid redundancy.
    Designed for lightweight vision models (fast inference).
    """
    return f"""Provide a comprehensive, detailed description of what is UNIQUE and SPECIFIC to this particular photo of {trigger_word}.

DEMAND RICH DETAIL in these areas:

1. CLOTHING & FASHION:
   - Describe every visible garment in detail: type, color, pattern, texture, fit, style
   - Note layering: shirts, jackets, coats, sweaters, etc.
   - Describe accessories: ties, scarves, belts, watches, bags, hats
   - Detail fabric appearance (casual cotton, formal silk, leather, denim, knit, etc.)
   - Note clothing condition and style era if relevant
   - Describe any visible logos, text, or distinctive patterns

2. BODY LANGUAGE & POSE:
   - Precise body position: standing, sitting, leaning, walking, crouching
   - Arm positions and hand gestures in detail
   - Leg stance and positioning
   - Head tilt and orientation
   - Overall posture: relaxed, formal, active, contemplative
   - Any interaction with objects or environment
   - Sense of movement or stillness

3. FACIAL EXPRESSION & DEMEANOR:
   - Current emotional expression: smiling, serious, contemplative, animated, neutral
   - Mouth position: open, closed, speaking, laughing
   - Eye direction: looking at camera, away, downward, to the side
   - Eyebrow position indicating emotion
   - Overall mood conveyed by expression

4. SETTING & ENVIRONMENT:
   - Precise location type: indoor/outdoor, public/private, natural/urban
   - Detailed background elements: architecture, furniture, nature, objects
   - Environmental context: office, street, park, building, vehicle, event space
   - Visible text, signs, or environmental markers
   - Weather conditions if outdoor (sunny, cloudy, rainy, snowy)
   - Season indicators if visible

5. LIGHTING & ATMOSPHERE:
   - Light source: natural sunlight, indoor lighting, flash, mixed
   - Light quality: harsh, soft, dramatic, even, diffused
   - Shadows: direction, intensity, length
   - Time of day indicators (golden hour, midday, evening, night)
   - Overall mood created by lighting (warm, cool, bright, dim, moody)
   - Color temperature and tones in the scene

6. CAMERA TECHNIQUE & COMPOSITION:
   - Camera angle: eye-level, low-angle, high-angle, Dutch tilt
   - Shot type: close-up, medium shot, wide shot, full-body, portrait
   - Framing: centered, rule of thirds, off-center
   - Depth of field: sharp throughout or blurred background
   - Photo style: candid, posed, professional, casual snapshot
   - Any notable compositional elements

7. CONTEXTUAL DETAILS:
   - Activity taking place: speaking, walking, working, socializing, presenting
   - Other people visible (without identifying): crowds, individuals, audience
   - Event type if discernible: formal event, casual gathering, work setting, public appearance
   - Any props or objects being held or interacted with
   - Sense of formality or casualness of the situation

CRITICAL EXCLUSIONS - Do NOT describe these (handled in identity phase):
- Permanent facial features (face shape, bone structure)
- Hair color, length, or base style
- Eye color or shape
- Permanent body build, height, or frame
- Base skin tone or complexion
- Age or age-related features
- Permanent glasses, jewelry, tattoos, or scars

Provide a rich, flowing narrative description (12-20 sentences minimum). Use vivid, specific language with precise details. Paint a complete picture of this unique moment. Start with "{trigger_word}". Write in descriptive prose, not lists."""


def compress_image(img_path: Path, max_width: int = 768) -> bytes:
    """Compress image for faster processing."""
    try:
        img = Image.open(img_path)
        ratio = max_width / img.width
        new_height = int(img.height * ratio)
        img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)
        
        buf = io.BytesIO()
        img.save(buf, format='JPEG', quality=85)
        return buf.getvalue()
    except Exception as e:
        print(f"⚠️  Error compressing {img_path.name}: {e}")
        return None


def analyze_variation(img_path: Path, trigger_word: str) -> Dict:
    """
    Process single image with lightweight vision model for variation captioning.
    
    Returns: {file_name, variation_caption}
    """
    try:
        img_data = base64.b64encode(compress_image(img_path)).decode('utf-8')
        
        client = ollama.Client(host='http://127.0.0.1:11434')
        response = client.chat(
            model=OLLAMA_VARIATION_MODEL,
            messages=[{
                'role': 'user',
                'content': get_variation_prompt(trigger_word),
                'images': [img_data]
            }],
            stream=False
        )
        
        content = response['message']['content'].strip()
        
        # Ensure trigger word appears first
        if not content.lower().startswith(trigger_word.lower()):
            content = f"{trigger_word} {content}"
        
        return {
            'file_name': img_path.name,
            'variation_caption': content
        }
    
    except Exception as e:
        print(f"\n⚠️  Error on {img_path.name}: {e}")
        return None


def run_variation_captioning(image_files: List[Path], trigger_word: str, output_dir: Path) -> List[Dict]:
    """
    Tier 2: Sequential variation captioning on ALL images.
    
    Returns: list of {file_name, variation_caption}
    """
    print("\n" + "="*70)
    print("TIER 2: VARIATION CAPTIONING (Lightweight Vision Model)")
    print("="*70)
    print(f"🎯 Model: {OLLAMA_VARIATION_MODEL} (single-stream)")
    print(f"📊 Dataset size: {len(image_files)} images")
    print(f"⏱️  Expected: 0.05-0.1 sec per image ({len(image_files) * 0.075:.0f} sec total)\n")
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    variations = []
    raw_dir = output_dir / "variations_raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    
    # Sequential processing (no parallelization)
    for img_path in tqdm(image_files, desc="📸 Variation Captioning", unit="img"):
        result = analyze_variation(img_path, trigger_word)
        if result:
            variations.append(result)
            
            # Also save individual caption file
            caption_path = raw_dir / f"{img_path.stem}.txt"
            caption_path.write_text(result['variation_caption'], encoding='utf-8')
    
    print(f"\n✅ Variation captioning complete!")
    print(f"   Captioned: {len(variations)} / {len(image_files)} images")
    
    return variations


def save_variation_artifacts(variations: List[Dict], output_dir: Path):
    """
    Save variation artifacts:
    - variations.csv: file_name, variation_caption
    - variations_raw/*.txt: individual caption files (already saved during inference)
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Main CSV
    variations_csv = output_dir / "variations.csv"
    with open(variations_csv, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['file_name', 'variation_caption'])
        writer.writeheader()
        writer.writerows(variations)
    
    print(f"\n" + "="*70)
    print("SAVING ARTIFACTS")
    print("="*70)
    print(f"\n📊 {variations_csv}")
    print(f"📁 Raw files: {output_dir / 'variations_raw'} ({len(variations)} files)")


# ============================================================================
# ORCHESTRATION
# ============================================================================

def run(slug: str):
    """
    Main: Tier 2 variation captioning
    
    1. Load all images from dataset
    2. Run variation captioning on each image
    3. Save variations.csv and individual caption files
    """
    print("\n" + "="*70)
    print("TIER 2: VARIATION CAPTIONING PIPELINE")
    print("="*70)
    
    if not verify_ollama():
        return
    
    # Setup
    path = utils.get_project_path(slug)
    config = utils.load_config(slug)
    trigger_word = config.get('trigger') or utils.obfuscate_trigger(config.get('name', slug))
    
    input_dir = path / utils.DIRS.get('clean', '04_clean')
    output_dir = path / "06_caption" / "captions"
    
    # Get all images
    image_files = sorted(input_dir.glob("*.jpg"))
    if not image_files:
        print(f"❌ No images found in {input_dir}")
        return
    
    print(f"\n📊 Dataset: {len(image_files)} images")
    print(f"🎯 Trigger: {trigger_word}")
    
    # Run captioning
    variations = run_variation_captioning(image_files, trigger_word, output_dir)
    
    # Save artifacts
    save_variation_artifacts(variations, output_dir)
    
    print("\n" + "="*70)
    print("✅ TIER 2 COMPLETE")
    print("="*70)
    print(f"📁 Output: {output_dir}")
    print(f"📊 Variations: {output_dir / 'variations.csv'}")
    print(f"\nNext step: Run Tier-3 fusion to combine identity + variations")


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python 06_variation_captioning.py <slug>")
        sys.exit(1)
    run(sys.argv[1])
