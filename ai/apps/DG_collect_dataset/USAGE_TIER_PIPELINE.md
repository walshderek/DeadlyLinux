# Tier-Separated Captioning Pipeline: Usage Guide

## Overview

The new pipeline separates identity inference from variation captioning into three independent tiers, dramatically improving performance when using heavy vision models like Qwen3-VL.

**Old approach:** All images → Qwen3-VL (8B model) → Hours of processing
**New approach:** Sample → Qwen3-VL + All images → LLaVA-7B + Fusion → Minutes

## Quick Start

### 1. Full Pipeline (All Tiers)

```bash
# Run all three tiers
cd /home/seanf/deadlygraphics/ai/apps/DG_collect_dataset
python DG_collect_dataset_tier.py "Person Name" --trigger-mode

# Example
python DG_collect_dataset_tier.py "Theresa May" --tier-mode
```

### 2. Individual Tiers

```bash
# Tier 1 only (identity inference on sample)
python DG_collect_dataset_tier.py "Person Name" --tier-mode --tier 1

# Tier 2 only (variation captioning on all images)
python DG_collect_dataset_tier.py "Person Name" --tier-mode --tier 2

# Tier 3 only (fusion)
python DG_collect_dataset_tier.py "Person Name" --tier-mode --tier 3
```

## What Each Tier Does

### Tier 1: Identity Inference

**Purpose:** Extract permanent identity traits from a small representative sample

**Input:**
- All images from `04_clean/`

**Process:**
1. Intelligently sample 16 representative images (stratified by size, sorted by clarity)
2. Run Qwen3-VL (heavy 8B model) on each sampled image
3. Synthesize a master identity description

**Output:**
```
05_identity/
├── identity.txt              # Master identity (3-4 sentences)
├── identity.json             # Structured identity data
├── identity_raw.csv          # Per-image identity descriptions
├── identity_sample_manifest.txt  # List of sampled images
└── identity_sample_manifest.json # Sampling metadata
```

**Example `identity.txt`:**
```
Theresa May has a fair complexion, brown eyes, and shoulder-length light brown hair. 
She has an angular face with defined cheekbones and fair skin. Age appears to be in 
her 60s. She typically wears business attire.
```

**Timing:**
- 16 images × 0.5–1 sec/image = 8–16 seconds inference
- Plus Ollama overhead: ~5–10 minutes total
- **One-time cost per dataset**

### Tier 2: Variation Captioning

**Purpose:** Capture scene-specific context (clothing, pose, lighting) for each image

**Input:**
- All images from `04_clean/`

**Process:**
1. Run lightweight vision model (LLaVA-7B) on every image
2. Prompt explicitly excludes identity traits
3. Focus on clothing, pose, environment, lighting

**Output:**
```
06_variations/
├── variations.csv           # CSV: file_name, variation_caption
└── variations_raw/          # Individual .txt files per image
    ├── image_001.txt
    ├── image_002.txt
    └── ...
```

**Example variation caption:**
```
Theresa May wearing a dark navy suit jacket with a pearl necklace. 
Standing in formal parliamentary setting, neutral expression. 
Professional office background with soft fluorescent lighting.
```

**Timing:**
- LLaVA-7B: ~0.05–0.1 sec/image
- 500 images: 25–50 seconds inference + overhead = 30–60 minutes
- **Scales linearly with dataset size**

### Tier 3: Fusion & Cleanup

**Purpose:** Merge identity + variation into final training captions

**Input:**
- `05_identity/identity.txt`
- `06_variations/variations.csv`

**Process:**
1. Combine identity + variation for each image
2. Remove high-frequency keywords (redundancy reduction)
3. Deduplicate sentences
4. Ensure trigger word appears first

**Output:**
```
07_final_captions/
├── final_captions.csv       # CSV: file_name, final_caption
├── final_captions_raw/      # Individual .txt files (ready for training)
│   ├── image_001.txt
│   ├── image_002.txt
│   └── ...
└── metadata.json            # Pipeline metadata
```

**Example final caption:**
```
Theresa May has a fair complexion, brown eyes, and shoulder-length light brown hair. 
She has an angular face with defined cheekbones. Wearing a dark navy suit jacket 
with a pearl necklace. Standing in formal parliamentary setting with soft fluorescent 
lighting.
```

