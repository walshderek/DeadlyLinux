# DG Captioning Pipeline: Architectural Refactor

## Problem Statement

The original pipeline processed **all images through Qwen3-VL** (a heavy 8B parameter VLM), treating identity inference and variation captioning as identical tasks. This caused runtime explosion: minutes → hours.

The architectural error: Conflating two fundamentally different problems:
1. **Identity inference** (permanent traits): face, hair, skin tone, body build — computed once, used everywhere
2. **Variation captioning** (scene-specific): clothing, pose, lighting, environment — changes per image

Processing all images through a heavy VLM is unnecessary. Identity traits should be extracted from a small representative sample once, then reused.

---

## Proposed Architecture: 3-Tier Separated Pipeline

### Tier 1: Identity Inference (Slow, Small Sample)
- **Model:** Qwen3-VL-8B (heavy VLM, single-stream only)
- **Input:** 10–20 carefully sampled representative images
- **Execution:** Sequential (GPU-bound, no parallelization)
- **Output:**
  - `identity.json`: structured identity traits (face, hair, eyes, skin, build, age_range)
  - `identity.txt`: natural-language master identity description
- **Duration:** ~5–10 minutes (one-time cost per dataset)
- **Purpose:** Extract consensus identity traits appearing across the sample

**Why it works:**
- Heavy VLM inference is expensive (0.5–1 sec per image on consumer GPU)
- Identity traits are **static** — no need to recompute for every image
- Small sample captures sufficient variance; larger samples show diminishing returns
- Sampling is intelligent: size-balanced, diversity-balanced within size buckets

### Tier 2: Variation Captioning (Fast, All Images)
- **Model:** LLaVA-7B or BLIP or Florence-2 (lightweight vision model)
- **Input:** All images (full dataset)
- **Execution:** Sequential single-stream (Ollama constraint)
- **Prompt:** Explicitly exclude identity traits; focus on scene context
- **Output:**
  - `variations.csv`: file_name, variation_caption (per-image)
  - `variations_raw/`: individual `.txt` files
- **Duration:** ~30–60 minutes for 500 images (~0.1 sec/image)
- **Purpose:** Capture image-specific context (clothing, pose, environment, lighting)

**Why it works:**
- Lightweight models are 5–10× faster than heavy VLMs
- Prompts explicitly exclude identity keywords (face, hair, eyes, etc.)
- Variation is **image-specific** — must be computed per image
- Still single-stream (Ollama is GPU-bound, no parallelization helps)

### Tier 3: Fusion & Cleanup (No Vision Models)
- **Input:**
  - `identity.json` (from Tier 1)
  - `variations.csv` (from Tier 2)
- **Processing:** Programmatic text manipulation + subtractive keyword logic
- **Output:**
  - `final_captions.csv`: file_name, fused_caption
  - `final_captions/`: individual `.txt` files (ready for training)
- **Duration:** Seconds
- **Purpose:** Merge identity + variation, deduplicate, clean artifacts

**Why it works:**
- Zero vision inference — instant
- Reuses Tier 2's consensus/subtractive logic
- Final captions are structured: `[IDENTITY] + [VARIATION] - [DUPLICATES]`

---

## Sampling Strategy (Tier 1)

Selecting 10–20 representative images is non-trivial. Naive random sampling may miss variation.

### Algorithm: Stratified Size & Diversity Sampling

1. **Compute image sizes:** Group images into buckets (S, M, L)
2. **Within each bucket:** Select images with maximum visual entropy
   - Entropy proxy: Laplacian variance (edge frequency)
   - Or: Simple histogram diversity score
3. **Balanced selection:** ~5–7 images per size bucket
4. **Output:** `identity_sample.txt` (image names) + `identity_sample/` (copy of sampled images)

**Rationale:**
- Datasets often have implicit clusterings (different sizes, lighting)
- Stratified sampling ensures diverse representation
- Size-balancing prevents bias toward dominant clusters
- Entropy-based selection avoids blurry/underexposed images

---

## Scaling & Performance Notes

### Why this architecture scales:

1. **Constant Tier-1 cost:** 10–20 images → 5–10 min, regardless of dataset size
   - 100 images: 5 min (Tier 1) + 10 min (Tier 2) = 15 min total ✓
   - 1000 images: 5 min (Tier 1) + 100 min (Tier 2) = 105 min total ✓
   - Original (all images through Qwen): 5000 min = 83 hours ✗

