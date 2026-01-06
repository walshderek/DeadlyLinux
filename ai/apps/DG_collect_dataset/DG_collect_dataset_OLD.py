import argparse
import sys
import os
import importlib
from pathlib import Path

# --- BOOTSTRAP ---
current_dir = os.path.dirname(os.path.abspath(__file__))
core_dir = os.path.join(current_dir, "core")
if core_dir not in sys.path:
    sys.path.append(core_dir)

import utils

STEPS = {
    1: "01_setup_scrape",
    2: "02_crop",
    3: "03_validate",
    4: "04_clean",
    5: "05_resize",
    6: "06_caption",
    7: "07_publish",
    8: "08_summary"
}

STEP_OUTPUT_DIRS = {
    1: "01_setup_scrape",
    2: "02_crop",
    3: "03_validate",
    4: "04_clean",
    5: "05_resize",
    6: "06_caption",
    7: "07_publish",
    8: "08_summary"
}

def is_step_complete(slug, step_num):
    """Check if a step has already been completed."""
    try:
        project_path = utils.get_project_path(slug)
        step_dir_name = STEP_OUTPUT_DIRS.get(step_num)
        if not step_dir_name:
            return False
        
        step_dir = project_path / step_dir_name
        
        # Step is complete if the directory exists and is non-empty
        if step_dir.exists() and any(step_dir.iterdir()):
            return True
        return False
    except Exception:
        return False

def get_first_incomplete_step(slug):
    """Find the first step that hasn't been completed yet."""
    for step_num in sorted(STEPS.keys()):
        if not is_step_complete(slug, step_num):
            return step_num
    return None  # All steps complete

def run_pipeline(slug, display_name, trigger, only_step=None, resume=True):
    print(f"==========================================")
    print(f"🚀 PIPELINE START: {display_name}")
    print(f"🔑 Trigger Identity: {trigger}")
    print(f"==========================================\n")
    
    # Save the abstract trigger to config
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
        # Auto-resume: start from first incomplete step
        if resume:
            first_incomplete = get_first_incomplete_step(slug)
            if first_incomplete is not None:
                step_nums = sorted([s for s in STEPS.keys() if s >= first_incomplete])
                print(f"📍 Resuming from Step {first_incomplete} ({STEPS[first_incomplete]})\n")
            else:
                print(f"✅ All steps already complete. Skipping pipeline.\n")
                return
        else:
            step_nums = sorted(STEPS.keys())

    for step_num in step_nums:
        module_name = STEPS.get(step_num)
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
            print(f"\n🔄 On next run, pipeline will resume from Step {step_num}.")
            break

    print(f"\n✅ Sequence finished for {slug}")

def main():
    parser = argparse.ArgumentParser(description="DeadlyGraphics Wan 2.2 Pipeline")
    parser.add_argument("name", help="Name of the person (e.g. 'Theresa May')")
    parser.add_argument("--trigger", default=None, help="Trigger word (Defaults to Obfuscated ID)")
    parser.add_argument("--only-step", help="Run only a specific step number (1-7)")

    args = parser.parse_args()
    
    raw_name = args.name
    slug = raw_name.lower().replace(" ", "_").replace("-", "_")
    display_name = raw_name.replace("_", " ").title()

    # --- TRIGGER LOGIC ---
    # 1. CLI Override
    if args.trigger and args.trigger != "Scottington":
        trigger = args.trigger
    else:
        # 2. Check Existing Config
        existing_cfg = utils.load_config(slug)
        if existing_cfg and 'trigger' in existing_cfg and existing_cfg['trigger'] != "Scottington":
            trigger = existing_cfg['trigger']
        else:
            # 3. Generate Abstract Trigger (e.g., "PR1NC3H4RR")
            # Uses the utils helper to ensure consistency
            trigger = utils.obfuscate_trigger(raw_name)

    run_pipeline(slug, display_name, trigger, args.only_step)

if __name__ == "__main__":
    main()