**Timing:**
- Purely programmatic (no vision inference)
- **Seconds for any dataset size**

## Project Structure

```
DG_collect_dataset/
├── DG_collect_dataset.py            # Legacy orchestrator (steps 1-8)
├── DG_collect_dataset_tier.py       # NEW: Tier-separated orchestrator
├── ARCHITECTURE_REFACTOR.md         # This design document
├── USAGE_TIER_PIPELINE.md           # This file
│
└── core/
    ├── 01_setup_scrape.py
    ├── 02_crop.py
    ├── 03_validate.py
    ├── 04_clean.py
    ├── 05_resize.py
    │
    ├── 05_sampling.py               # NEW: Sampling logic
    ├── 05_identity_inference.py     # NEW: Tier 1
    ├── 06_variation_captioning.py   # NEW: Tier 2
    ├── 07_fusion.py                 # NEW: Tier 3
    │
    ├── 06_caption.py                # Old monolithic caption (DEPRECATED)
    ├── 07_publish.py
    ├── 08_summary.py
    └── utils.py
```

## Workflow Examples

### Example 1: Process a New Person

```bash
# Step 1: Setup and crop
python DG_collect_dataset.py "Theresa May" --only-step 1
python DG_collect_dataset.py "Theresa May" --only-step 2
python DG_collect_dataset.py "Theresa May" --only-step 3
python DG_collect_dataset.py "Theresa May" --only-step 4

# Step 2: Run tier-separated captioning
python DG_collect_dataset_tier.py "Theresa May" --tier-mode

# Step 3: Publish
python DG_collect_dataset.py "Theresa May" --only-step 7

# Step 4: Summary
python DG_collect_dataset.py "Theresa May" --only-step 8
```

### Example 2: Rerun Only Captioning (with Existing Identity)

If you already have identity captions and want to re-run Tier 2 and 3:

```bash
# Re-run variation captioning and fusion
python DG_collect_dataset_tier.py "Theresa May" --tier-mode --tier 2
python DG_collect_dataset_tier.py "Theresa May" --tier-mode --tier 3
```

### Example 3: Debug Specific Tier

```bash
# Run each tier independently to debug
python DG_collect_dataset_tier.py "Theresa May" --tier-mode --tier 1
# Check: outputs/theresa_may/05_identity/identity.txt

python DG_collect_dataset_tier.py "Theresa May" --tier-mode --tier 2
# Check: outputs/theresa_may/06_variations/variations.csv

python DG_collect_dataset_tier.py "Theresa May" --tier-mode --tier 3
# Check: outputs/theresa_may/07_final_captions/final_captions.csv
```

## Output Locations

```
outputs/
└── [slug]/
    ├── 01_setup_scrape/         # Raw download
    ├── 02_crop/                 # Cropped to faces
    ├── 03_validate/             # BLIP-filtered valid faces
    ├── 04_clean/                # Final input (all images)
    ├── 05_resize/               # Resized versions
    │
    ├── 05_identity/             # TIER 1 OUTPUT
    │   ├── identity.txt
    │   ├── identity.json
    │   └── identity_raw.csv
    │
    ├── 06_variations/           # TIER 2 OUTPUT
    │   ├── variations.csv
    │   └── variations_raw/
    │
    ├── 07_final_captions/       # TIER 3 OUTPUT
    │   ├── final_captions.csv
    │   ├── final_captions_raw/
    │   └── metadata.json
    │
    ├── 07_publish/              # Training-ready data
    └── 08_summary/              # Summary reports
```

## Model Configuration

### Tier 1: Heavy VLM
- **Default:** `qwen3-vl` (Qwen3-VL-8B)
- **Alternatives:** Any Ollama-compatible vision model (larger = better quality, slower)
- **Edit:** [core/05_identity_inference.py](core/05_identity_inference.py) line ~28

### Tier 2: Lightweight VLM
- **Default:** `llava:7b` (LLaVA-7B)
- **Alternatives:** `llava:13b`, `bakllava`, `moondream`, `florence`
- **Edit:** [core/06_variation_captioning.py](core/06_variation_captioning.py) line ~22

### Text Model (Consensus)
- **Default:** `qwen3` (Qwen 3 7B)
- **Edit:** [core/05_identity_inference.py](core/05_identity_inference.py) line ~29

## Performance Notes

