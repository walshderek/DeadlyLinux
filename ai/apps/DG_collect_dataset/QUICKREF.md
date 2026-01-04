# Quick Reference: Tier-Separated Captioning

## TL;DR

**Old pipeline:** All images → Qwen3-VL (hours of processing)  
**New pipeline:** Sample → Qwen3-VL + All images → LLaVA-7B + Fusion → ~1 hour

## Commands

```bash
cd /home/seanf/deadlygraphics/ai/apps/DG_collect_dataset

# Full pipeline (all 3 tiers)
python DG_collect_dataset_tier.py "Name" --tier-mode

# Individual tiers
python DG_collect_dataset_tier.py "Name" --tier-mode --tier 1
python DG_collect_dataset_tier.py "Name" --tier-mode --tier 2
python DG_collect_dataset_tier.py "Name" --tier-mode --tier 3
```

## What Gets Output

```
outputs/[slug]/
├── 05_identity/           ← TIER 1 (5-10 min)
│   ├── identity.txt       [Master identity description]
│   ├── identity.json      [Structured data]
│   └── ...
├── 06_variations/         ← TIER 2 (30-80 min)
│   ├── variations.csv     [Per-image captions]
│   └── variations_raw/    [Individual files]
└── 07_final_captions/     ← TIER 3 (<1 sec)
    ├── final_captions.csv [Ready for training]
    └── final_captions_raw/[Individual files]
```

## Timing

| Size | Total Time |
|---|---|
| 50 images | 15–20 min |
| 100 images | 20–25 min |
| 500 images | 60–90 min |

## Why It's Fast

1. **Heavy model (Qwen3-VL) on sample only** → constant 5 min
2. **Lightweight model (LLaVA-7B) on all** → linear, fast
3. **Fusion is programmatic** → seconds

## Troubleshooting

| Problem | Solution |
|---|---|
| "Cannot connect to Ollama" | Run `ollama serve` in another terminal |
| "Model not found" | Run `ollama pull qwen3-vl` and `ollama pull llava:7b` |
| Out of memory | Run tiers on different days, or use smaller models |
| Poor identity | Check sampled images in `05_identity/identity_sample_manifest.txt` |

## Files to Review After Each Tier

- **After Tier 1:** `05_identity/identity.txt`
- **After Tier 2:** `06_variations/variations.csv` (first 5 rows)
- **After Tier 3:** `07_final_captions/final_captions.csv` (first 5 rows)

## Documentation

- **Architecture:** `ARCHITECTURE_REFACTOR.md` (design + rationale)
- **Usage guide:** `USAGE_TIER_PIPELINE.md` (detailed, examples)
- **Implementation:** `IMPLEMENTATION_SUMMARY.md` (code overview)
- **This file:** `QUICKREF.md` (quick commands + tips)

## Key Design Principle

> **Identity (permanent) ≠ Variation (per-image)**
> 
> Don't process both through the same expensive model.
> Process identity once (16 images), variations N times (lightweight).

---

See `USAGE_TIER_PIPELINE.md` for full documentation.
