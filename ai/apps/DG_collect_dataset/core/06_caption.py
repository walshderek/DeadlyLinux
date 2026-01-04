"""
STEP 5: IDENTITY-AWARE SUBTRACTIVE CAPTIONING
Load vision model ONCE, process images sequentially.

Phase 1: Vision Analysis - Sequential processing, one call per image
Phase 2: Consensus Engine - Extract constants from prompts
Phase 3: Subtractive Save - Clean captions by removing constants
"""

import os
import csv
import json
import base64
from pathlib import Path
from typing import List, Dict
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from PIL import Image
import io
import ollama
from tqdm import tqdm

# Import utils
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
import utils

# Configuration
OLLAMA_VISION_MODEL = "llava:7b"
OLLAMA_TEXT_MODEL = "qwen3"
OLLAMA_HOST = "127.0.0.1:11434"
CONSTANT_THRESHOLD = 0.8


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


# ============================================================================
# PHASE 1: VISION ANALYSIS (Sequential, one model load)
# ============================================================================

def get_vision_prompt(trigger_word: str) -> str:
    """Ultra-fast prompt for llava:7b."""
    return f"""Quick analysis of {trigger_word}:

Physical: Describe face, hair, eyes, build in 1 sentence.

Scene: Describe setting, lighting, mood in 1 sentence.

Keep it short and fast."""


def compress_image(img_path: Path, max_width: int = 768) -> bytes:
    """Compress image to reduce processing time."""
    img = Image.open(img_path)
    ratio = max_width / img.width
    new_height = int(img.height * ratio)
    img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)
    
    buf = io.BytesIO()
    img.save(buf, format='JPEG', quality=85)
    return buf.getvalue()


def analyze_image(img_path: Path, trigger_word: str) -> Dict:
    """
    Process single image with vision model.
    Returns prompt and caption.
    """
    try:
        # Compress image for faster processing
        img_data = base64.b64encode(compress_image(img_path)).decode('utf-8')
        
        response = ollama.chat(
            model=OLLAMA_VISION_MODEL,
            messages=[{
                'role': 'user',
                'content': get_vision_prompt(trigger_word),
                'images': [img_data]
            }]
        )
        
        content = response['message']['content'].strip()
        
        # Parse response - look for section markers
        prompt = ""
        caption = ""
        
        # Try to extract Physical and Scene sections
        if "Physical:" in content:
            try:
                physical_start = content.index("Physical:") + len("Physical:")
                physical_end = content.index("Scene:") if "Scene:" in content else len(content)
                prompt = content[physical_start:physical_end].strip()
            except:
                pass
        
        if "Scene:" in content:
            try:
                scene_start = content.index("Scene:") + len("Scene:")
                caption = content[scene_start:].strip()
            except:
                pass
        
        # Fallback if parsing didn't work
        if not prompt:
            lines = [l.strip() for l in content.split('\n') if l.strip() and len(l.strip()) > 10]
            prompt = lines[0] if lines else f"{trigger_word} description"
        
        if not caption:
            lines = [l.strip() for l in content.split('\n') if l.strip() and len(l.strip()) > 10]
            caption = lines[1] if len(lines) > 1 else (lines[0] if lines else f"{trigger_word} scene")
        
        # Clean up
        prompt = prompt.replace("Physical:", "").strip()
        caption = caption.replace("Scene:", "").strip()
        
        # Ensure trigger word
        if not prompt.lower().startswith(trigger_word.lower()):
            prompt = f"{trigger_word} {prompt}"
        if not caption.lower().startswith(trigger_word.lower()):
            caption = f"{trigger_word} {caption}"
        
        return {
            'file_name': img_path.name,
            'prompt': prompt,
            'caption': caption
        }
        
    except Exception as e:
        print(f"\n⚠️  Error on {img_path.name}: {e}")
        return None


