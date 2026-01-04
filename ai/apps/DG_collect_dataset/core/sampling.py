"""
SAMPLING LOGIC: Stratified sampling for Tier-1 identity inference

Selects 10-20 representative images from a dataset using:
1. Size stratification (S, M, L buckets)
2. Entropy-based diversity selection (edge frequency)
3. Balanced sampling across strata
"""

import numpy as np
from pathlib import Path
from typing import List, Tuple
from PIL import Image
import cv2
from tqdm import tqdm


def compute_image_entropy(img_path: Path) -> float:
    """
    Compute Laplacian variance as a proxy for visual complexity/entropy.
    
    High variance = sharp, detailed image (good for identity inference)
    Low variance = blurry, low-contrast image (bad for identity inference)
    
    Returns float in [0, 1] range (normalized).
    """
    try:
        # Read as grayscale
        img = cv2.imread(str(img_path), cv2.IMREAD_GRAYSCALE)
        if img is None:
            return 0.0
        
        # Compute Laplacian (edge detection)
        laplacian = cv2.Laplacian(img, cv2.CV_64F)
        
        # Variance of Laplacian = measure of sharpness
        variance = np.var(laplacian)
        
        # Normalize to [0, 1] (empirical ceiling ~1000 for typical images)
        normalized = min(variance / 1000.0, 1.0)
        return float(normalized)
    
    except Exception as e:
        print(f"⚠️  Error computing entropy for {img_path.name}: {e}")
        return 0.5  # Neutral fallback


def get_image_size_category(img_path: Path) -> str:
    """
    Categorize image by dimensions into Small / Medium / Large buckets.
    
    Returns: 'S' (small), 'M' (medium), or 'L' (large)
    """
    try:
        img = Image.open(img_path)
        width, height = img.size
        area = width * height
        
        # Empirical thresholds (adjust based on dataset)
        if area < 400_000:      # < ~632×632
            return 'S'
        elif area < 1_000_000:  # < ~1000×1000
            return 'M'
        else:
            return 'L'
    
    except Exception as e:
        print(f"⚠️  Error reading image dimensions for {img_path.name}: {e}")
        return 'M'  # Neutral fallback


