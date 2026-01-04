"""
TIER 3: FUSION & CLEANUP
Programmatic merge of identity + variation captions.
No vision models required (instant execution).

Applies:
- Keyword deduplication
- Subtractive keyword logic
- Output structuring

Outputs: final_captions.csv, final_captions/*.txt
"""

import csv
import json
from pathlib import Path
from typing import List, Dict
from collections import Counter
import re

# Import utils
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
import utils

# Configuration
CONSTANT_THRESHOLD = 0.8  # Keywords appearing in >80% of variations


def load_identity(identity_dir: Path) -> str:
    """
    Load master identity description from Tier-1 output.
    
    Returns: master identity text
    """
    identity_txt = identity_dir / "identity.txt"
    if not identity_txt.exists():
        print(f"⚠️  Identity file not found: {identity_txt}")
        return ""
    
    return identity_txt.read_text(encoding='utf-8').strip()


def load_variations(variations_dir: Path) -> Dict[str, str]:
    """
    Load variation captions from Tier-2 output.
    
    Returns: {file_name: variation_caption}
    """
    variations_csv = variations_dir / "variations.csv"
    
    if not variations_csv.exists():
        print(f"⚠️  Variations file not found: {variations_csv}")
        return {}
    
    variations = {}
    with open(variations_csv, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            variations[row['file_name']] = row['variation_caption']
    
    return variations


def extract_strip_keywords(variations: Dict[str, str]) -> List[str]:
    """
    Find constant traits appearing in >80% of variation captions.
    
    These are scene elements that appear consistently and should be stripped
    to avoid redundancy in final captions.
    
    Returns: list of keywords to remove
    """
    if not variations:
        return []
    
    # Tokenize and count word frequencies
    all_words = []
    for caption in variations.values():
        words = caption.lower().split()
        words = [
            re.sub(r'[.,;:!?"()\[\]]', '', w)
            for w in words
            if len(w) > 3
        ]
        all_words.extend(words)
    
    word_counts = Counter(all_words)
    total_captions = len(variations)
    
    # Find high-frequency words (>80% threshold)
    strip_keywords = []
    for word, count in word_counts.most_common(100):
        frequency = count / total_captions
        if frequency >= CONSTANT_THRESHOLD:
            strip_keywords.append(word)
    
    return sorted(strip_keywords)


def strip_constants(text: str, keywords: List[str]) -> str:
    """
    Remove constant keywords from text (case-insensitive).
    
    Args:
        text: Input caption text
        keywords: List of keywords to remove
    
    Returns: Cleaned text
    """
    for keyword in keywords:
        # Remove exact word matches (word boundaries)
        pattern = r'\b' + re.escape(keyword) + r'\b'
        text = re.sub(pattern, '', text, flags=re.IGNORECASE)
    
    # Clean up extra spaces
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text


def fuse_identity_variation(identity: str, variation: str, trigger_word: str,
                           strip_keywords: List[str]) -> str:
    """
    Merge identity and variation captions into a single, deduplicated caption.
    
    Algorithm:
    1. Combine identity + variation
    2. Remove high-frequency keywords (reduce redundancy)
    3. Clean punctuation and spacing
    4. Ensure trigger word appears first
    
    Args:
        identity: Master identity description
        variation: Per-image variation caption
        trigger_word: Trigger word (subject name)
        strip_keywords: High-frequency keywords to remove
    
    Returns: Fused caption
    """
    # Combine
    fused = f"{identity} {variation}"
    
    # Remove high-frequency keywords
    fused = strip_constants(fused, strip_keywords)
    
    # Remove duplicate sentences (simple check)
    sentences = [s.strip() for s in fused.split('.') if s.strip()]
    seen = set()
    unique_sentences = []
    for sent in sentences:
        sent_lower = sent.lower()
        if sent_lower not in seen:
            seen.add(sent_lower)
            unique_sentences.append(sent)
    
    fused = '. '.join(unique_sentences)
    if not fused.endswith('.'):
        fused += '.'
    
    # Ensure trigger word first
    if not fused.lower().startswith(trigger_word.lower()):
        fused = f"{trigger_word} {fused}"
    
    # Clean up extra spaces
    fused = re.sub(r'\s+', ' ', fused).strip()
    
    return fused


def run_fusion(identity_dir: Path, variations_dir: Path, trigger_word: str,
               image_files: List[Path], output_dir: Path) -> Dict[str, str]:
    """
    Tier 3: Fuse identity + variations into final captions.
    
    Returns: {file_name: final_caption}
    """
    print("\n" + "="*70)
    print("TIER 3: FUSION & CLEANUP (Programmatic)")
    print("="*70)
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Step 1: Load identity and variations
    print(f"\n📖 Loading identity and variations...")
    
    identity = load_identity(identity_dir)
    if not identity:
        print("❌ Identity not found. Cannot proceed with fusion.")
        return {}
    
    variations = load_variations(variations_dir)
    if not variations:
        print("❌ Variations not found. Cannot proceed with fusion.")
        return {}
    
    print(f"✅ Loaded:")
    print(f"   Identity: {identity[:60]}...")
    print(f"   Variations: {len(variations)} captions\n")
    
    # Step 2: Extract strip keywords
    print(f"🔍 Extracting high-frequency keywords...")
    strip_keywords = extract_strip_keywords(variations)
    print(f"✅ Found {len(strip_keywords)} constant keywords to strip")
    if strip_keywords:
        print(f"   Examples: {', '.join(strip_keywords[:10])}\n")
    
    # Step 3: Fuse captions
    print(f"🔀 Fusing identity + variations...")
    
    final_captions = {}
    raw_dir = output_dir / "final_captions_raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    
    for img_file in image_files:
        if img_file.name not in variations:
            print(f"⚠️  No variation found for {img_file.name}")
            continue
        
        variation = variations[img_file.name]
        fused = fuse_identity_variation(identity, variation, trigger_word, strip_keywords)
        
        final_captions[img_file.name] = fused
        
        # Save individual caption file
        caption_path = raw_dir / f"{img_file.stem}.txt"
        caption_path.write_text(fused, encoding='utf-8')
    
    print(f"✅ Fused {len(final_captions)} captions\n")
    
    return final_captions


def save_final_artifacts(final_captions: Dict[str, str], output_dir: Path, trigger_word: str):
    """
    Save final caption artifacts:
    - final_captions.csv: file_name, final_caption (in parent dir)
    - final_captions_raw/*.txt: individual caption files
    - metadata.json: pipeline metadata
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # CSV output - save in parent directory (project root)
    final_csv = output_dir.parent / "final_captions.csv"
    with open(final_csv, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['file_name', 'final_caption'])
        writer.writeheader()
        for file_name, caption in sorted(final_captions.items()):
            writer.writerow({'file_name': file_name, 'final_caption': caption})
    
    # Metadata
    metadata_json = output_dir / "metadata.json"
    with open(metadata_json, 'w') as f:
        json.dump({
            'trigger_word': trigger_word,
            'pipeline': 'tier-separated-3-phase',
            'phase_3': 'fusion_and_cleanup',
            'total_captions': len(final_captions),
            'outputs': {
                'final_captions_csv': 'final_captions.csv',
                'final_captions_raw': 'final_captions_raw/',
                'metadata': 'metadata.json'
            }
        }, f, indent=2)
    
    print("="*70)
    print("SAVING ARTIFACTS")
    print("="*70)
    print(f"\n📊 {final_csv}")
    print(f"📁 Raw files: {output_dir / 'final_captions_raw'} ({len(final_captions)} files)")
    print(f"📝 {metadata_json}")


# ============================================================================
# ORCHESTRATION
# ============================================================================

def run(slug: str):
    """
    Main: Tier 3 fusion
    
    1. Load identity (from Tier-1)
    2. Load variations (from Tier-2)
    3. Fuse into final captions
    4. Save outputs
    """
    print("\n" + "="*70)
    print("TIER 3: FUSION & CLEANUP PIPELINE")
    print("="*70)
    
    # Setup
    path = utils.get_project_path(slug)
    config = utils.load_config(slug)
    trigger_word = config.get('trigger') or utils.obfuscate_trigger(config.get('name', slug))
    
    identity_dir = path / "06_caption" / "identity"
    variations_dir = path / "06_caption" / "captions"
    output_dir = path / "06_caption" / "final_captions"
    
    # Verify Tier-1 and Tier-2 outputs exist
    if not identity_dir.exists() or not (identity_dir / "identity.txt").exists():
        print(f"❌ Identity not found. Run Tier-1 first: {identity_dir}")
        return
    
    if not variations_dir.exists() or not (variations_dir / "variations.csv").exists():
        print(f"❌ Variations not found. Run Tier-2 first: {variations_dir}")
        return
    
    # Get all images for reference
    input_dir = path / utils.DIRS.get('clean', '04_clean')
    image_files = sorted(input_dir.glob("*.jpg"))
    
    print(f"\n📊 Dataset: {len(image_files)} images")
    print(f"🎯 Trigger: {trigger_word}")
    
    # Run fusion
    final_captions = run_fusion(identity_dir, variations_dir, trigger_word, 
                               image_files, output_dir)
    
    # Save outputs
    save_final_artifacts(final_captions, output_dir, trigger_word)
    
    print("\n" + "="*70)
    print("✅ TIER 3 COMPLETE")
    print("="*70)
    print(f"📁 Output: {output_dir}")
    print(f"📊 Final captions: {output_dir / 'final_captions.csv'}")
    print(f"🎯 Total captions: {len(final_captions)}")
    print(f"\n✨ Pipeline complete! Ready for training.")


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python 07_fusion.py <slug>")
        sys.exit(1)
    run(sys.argv[1])
