import sys
import os
import re
import torch
import csv
import shutil
from pathlib import Path
from transformers import Qwen2_5_VLForConditionalGeneration, AutoProcessor, BitsAndBytesConfig
from qwen_vl_utils import process_vision_info
from tqdm import tqdm
import utils

def get_whisper_prompt(trigger, real_name):
    """Pass 1: Environmental description only."""
    return f"""
Analyze this photo of {real_name} (trigger: {trigger}).
Ground rules:
- Start with the word "{trigger}".
- Describe only clothing, pose, background, setting, and camera angle.
- DO NOT describe the subject's face, eyes, hair, or skin.
- Format: One concise sentence.
"""

def get_photofit_prompt(trigger):
    """Pass 2: Identity 'Inversese' (Clinical Physical Profiling)."""
    return f"""
Analyze subject "{trigger}". Provide a physical description of ONLY the person.
Include: haircut/thickness, facial expression, estimated age, skin tone, build, and eye shape.
Note if they are wearing glasses or jewelry.
Format: Single objective paragraph.
"""

def clean_caption(text, trigger):
    text = re.sub(r"(?i)^(the image features|photo of|an image of)\s*", "", text.strip())
    text = text.replace("**", "").replace("*", "").strip(" ,.:")
    if not text.lower().startswith(trigger.lower()):
        text = f"{trigger}, {text}"
    return text

def run(slug):
    config = utils.load_config(slug)
    trigger = config.get('trigger', 'Scottington')
    real_name = config.get('name', slug)
    path = utils.get_project_path(slug)
    
    in_dir = path / "04_clean"
    out_dir = path / "05_caption"
    char_dir = path / "characterDesc"
    out_dir.mkdir(parents=True, exist_ok=True)
    char_dir.mkdir(parents=True, exist_ok=True)

    print(f"📝 [05_caption] GPU Dual-Pass Engine for: {real_name}")
    qwen_path = "/mnt/c/AI/models/LLM/Qwen2.5-VL-3B-Instruct"

    # RTX 4080 SUPER Optimization
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_compute_dtype=torch.float16,
        bnb_4bit_quant_type="nf4"
    )

    model = Qwen2_5_VLForConditionalGeneration.from_pretrained(
        qwen_path, quantization_config=bnb_config, device_map="auto"
    )
    processor = AutoProcessor.from_pretrained(qwen_path)

    files = sorted([f for f in os.listdir(in_dir) if f.lower().endswith(('.jpg', '.png'))])
    photofit_logs = []

    def quick_infer(img_path, instruction):
        messages = [{"role": "user", "content": [{"type": "image", "image": str(img_path), "max_pixels": 768*768}, {"type": "text", "text": instruction}]}]
        text_input = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        image_inputs, _ = process_vision_info(messages)
        inputs = processor(text=[text_input], images=image_inputs, padding=True, return_tensors="pt").to(model.device)
        generated_ids = model.generate(**inputs, max_new_tokens=128)
        return processor.batch_decode(generated_ids[:, inputs.input_ids.shape[1]:], skip_special_tokens=True)[0].strip()

    for f in tqdm(files, desc="Processing Identity"):
        # Copy image for caption folder
        shutil.copy2(in_dir / f, out_dir / f)
        
        # Pass 1: Whisper (Env/Action)
        env_cap = clean_caption(quick_infer(in_dir/f, get_whisper_prompt(trigger, real_name)), trigger)
        with open(out_dir / (os.path.splitext(f)[0] + ".txt"), "w", encoding="utf-8") as tf:
            tf.write(env_cap)
        
        # Pass 2: Photofit (Physical Traits)
        trait_desc = quick_infer(in_dir/f, get_photofit_prompt(trigger))
        photofit_logs.append({"image": f, "description": trait_desc})

    # --- STATISTICAL CONSENSUS ---
    print("🔄 Generating Master Photofit consensus...")
    csv_path = char_dir / f"{slug}_desc.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["image", "description"])
        writer.writeheader()
        writer.writerows(photofit_logs)

    all_desc = "\n".join([d['description'] for d in photofit_logs])
    summary_prompt = f"Analyze these {len(photofit_logs)} descriptions of {trigger}. Create a clinical 'Master Photofit' consensus paragraph (~200 words). If glasses appear in >50% of reports, include them:\n{all_desc}"
    
    sum_msg = [{"role": "user", "content": [{"type": "text", "text": summary_prompt}]}]
    inputs = processor(text=[processor.apply_chat_template(sum_msg, tokenize=False, add_generation_prompt=True)], return_tensors="pt").to(model.device)
    gen_ids = model.generate(**inputs, max_new_tokens=400)
    master_photofit = processor.batch_decode(gen_ids[:, inputs.input_ids.shape[1]:], skip_special_tokens=True)[0].strip()

    with open(char_dir / f"{slug}_desc.txt", "w") as f: f.write(master_photofit)
    print(f"✅ Success. Master Photofit saved to: {char_dir}")

if __name__ == "__main__":
    if len(sys.argv) > 1: run(sys.argv[1])