def stratified_sample(image_files: List[Path], sample_size: int = 16) -> Tuple[List[Path], dict]:
    """
    Stratified sampling: Select representative images balancing size and entropy.
    
    Args:
        image_files: List of image paths to sample from
        sample_size: Target number of images to select (default 16, 10-20 recommended)
    
    Returns:
        (sampled_paths, metadata_dict)
        where metadata_dict contains:
            - 'total_images': total images in dataset
            - 'sampled_count': actual count of selected images
            - 'strata': breakdown by size category
            - 'entropy_scores': entropy values for sampled images
    """
    
    if len(image_files) <= sample_size:
        print(f"⚠️  Dataset has {len(image_files)} images; sample_size {sample_size} is excessive.")
        print(f"   Using all images.")
        return sorted(image_files), {
            'total_images': len(image_files),
            'sampled_count': len(image_files),
            'strata': {},
            'entropy_scores': {},
            'note': 'Full dataset used (smaller than sample_size)'
        }
    
    print("\n" + "="*70)
    print("SAMPLING: Stratified Selection for Tier-1 Identity Inference")
    print("="*70)
    print(f"📊 Dataset: {len(image_files)} images")
    print(f"🎯 Target sample: {sample_size} images")
    print(f"📐 Strategy: Size-stratified + entropy-balanced\n")
    
    # ---- STEP 1: Categorize by size ----
    print("📏 Categorizing images by size...")
    
    size_buckets = {'S': [], 'M': [], 'L': []}
    for img_path in image_files:
        category = get_image_size_category(img_path)
        size_buckets[category].append(img_path)
    
    print(f"   Small:  {len(size_buckets['S'])} images")
    print(f"   Medium: {len(size_buckets['M'])} images")
    print(f"   Large:  {len(size_buckets['L'])} images\n")
    
    # ---- STEP 2: Compute entropy for each bucket ----
    print("⚡ Computing image entropy (sharpness/clarity)...")
    
    entropy_map = {}
    for category, images in size_buckets.items():
        if images:
            for img_path in tqdm(images, desc=f"  {category} bucket", unit="img", disable=len(images) < 10):
                entropy_map[img_path] = compute_image_entropy(img_path)
    
    print()
    
    # ---- STEP 3: Allocate sample slots to buckets ----
    # Proportional allocation: if dataset is 30% small, allocate 30% of sample to small
    
    allocations = {}
    total_per_bucket = sum(len(images) for images in size_buckets.values())
    
    for category in ['S', 'M', 'L']:
        bucket_size = len(size_buckets[category])
        if bucket_size == 0:
            allocations[category] = 0
        else:
            proportion = bucket_size / total_per_bucket
            allocated = max(1, int(np.round(proportion * sample_size)))
            allocations[category] = allocated
    
    # Adjust if total doesn't match (rounding artifact)
    total_allocated = sum(allocations.values())
    if total_allocated > sample_size:
        # Reduce largest bucket
        largest_cat = max(allocations, key=allocations.get)
        allocations[largest_cat] -= (total_allocated - sample_size)
    elif total_allocated < sample_size:
        # Increase largest bucket
        largest_cat = max(allocations, key=allocations.get)
        allocations[largest_cat] += (sample_size - total_allocated)
    
    print(f"📌 Allocated sample slots by size:")
    for cat in ['S', 'M', 'L']:
        print(f"   {cat}: {allocations[cat]} / {len(size_buckets[cat])}")
    print()
    
    # ---- STEP 4: Select highest-entropy images from each bucket ----
    print(f"🎲 Selecting highest-entropy images from each bucket...\n")
    
    sampled = []
    sampled_by_category = {'S': [], 'M': [], 'L': []}
    
    for category in ['S', 'M', 'L']:
        images = size_buckets[category]
        if not images:
            continue
        
        target_count = allocations[category]
        
        # Sort by entropy (descending)
        sorted_images = sorted(
            images,
            key=lambda p: entropy_map.get(p, 0.5),
            reverse=True
        )
        
        # Take top N
        selected = sorted_images[:target_count]
        sampled.extend(selected)
        sampled_by_category[category] = selected
        
        avg_entropy = np.mean([entropy_map[p] for p in selected])
        print(f"   {category}: Selected {len(selected)} images (avg entropy: {avg_entropy:.3f})")
    
    print()
    
    # ---- STEP 5: Sort sampled images by original order ----
    sampled_sorted = sorted(sampled, key=lambda p: image_files.index(p))
    
    # ---- BUILD METADATA ----
    entropy_scores = {img.name: entropy_map[img] for img in sampled_sorted}
    
    metadata = {
        'total_images': len(image_files),
        'sampled_count': len(sampled_sorted),
        'strata': {
            'small': len(sampled_by_category['S']),
            'medium': len(sampled_by_category['M']),
            'large': len(sampled_by_category['L'])
        },
        'entropy_scores': entropy_scores,
        'sampling_method': 'stratified_entropy_balanced'
    }
    
    print(f"✅ Sampling Complete!")
    print(f"   Selected: {len(sampled_sorted)} / {len(image_files)} images")
    print(f"   Strata: S={metadata['strata']['small']} M={metadata['strata']['medium']} L={metadata['strata']['large']}")
    
    return sampled_sorted, metadata


def save_sample_manifest(sampled_paths: List[Path], output_dir: Path, metadata: dict):
    """
    Save sample manifest: list of selected image names + entropy scores.
    
    Outputs:
    - identity_sample_manifest.txt: Plain list of selected images
    - identity_sample_manifest.json: Manifest with metadata
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Text manifest
    manifest_txt = output_dir / "identity_sample_manifest.txt"
    with open(manifest_txt, 'w') as f:
        for img_path in sampled_paths:
            f.write(f"{img_path.name}\n")
    
    # JSON manifest with metadata
    import json
    manifest_json = output_dir / "identity_sample_manifest.json"
    with open(manifest_json, 'w') as f:
        json.dump({
            'total_dataset_images': metadata['total_images'],
            'sampled_images': [img.name for img in sampled_paths],
            'sampled_count': metadata['sampled_count'],
            'strata_breakdown': metadata['strata'],
            'entropy_scores': metadata['entropy_scores'],
            'sampling_method': metadata.get('sampling_method', 'unknown')
        }, f, indent=2)
    
    print(f"\n📁 Manifest saved:")
    print(f"   {manifest_txt}")
    print(f"   {manifest_json}")


if __name__ == "__main__":
    # Test / example usage
    import sys
    if len(sys.argv) < 2:
        print("Usage: python 05_sampling.py <input_dir>")
        sys.exit(1)
    
    input_dir = Path(sys.argv[1])
    image_files = sorted(input_dir.glob("*.jpg"))
    
    sampled, metadata = stratified_sample(image_files, sample_size=16)
    
    # Optionally save manifest
    output_dir = input_dir.parent / "identity_sample"
    save_sample_manifest(sampled, output_dir, metadata)
    
    print(f"\n✅ Sampled images ready in: {output_dir}")
