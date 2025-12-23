import argparse
import sys
import os
import importlib

# --- BOOTSTRAP: Add 'core' to path ---
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
    5: "05_caption",    
    6: "06_publish",
    7: "07_summary"     
}

def run_pipeline(slug, display_name, trigger, model, only_step=None):
    print(f"🚀 Pipeline Started: {slug}")
    print(f"🔑 Trigger Word: {trigger}")
    
    utils.save_config(slug, {
        'slug': slug,
        'name': display_name,
        'trigger': trigger,
        'model': model
    })

    if only_step:
        try:
            step_nums = [int(only_step)]
        except ValueError:
            print(f"❌ Error: --only-step must be a number (1-7).")
            return
    else:
        step_nums = sorted(STEPS.keys())

    for step_num in step_nums:
        module_name = STEPS.get(step_num)
        
        # Check inside core/
        if not os.path.exists(os.path.join(core_dir, module_name + ".py")):
            print(f"⚠️  Skipping {module_name} (File not found)")
            continue

        print(f"\n--> [{module_name}] Running Step {step_num}...")
        try:
            module = importlib.import_module(module_name)
            if hasattr(module, 'run'):
                module.run(slug)
            else:
                print(f"❌ Error: {module_name} missing 'run(slug)' function.")
        except Exception as e:
            print(f"❌ Error executing {module_name}: {e}")
            import traceback
            traceback.print_exc()
            break

    print(f"\n✅ Pipeline sequence finished for {slug}")

def main():
    parser = argparse.ArgumentParser(description="DeadlyGraphics Dataset Pipeline")
    parser.add_argument("name", help="Name of the person (e.g. 'Ed Milliband')")
    parser.add_argument("--trigger", default=None, help="Trigger word (defaults to obscured name)")
    parser.add_argument("--only-step", help="Run only a specific step number (1-7)")
    parser.add_argument("--model", default="qwen-vl", help="Model for captioning")
    # Legacy args ignored
    parser.add_argument("--limit", default=None, help="Ignored")
    parser.add_argument("--count", default=None, help="Ignored")
    parser.add_argument("--gender", default=None, help="Ignored")

    args = parser.parse_args()
    
    raw_name = args.name
    slug = raw_name.lower().replace(" ", "_").replace("-", "_")
    display_name = raw_name.replace("_", " ").title()

    existing_cfg = utils.load_config(slug)
    if args.trigger:
        trigger = args.trigger
    elif existing_cfg and 'trigger' in existing_cfg:
        trigger = existing_cfg['trigger']
    else:
        trigger = utils.obfuscate_trigger(display_name)

    run_pipeline(slug, display_name, trigger, args.model, args.only_step)

if __name__ == "__main__":
    main()