def phase_1_vision_analysis(image_files: List[Path], trigger_word: str, output_dir: Path) -> tuple:
    """
    Phase 1: Parallel vision analysis.
    Load model once, process images in parallel threads.
    """
    print("\n" + "="*70)
    print("PHASE 1: VISION ANALYSIS")
    print("="*70)
    print(f"🔍 Parallel analysis of {len(image_files)} images")
    print(f"   llava:7b on 256x256 = ~2-3 sec per image (4 workers)\n")
    
    prompts_data = []
    captions_data = []
    prompts_list = []
    captions_list = []
    
    # Create phase subfolder
    phase_dir = output_dir / "phase_1_vision"
    phase_dir.mkdir(parents=True, exist_ok=True)
    
    # Parallel processing with ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {
            executor.submit(analyze_image, img_file, trigger_word): img_file 
            for img_file in image_files
        }
        
        for future in tqdm(as_completed(futures), total=len(image_files), desc="📊 Vision Analysis", unit="img"):
            result = future.result()
            if result:
                prompts_data.append({'file_name': result['file_name'], 'prompt': result['prompt']})
                captions_data.append({'file_name': result['file_name'], 'caption': result['caption']})
                prompts_list.append(result['prompt'])
                captions_list.append(result['caption'])
    
    # Save prompts.csv
    prompts_csv = phase_dir / "prompts.csv"
    with open(prompts_csv, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['file_name', 'prompt'], quoting=csv.QUOTE_ALL)
        writer.writeheader()
        writer.writerows(prompts_data)
    
    # Save raw captions
    captions_csv = phase_dir / "captions_raw.csv"
    with open(captions_csv, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['file_name', 'caption'], quoting=csv.QUOTE_ALL)
        writer.writeheader()
        writer.writerows(captions_data)
    
    print(f"\n✅ Phase 1 Complete!")
    print(f"   📁 {phase_dir}")
    print(f"   📊 {len(prompts_list)} images analyzed")
    
    return prompts_list, captions_list


# ============================================================================
# PHASE 2: CONSENSUS ENGINE (Text-only)
# ============================================================================

def calculate_master_description(prompts: List[str], trigger_word: str) -> str:
    """Merge prompts into master description."""
    sample = prompts[:50]
    
    prompt = f"""Analyze these {len(sample)} physical descriptions of "{trigger_word}":

{chr(10).join(f"{i+1}. {desc}" for i, desc in enumerate(sample))}

Create ONE master description that captures the consensus traits.
Focus on features mentioned consistently.
Keep it 3-4 sentences, factual and specific.
Start with "{trigger_word}".

Master Description:"""
    
    response = ollama.chat(
        model=OLLAMA_TEXT_MODEL,
        messages=[{'role': 'user', 'content': prompt}]
    )
    
    return response['message']['content'].strip()


def extract_strip_keywords(prompts: List[str], trigger_word: str) -> List[str]:
    """Find constant traits appearing in >80% of prompts."""
    # Skip filler words
    filler = {'and', 'the', 'a', 'an', 'in', 'is', 'are', 'be', 'his', 'her', 'with', 'man', 'woman', 'person'}
    
    # Frequency analysis
    all_words = []
    for desc in prompts:
        words = desc.lower().replace(trigger_word.lower(), "").split()
        words = [w.strip('.,;:!?"()[]') for w in words 
                 if len(w) > 2 and w.lower() not in filler]
        all_words.extend(words)
    
    word_counts = Counter(all_words)
    total = len(prompts)
    
    # Find high-frequency words (appears in 80%+ of prompts)
    constants = []
    for word, count in word_counts.most_common(100):
        freq = count / total
        if freq >= CONSTANT_THRESHOLD:
            constants.append(word)
    
    # Additional explicit keywords likely to be constants
    common_traits = ['glasses', 'gray', 'grey', 'hair', 'suit', 'tie', 'formal', 'professional', 'dark', 'fair', 'complexion', 'skin']
    for trait in common_traits:
        if any(trait in desc.lower() for desc in prompts[:100]):
            # Check frequency
            count = sum(1 for desc in prompts if trait in desc.lower())
            if count / total >= CONSTANT_THRESHOLD and trait not in constants:
                constants.append(trait)
    
    return sorted(list(set(constants)))


def phase_2_consensus_engine(prompts_list: List[str], trigger_word: str, project_path: Path) -> List[str]:
    """Phase 2: Extract constants from prompts."""
    print("\n" + "="*70)
    print("PHASE 2: CONSENSUS ENGINE")
    print("="*70)
    print(f"🧠 Analyzing {len(prompts_list)} prompts...\n")
    
    # Master description
    master = calculate_master_description(prompts_list, trigger_word)
    master_path = project_path / "average_prompt.txt"
    master_path.write_text(master, encoding='utf-8')
    
    print(f"✅ Master Description:")
    print(f"   {master}\n")
    
    # Extract constants
    print(f"🔍 Identifying constant traits...\n")
    strip_keywords = extract_strip_keywords(prompts_list, trigger_word)
    
    strip_path = project_path / "strip_keywords.json"
    with open(strip_path, 'w') as f:
        json.dump(strip_keywords, f, indent=2)
    
    print(f"✅ Strip Keywords ({len(strip_keywords)}):")
    print(f"   {', '.join(strip_keywords)}\n")
    
    return strip_keywords


