"""
TIER 1: IDENTITY INFERENCE
Heavy VLM (Qwen3-VL-8B) on sampled images only.

Single-stream execution (no parallelization).
Outputs: identity.json, identity.txt
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

# Import utils (fix path first)
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent))
import utils

# Import sampling module
from sampling import stratified_sample, save_sample_manifest

# Configuration
OLLAMA_IDENTITY_MODEL = "qwen3-vl"  # Heavy VLM
OLLAMA_TEXT_MODEL = "qwen3"         # LLM for consensus
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


def get_identity_prompt(trigger_word: str) -> str:
    """
    Prompt for identity inference: extract permanent traits only.
    
    Designed for Qwen3-VL: comprehensive analysis of face, hair, eyes, build.
    """
    return f"""Analyze this image of {trigger_word} in rich, comprehensive detail.

Extract PERMANENT IDENTITY TRAITS that define their core physical appearance across all contexts:

1. FACIAL STRUCTURE & FEATURES:
   - Describe face shape in detail (round, oval, square, angular, heart-shaped, diamond)
   - Note bone structure: prominent cheekbones, jaw definition, forehead shape
   - Describe eyes comprehensively: exact color (blue, brown, green, hazel with specifics), shape (almond, round, hooded), size relative to face, spacing, any distinctive characteristics
   - Detail eyebrows: thickness, arch, color, shape, grooming style
   - Describe nose: size, shape (straight, roman, button, aquiline), bridge width, nostril shape
   - Detail mouth and lips: fullness, shape, natural color, smile characteristics
   - Note chin and jawline: prominence, shape, definition
   - Identify any distinctive facial features: scars, marks, moles, dimples, laugh lines, creases

2. HAIR CHARACTERISTICS:
   - Precise color description (light brown, dark blonde, salt-and-pepper, jet black, auburn, etc.)
   - Note any grays, highlights, natural variations, or streaks
   - Describe length accurately (short, shoulder-length, long, very long with measurements if visible)
   - Detail texture (straight, wavy, curly, coily) and thickness (fine, medium, thick, voluminous)
   - Note typical styling patterns if evident across photos
   - Describe hairline shape and any receding patterns

3. BODY TYPE & PHYSICAL BUILD:
   - Comprehensive body type description (slim, athletic, muscular, curvy, stocky, heavyset, petite, tall)
   - Height impression based on proportions and context clues
   - Shoulder width and build (broad, narrow, squared)
   - Posture tendencies if notable (upright, relaxed, forward-leaning)
   - Overall proportions and body frame

4. SKIN & COMPLEXION:
   - Detailed skin tone (fair, light, medium, olive, tan, brown, dark brown, deep with undertones)
   - Note skin texture if visible (smooth, textured, weathered)
   - Identify any visible skin characteristics (freckles, blemishes, sun spots, birthmarks)

5. AGE INDICATORS:
   - Estimated age range with reasoning (early 20s, late 30s, mid-40s, 50s, 60s+)
   - Note specific age indicators visible (wrinkles, fine lines, skin elasticity, gray hair percentage)

6. PERMANENT ACCESSORIES & DISTINCTIVE MARKS:
   - Glasses: style, frame type, color if permanent fixture
   - Jewelry that appears permanent (wedding ring, signature pieces)
   - Tattoos: location, size, subject matter if visible
   - Scars, birthmarks, or permanent marks: location and description
   - Any other distinctive permanent features (piercings, dental characteristics if visible)

IMPORTANT EXCLUSIONS: Do NOT describe:
- Temporary clothing, outfits, or fashion choices
- Current pose, gesture, or body position
- Environmental setting, background, or location
- Temporary makeup or styling
- Current emotional expression (though resting face characteristics are fine)

Provide a comprehensive, richly detailed description (3-5 sentences). Use specific, vivid language with precise adjectives. Start with "{trigger_word}". Write in flowing prose, not bullet points."""


def compress_image(img_path: Path, max_width: int = 256) -> bytes:
    """Compress image for faster Ollama processing."""
    try:
        img = Image.open(img_path)
        # Don't upscale if image is already smaller
        if img.width <= max_width:
            buf = io.BytesIO()
            img.save(buf, format='JPEG', quality=85)
            return buf.getvalue()
        
        ratio = max_width / img.width
        new_height = int(img.height * ratio)
        img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)
        
        buf = io.BytesIO()
        img.save(buf, format='JPEG', quality=85)
        return buf.getvalue()
    except Exception as e:
        print(f"⚠️  Error compressing {img_path.name}: {e}")
        return None


def analyze_identity(img_path: Path, trigger_word: str) -> Dict:
    """
    Process single image with heavy VLM for identity inference.
    
    Returns: {file_name, identity_description}
    """
    try:
        img_data = base64.b64encode(compress_image(img_path)).decode('utf-8')
        
        # Increase timeout for heavy VLM (models can take 10-20 seconds)
        client = ollama.Client(host='http://127.0.0.1:11434')
        response = client.chat(
            model=OLLAMA_IDENTITY_MODEL,
            messages=[{
                'role': 'user',
                'content': get_identity_prompt(trigger_word),
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
            'identity_description': content
        }
    
    except Exception as e:
        print(f"\n⚠️  Error on {img_path.name}: {e}")
        return None


def run_identity_inference(sampled_images: List[Path], trigger_word: str, output_dir: Path) -> tuple:
    """
    Tier 1: Sequential identity inference on sampled images only.
    
    Returns: (identity_descriptions, sample_metadata)
    """
    print("\n" + "="*70)
    print("TIER 1: IDENTITY INFERENCE (Heavy VLM)")
    print("="*70)
    print(f"🎯 Model: {OLLAMA_IDENTITY_MODEL} (single-stream)")
    print(f"📊 Sample size: {len(sampled_images)} images")
    print(f"⏱️  Expected: 0.5-1 sec per image\n")
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    identities = []
    
    # Sequential processing (no parallelization)
    for img_path in tqdm(sampled_images, desc="🔍 Identity Inference", unit="img"):
        result = analyze_identity(img_path, trigger_word)
        if result:
            identities.append(result)
    
    print(f"\n✅ Identity inference complete!")
    print(f"   Analyzed: {len(identities)} / {len(sampled_images)} images")
    
    return identities


def merge_identity_descriptions(identities: List[Dict], trigger_word: str, 
                                ollama_model: str = OLLAMA_TEXT_MODEL) -> str:
    """
    Use LLM to synthesize identity descriptions into a master identity.
    
    Input: List of per-image identity descriptions
    Output: Single master identity description (3-4 sentences)
    """
    sample = identities[:min(10, len(identities))]
    
    descriptions_text = "\n".join(
        f"{i+1}. {desc['identity_description']}"
        for i, desc in enumerate(sample)
    )
    
    prompt = f"""Analyze these {len(sample)} identity descriptions of {trigger_word}:

