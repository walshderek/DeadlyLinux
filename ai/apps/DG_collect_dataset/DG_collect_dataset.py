"""
TIER-SEPARATED CAPTIONING PIPELINE ORCHESTRATOR

New pipeline structure (replaces old 05_caption.py + 06_caption.py):

Tier-1: 05_identity_inference.py
  Input: All images from 04_clean
  Sample: ~16 representative images
  Model: Qwen3-VL-8B (heavy VLM)
  Output: identity.json, identity.txt
  Duration: ~5-10 minutes

Tier-2: 06_variation_captioning.py
  Input: All images from 04_clean
  Model: LLaVA-7B or BLIP (lightweight)
  Output: variations.csv, variations_raw/*.txt
  Duration: ~30-60 minutes for 500 images

Tier-3: 07_fusion.py
  Input: Identity (Tier-1) + Variations (Tier-2)
  Processing: Programmatic merge + deduplication
  Output: final_captions.csv, final_captions_raw/*.txt
  Duration: Seconds
"""

import argparse
import sys
import os
import importlib

# --- BOOTSTRAP ---
current_dir = os.path.dirname(os.path.abspath(__file__))
core_dir = os.path.join(current_dir, "core")
if core_dir not in sys.path:
    sys.path.append(core_dir)

import utils

# New tier-separated pipeline
TIER_PIPELINE = {
    1: "identity_inference",      # Heavy VLM on sample
    2: "variation_captioning",    # Lightweight VLM on all
    3: "fusion"                   # Programmatic merge
}

# Original pipeline (for backwards compatibility)
LEGACY_STEPS = {
    1: "01_setup_scrape",
    2: "02_crop",
    3: "03_validate",
    4: "04_clean",
    5: "05_resize",
    6: "06_caption",  # Old monolithic caption step (DEPRECATED)
    7: "07_publish",
    8: "08_summary"
}


def run_tier_pipeline(slug, display_name, trigger, tier_only=None):
    """
    Run new tier-separated captioning pipeline.
    
    Args:
        slug: Project slug
        display_name: Human-readable name
        trigger: Trigger word
        tier_only: Run only specific tier (1, 2, or 3)
    """
    print("\n" + "="*70)
    print("🎯 TIER-SEPARATED CAPTIONING PIPELINE")
    print("="*70)
    print(f"📊 Project: {display_name}")
    print(f"🔑 Trigger: {trigger}")
    print("="*70 + "\n")
    
    # Save config
    utils.save_config(slug, {
        'slug': slug,
        'name': display_name,
        'trigger': trigger
    })
    
    # Determine which tiers to run
    if tier_only:
        try:
            tier_nums = [int(tier_only)]
            if tier_nums[0] not in TIER_PIPELINE:
                print(f"❌ Error: Tier must be 1, 2, or 3 (not {tier_nums[0]})")
                return
        except ValueError:
            print(f"❌ Error: --tier must be a number (1, 2, or 3)")
            return
    else:
        tier_nums = sorted(TIER_PIPELINE.keys())
    
    # Run tiers in sequence
    for tier_num in tier_nums:
        module_name = TIER_PIPELINE.get(tier_num)
        if not os.path.exists(os.path.join(core_dir, module_name + ".py")):
            print(f"❌ Module not found: {module_name}.py")
            continue
        
        print(f"\n{'='*70}")
        print(f"🚀 Running TIER {tier_num}: {module_name}")
        print(f"{'='*70}\n")
        
        try:
            module = importlib.import_module(module_name)
            if hasattr(module, 'run'):
                module.run(slug)
            else:
                print(f"❌ Error: {module_name} missing 'run(slug)' function.")
        except Exception as e:
            print(f"\n❌ CRITICAL ERROR in Tier {tier_num} ({module_name}): {e}")
            import traceback
            traceback.print_exc()
            print(f"\n💡 Troubleshooting:")
            print(f"   - Check Ollama is running: ollama serve")
            print(f"   - Check models are available: ollama list")
            print(f"   - Check input directory: {utils.get_project_path(slug) / '04_clean'}")
            return
    
    print(f"\n" + "="*70)
    print("✅ TIER-SEPARATED PIPELINE COMPLETE")
    print("="*70)
    print(f"📊 Project: {display_name}")
    print(f"📁 Output directory: {utils.get_project_path(slug) / '06_caption'}")
    print(f"📄 Final captions: final_captions.csv")
    print("\n💡 Next steps:")
    print(f"   1. Review captions: {utils.get_project_path(slug) / 'final_captions.csv'}")
    print(f"   2. Run publishing/training pipeline")


