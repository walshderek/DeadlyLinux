import argparse
import sys
import os
import importlib

# --- VENV ACTIVATION ---
def activate_venv():
    venv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".venv", "bin", "activate_this.py")
    if os.environ.get("VIRTUAL_ENV") is None:
        activate_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".venv", "bin", "activate")
        if os.path.exists(activate_script):
            print(f"[INFO] Activating venv: {activate_script}")
            os.execv(activate_script, [activate_script] + sys.argv)

activate_venv()

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
    5: "05_caption",
    6: "06_publish",
    7: "07_summary"
}

def run_pipeline(slug, display_name, trigger, only_step=None):
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
            print(f"❌ Error: --only-step must be a number (1-7).")
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