{descriptions_text}

Create ONE master identity description that captures their defining features.
Focus on traits that appear consistently across descriptions.
Keep it 3-4 sentences, factual and specific.
Start with "{trigger_word}".

Master Identity:"""
    
    client = ollama.Client(host='http://127.0.0.1:11434')
    response = client.chat(
        model=ollama_model,
        messages=[{'role': 'user', 'content': prompt}],
        stream=False
    )
    
    return response['message']['content'].strip()


def save_identity_artifacts(identities: List[Dict], master_identity: str, 
                           trigger_word: str, output_dir: Path):
    """
    Save identity artifacts:
    - identity.json: structured identity data
    - identity.txt: master identity description
    - identity_raw.csv: per-image identity descriptions
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. Master identity (plain text)
    identity_txt = output_dir / "identity.txt"
    identity_txt.write_text(master_identity, encoding='utf-8')
    print(f"📄 {identity_txt}")
    
    # 2. Structured identity (JSON)
    identity_json = output_dir / "identity.json"
    identity_data = {
        'trigger_word': trigger_word,
        'master_identity': master_identity,
        'derived_from_images': len(identities),
        'identity_descriptions': [
            {'file_name': item['file_name'], 'description': item['identity_description']}
            for item in identities
        ]
    }
    with open(identity_json, 'w') as f:
        json.dump(identity_data, f, indent=2)
    print(f"📊 {identity_json}")
    
    # 3. Raw per-image descriptions (CSV)
    identity_csv = output_dir / "identity_raw.csv"
    with open(identity_csv, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['file_name', 'identity_description'])
        writer.writeheader()
        writer.writerows(identities)
    print(f"📋 {identity_csv}")


# ============================================================================
# ORCHESTRATION
# ============================================================================

def run(slug: str):
    """
    Main: Tier 1 identity inference
    
    1. Load dataset
    2. Sample representative images
    3. Run identity inference on sample
    4. Synthesize master identity
    5. Save artifacts
    """
    print("\n" + "="*70)
    print("TIER 1: IDENTITY INFERENCE PIPELINE")
    print("="*70)
    
    if not verify_ollama():
        return
    
    # Setup
    path = utils.get_project_path(slug)
    config = utils.load_config(slug)
    trigger_word = config.get('trigger') or utils.obfuscate_trigger(config.get('name', slug))
    
    # CRITICAL: Use 256px resized images for faster inference
    input_dir = path / "05_resize" / "256"
    if not input_dir.exists():
        print(f"❌ CRITICAL: 256px folder not found at {input_dir}")
        print(f"   Run Step 5 (resize) first to generate 256px images.")
        return
    
    output_dir = path / "06_caption" / "identity"
    
    # Get all images
    image_files = sorted(input_dir.glob("*.jpg"))
    if not image_files:
        print(f"❌ No images found in {input_dir}")
        return
    
    print(f"✅ Using 256x256 images from: {input_dir}")
    
    print(f"\n📊 Full dataset: {len(image_files)} images")
    print(f"🎯 Trigger: {trigger_word}")
    
    # Step 1: Sample
    sampled, metadata = stratified_sample(image_files, sample_size=16)
    save_sample_manifest(sampled, output_dir, metadata)
    
    # Step 2: Infer identity
    identities = run_identity_inference(sampled, trigger_word, output_dir)
    
    # Step 3: Merge descriptions
    print("\n" + "="*70)
    print("SYNTHESIZING MASTER IDENTITY")
    print("="*70)
    print(f"🧠 Merging {len(identities)} identity descriptions...\n")
    
    master_identity = merge_identity_descriptions(identities, trigger_word)
    print(f"✅ Master Identity:")
    print(f"\n   {master_identity}\n")
    
    # Step 4: Save
    print("="*70)
    print("SAVING ARTIFACTS")
    print("="*70)
    print()
    save_identity_artifacts(identities, master_identity, trigger_word, output_dir)
    
    print("\n" + "="*70)
    print("✅ TIER 1 COMPLETE")
    print("="*70)
    print(f"📁 Output: {output_dir}")
    print(f"📄 Identity: {output_dir / 'identity.txt'}")
    print(f"📊 Artifacts: {output_dir / 'identity.json'}")
    print(f"\nNext step: Run Tier-2 variation captioning on all {len(image_files)} images")


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python 05_identity_inference.py <slug>")
        sys.exit(1)
    run(sys.argv[1])