### Single Machine (Consumer GPU)

| Dataset Size | Tier 1 | Tier 2 | Tier 3 | **Total** |
|---|---|---|---|---|
| 50 images | 5 min | 5–8 min | 1 sec | **10–13 min** |
| 100 images | 5 min | 10–16 min | 1 sec | **15–21 min** |
| 500 images | 5 min | 50–80 min | 1 sec | **55–85 min** |
| 1000 images | 5 min | 100–160 min | 2 sec | **105–165 min** |

**Why Tier 1 is constant:** Only 16 images sampled; rest go to Tier 2

**Why Tier 2 scales linearly:** Lightweight model is ~10× faster than heavy VLM

**Old approach (all through Qwen):**
- 100 images: 50–100 minutes (5 min inference per image)
- 500 images: 250–500 minutes (4+ hours)
- **Not practical for large datasets**

### GPU Memory

- **Tier 1 (Qwen3-VL):** 8GB+ (run one at a time)
- **Tier 2 (LLaVA-7B):** 4–6GB (lightweight)
- **Tier 3 (Programmatic):** Negligible

If memory is constrained, Tier 1 and Tier 2 can run at different times.

## Troubleshooting

### Issue: "Cannot connect to Ollama"

```bash
# Check Ollama is running
ollama serve
# In another terminal, verify
ollama list
```

### Issue: Model not found

```bash
# Download required models
ollama pull qwen3-vl      # Tier 1
ollama pull llava:7b      # Tier 2
ollama pull qwen3         # Consensus
```

### Issue: Out of memory

- Reduce sample size in Tier 1: Edit [core/05_sampling.py](core/05_sampling.py) line ~74
- Switch to smaller model: e.g., `llava:7b` instead of `llava:13b`
- Run tiers on different days/machines

### Issue: Poor identity descriptions

- Check sampled images: `05_identity/identity_sample_manifest.txt`
- Increase sample size: Edit `sample_size=20` in [core/05_identity_inference.py](core/05_identity_inference.py) line ~218
- Verify Tier 1 model quality: Try `qwen2-vl` or `llava:13b` instead

### Issue: Repetitive variation captions

- This is normal; Tier 3 removes redundancy
- Check final output: `07_final_captions/final_captions.csv`
- Adjust `CONSTANT_THRESHOLD` in [core/07_fusion.py](core/07_fusion.py) to be stricter

## Extending the Pipeline

### Adding a Fourth Tier (Custom Processing)

Create `08_custom_processing.py`:

```python
def run(slug: str):
    path = utils.get_project_path(slug)
    final_dir = path / "07_final_captions"
    
    # Read final captions
    final_csv = final_dir / "final_captions.csv"
    # ... your custom logic ...
    
    # Save outputs
    output_dir = path / "08_custom"
    output_dir.mkdir(parents=True, exist_ok=True)
    # ... save your outputs ...
```

Then register in `DG_collect_dataset_tier.py`:

```python
TIER_PIPELINE = {
    1: "05_identity_inference",
    2: "06_variation_captioning",
    3: "07_fusion",
    4: "08_custom_processing"  # NEW
}
```

### Customizing Prompts

Edit the prompt functions:
- **Tier 1:** `get_identity_prompt()` in [core/05_identity_inference.py](core/05_identity_inference.py) line ~35
- **Tier 2:** `get_variation_prompt()` in [core/06_variation_captioning.py](core/06_variation_captioning.py) line ~29

### Changing Sampling Strategy

Edit [core/05_sampling.py](core/05_sampling.py):
- Size bucket thresholds: Line ~71
- Entropy weighting: Line ~106
- Sample allocation: Line ~125

## Backwards Compatibility

The old pipeline still works:

```bash
# Legacy (all steps 1-8, monolithic caption at step 6)
python DG_collect_dataset.py "Theresa May"

# New (separate tiers for captions)
python DG_collect_dataset_tier.py "Theresa May" --tier-mode
```

**Recommendation:** Use new tier-separated pipeline for all future projects.

## Architecture Reference

See [ARCHITECTURE_REFACTOR.md](ARCHITECTURE_REFACTOR.md) for:
- Design rationale
- Scaling analysis
- Why parallelization won't help
- Academic references

---

**Status:** Production-ready
**Last Updated:** January 2026
**Maintainer:** ML Systems Engineering