# ============================================================================
# PHASE 3: SUBTRACTIVE SAVE (Text-only, instant)
# ============================================================================

def strip_constants(text: str, keywords: List[str]) -> str:
    """Remove constant keywords from text, being careful not to corrupt it."""
    for keyword in keywords:
        # Only remove as whole words, surrounded by spaces or punctuation
        import re
        # Match keyword as whole word with word boundaries
        pattern = r'\b' + re.escape(keyword) + r'\b'
        text = re.sub(pattern, '', text, flags=re.IGNORECASE)
    
    # Clean extra spaces
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def phase_3_subtractive_save(image_files: List[Path], captions_list: List[str],
                             strip_keywords: List[str], input_dir: Path, output_dir: Path):
    """Phase 3: Clean captions and save outputs."""
    print("\n" + "="*70)
    print("PHASE 3: SUBTRACTIVE SAVE")
    print("="*70)
    print(f"💾 Cleaning and saving {len(captions_list)} captions...\n")
    
    # Create phase folder
    phase_dir = output_dir / "phase_3_final"
    phase_dir.mkdir(parents=True, exist_ok=True)
    
    successful = 0
    final_data = []
    
    for img_file, caption in zip(image_files, captions_list):
        try:
            # Strip constants
            cleaned = strip_constants(caption, strip_keywords)
            
            # Save caption
            txt_path = phase_dir / f"{img_file.stem}.txt"
            txt_path.write_text(cleaned, encoding='utf-8')
            
            # Copy image
            import shutil
            shutil.copy2(img_file, phase_dir / img_file.name)
            
            final_data.append({'file_name': img_file.name, 'caption': cleaned})
            successful += 1
            
        except Exception as e:
            print(f"⚠️  Error on {img_file.name}: {e}")
    
    # Save final CSV
    final_csv = phase_dir / "captions_final.csv"
    with open(final_csv, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['file_name', 'caption'])
        writer.writeheader()
        writer.writerows(final_data)
    
    print(f"\n✅ Phase 3 Complete!")
    print(f"   📁 {phase_dir}")
    print(f"   🎯 {successful}/{len(image_files)} saved")


# ============================================================================
# ORCHESTRATION
# ============================================================================

def run(slug: str):
    """Main: Phase 1 (vision) → Phase 2 (consensus) → Phase 3 (save)"""
    print("\n" + "="*70)
    print("IDENTITY-AWARE SUBTRACTIVE CAPTIONING")
    print("="*70)
    
    if not verify_ollama():
        return
    
    # Setup
    path = utils.get_project_path(slug)
    config = utils.load_config(slug)
    trigger_word = config.get('trigger') or utils.obfuscate_trigger(config.get('name', slug))
    
    # Read 256x256 resized images for faster captioning
    input_dir = path / "05_resize_256x256"
    output_dir = path / utils.DIRS.get('caption', '06_caption')
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Get images
    image_files = sorted(input_dir.glob("*.jpg"))
    if not image_files:
        print(f"❌ No images found in {input_dir}")
        return
    
    print(f"\n📊 Dataset: {len(image_files)} images")
    print(f"🎯 Trigger: {trigger_word}")
    print(f"🤖 Vision: {OLLAMA_VISION_MODEL} (sequential)")
    print(f"📝 Text: {OLLAMA_TEXT_MODEL}")
    
    # Run phases
    prompts_list, captions_list = phase_1_vision_analysis(image_files, trigger_word, output_dir)
    strip_keywords = phase_2_consensus_engine(prompts_list, trigger_word, path)
    phase_3_subtractive_save(image_files, captions_list, strip_keywords, input_dir, output_dir)
    
    # Summary
    print("\n" + "="*70)
    print("✅ PIPELINE COMPLETE")
    print("="*70)
    print(f"📁 Phase 1: {output_dir / 'phase_1_vision'}")
    print(f"📁 Phase 2: {path / 'average_prompt.txt'}")
    print(f"📁 Phase 3: {output_dir / 'phase_3_final'}")
    print(f"📊 Total: {len(image_files)} images")


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python 05_caption.py <slug>")
        sys.exit(1)
    run(sys.argv[1])