2. **Linear Tier-2 scaling:** Lightweight model → O(n) with low constant
   - No parallelization possible (Ollama single-stream GPU-bound)
   - But lightweight models are 5–10× faster → acceptable

3. **Negligible Tier-3:** Programmatic text processing is instant

4. **Reusability:** Identity traits computed once; shared across all images

### Impossibilities (do NOT attempt):

- ❌ Parallelizing Ollama vision inference (GPU-bound, no batching)
- ❌ Micro-tuning Qwen prompts (time-complexity won't change)
- ❌ Merging tiers (defeats the purpose; re-creates the original problem)
- ❌ Using smaller VLMs for identity (loss of quality)

### Correct assumptions baked into design:

- ✓ Ollama vision calls are GPU-bound single-stream
- ✓ Image compression is lossless for vision models
- ✓ Identity inference doesn't need exhaustive coverage
- ✓ Variation captions are always image-specific

---

## Implementation Details

### Code Structure

```
core/
├── 05_identity_inference.py    # Tier 1: Heavy VLM on sample
├── 05_sampling.py              # Utility: Stratified sampling
├── 06_variation_captioning.py  # Tier 2: Lightweight VLM on all
├── 07_fusion.py                # Tier 3: Programmatic merge
└── [existing files]
```

### Phase Boundaries

Each tier produces well-defined outputs; tiers can run independently:

```
Tier 1 → identity.json, identity.txt
         ↓
Tier 2 → variations.csv, variations_raw/*.txt
         ↓
Tier 3 → final_captions.csv, final_captions/*.txt
```

This allows:
- Rerunning Tier 2/3 without Tier 1 (if identity is stable)
- Debugging each tier independently
- Caching identity results across multiple datasets

---

## Prompt Design

### Tier 1: Identity Inference Prompt

```
Analyze this image of [TRIGGER_WORD].
Extract PERMANENT IDENTITY TRAITS that persist across all photos:
- Face shape and features (if visible)
- Hair color, length, style
- Eye color (if visible)
- Body build / silhouette
- Skin tone
- Approximate age range
- Any distinctive marks or features

Be specific and factual. Avoid clothing, pose, or background.
Respond in 5-6 sentences.
```

### Tier 2: Variation Captioning Prompt

```
Analyze this image. Describe what is UNIQUE to this photo:
- Clothing and accessories
- Pose and body position
- Setting / background
- Lighting and mood
- Camera angle / framing

IMPORTANT: Do NOT describe face, hair, eyes, body build, or skin tone.
Those are handled separately.
Keep it concise: 3-4 sentences.
```

### Tier 3: Fusion Logic (Programmatic)

```python
# Pseudo-code
fused = f"{trigger_word} {identity_traits}. {variation_caption}."
fused = remove_duplicate_keywords(fused)
fused = remove_high_frequency_words(fused, threshold=0.8)
return fused
```

---

## Why This Design Is Correct

1. **Separates concerns:** Identity (once) from variation (per-image)
2. **Respects computational boundaries:** Heavy VLM only on sample; lightweight VLM on all
3. **Preserves intent:** Final captions still include identity + scene context
4. **Enables caching:** Identity results reusable across datasets / fine-tuning runs
5. **Scales linearly:** Tier 2 dominates runtime; grows with dataset size, not model size
6. **Explainable:** Each tier has clear, auditable outputs
7. **Debuggable:** Failures isolated to specific tier; easy to rerun or skip

---

## Transition & Backwards Compatibility

- Old pipeline: `05_caption.py` (Qwen on all images) — **DEPRECATED**
- New pipeline: `05_identity_inference.py` → `06_variation_captioning.py` → `07_fusion.py`
- Filesystem outputs remain in expected locations (CSV, TXT files)
- Existing training workflows unaffected

---

## Deliverables Summary

✓ 3-tier module separation  
✓ Sampling logic for Tier 1  
✓ Single-stream execution (no parallelization)  
✓ Identity + variation prompts  
✓ Fusion & subtractive cleanup  
✓ Clear phase boundaries  
✓ Scaling rationale documented  