def run_legacy_pipeline(slug, display_name, trigger, only_step=None):
    """
    Run legacy pipeline (old monolithic steps 1-8).
    DEPRECATED: Use run_tier_pipeline instead for captioning.
    """
    print(f"\n{'='*70}")
    print(f"⚠️  LEGACY PIPELINE (steps 1-8)")
    print(f"{'='*70}")
    print(f"📊 Project: {display_name}")
    print(f"🔑 Trigger: {trigger}")
    print(f"{'='*70}\n")
    
    # Save config
    utils.save_config(slug, {
        'slug': slug,
        'name': display_name,
        'trigger': trigger
    })
    
    if only_step:
        try:
            step_nums = [int(only_step)]
        except ValueError:
            print(f"❌ Error: --only-step must be a number (1-8).")
            return
    else:
        step_nums = sorted(LEGACY_STEPS.keys())
    
    for step_num in step_nums:
        module_name = LEGACY_STEPS.get(step_num)
        if not os.path.exists(os.path.join(core_dir, module_name + ".py")):
            continue
        
        print(f"\n--> [{module_name}] Running Step {step_num}...")
        try:
            module = importlib.import_module(module_name)
            if hasattr(module, 'run'):
                module.run(slug)
            else:
                print(f"❌ Error: {module_name} missing 'run(slug)' function.")
        except Exception as e:
            print(f"❌ CRITICAL ERROR in {module_name}: {e}")
            import traceback
            traceback.print_exc()
            break
    
    print(f"\n✅ Legacy pipeline finished for {slug}")


def main():
    parser = argparse.ArgumentParser(
        description="DeadlyGraphics Data Processing Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
TIER-SEPARATED CAPTIONING (Recommended):
  python DG_collect_dataset.py "Name" --tier-mode
  python DG_collect_dataset.py "Name" --tier-mode --tier 1
  python DG_collect_dataset.py "Name" --tier-mode --tier 2
  python DG_collect_dataset.py "Name" --tier-mode --tier 3

LEGACY PIPELINE (steps 1-8):
  python DG_collect_dataset.py "Name"
  python DG_collect_dataset.py "Name" --only-step 5

Note: For captioning, use --tier-mode (new) instead of legacy steps 5-6.
        """
    )
    parser.add_argument("name", help="Name of the person (e.g. 'Theresa May')")
    parser.add_argument("--trigger", default=None, help="Trigger word (defaults to obfuscated ID)")
    parser.add_argument("--tier-mode", action="store_true", 
                       help="Run tier-separated captioning pipeline (recommended)")
    parser.add_argument("--tier", type=int, help="Run only specific tier (1, 2, or 3)")
    parser.add_argument("--only-step", type=int, help="Legacy: Run only specific step (1-8)")
    
    args = parser.parse_args()
    
    raw_name = args.name
    slug = raw_name.lower().replace(" ", "_").replace("-", "_")
    display_name = raw_name.replace("_", " ").title()
    
    # --- TRIGGER LOGIC ---
    if args.trigger and args.trigger != "Scottington":
        trigger = args.trigger
    else:
        existing_cfg = utils.load_config(slug)
        if existing_cfg and 'trigger' in existing_cfg and existing_cfg['trigger'] != "Scottington":
            trigger = existing_cfg['trigger']
        else:
            trigger = utils.obfuscate_trigger(raw_name)
    
    # --- PIPELINE SELECTION ---
    if args.tier_mode or args.tier:
        # New tier-separated pipeline
        run_tier_pipeline(slug, display_name, trigger, args.tier)
    else:
        # Legacy pipeline (backwards compatibility)
        run_legacy_pipeline(slug, display_name, trigger, args.only_step)


if __name__ == "__main__":
    main()
