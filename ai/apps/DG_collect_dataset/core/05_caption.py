import sys
import os
import re
import torch
import shutil
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from transformers import Qwen2_5_VLForConditionalGeneration, AutoProcessor, BitsAndBytesConfig
from qwen_vl_utils import process_vision_info
from tqdm import tqdm

# --- BOOTSTRAP ---
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)
import utils

# --- CONFIGURATION ---
BATCH_SIZE = 4
QWEN_PATH = "/mnt/c/AI/models/LLM/Qwen2.5-VL-3B-Instruct"

def get_caption_prompt(trigger):
    """
    Instructs the model to describe the image, referring to the person
    by the specific abstract trigger word provided.
    """
    return f"""
Describe this image of {trigger}.
Focus on their clothing, the background, and any actions.
Be concise.
"""

def clean_and_force_trigger(text, trigger):
    """
    Ensures the caption starts with the abstract trigger word.
    """
    # Strip common prefixes
    text = re.sub(r"(?i)^(sure,? here is|the image shows|a photo of|an image of|this is a picture of)\s*", "", text.strip())
    text = text.replace("**", "").replace("*", "").strip(" ,.:")
    
    # FORCE the trigger at the start if missing
    if not text.lower().startswith(trigger.lower()):
        text = f"{trigger}, {text}"
        
    return text

def run(slug):
    config = utils.load_config(slug)
    if not config:
        print(f"❌ Error: Config not found for {slug}")
        return

    # Use the trigger exactly as defined in config (the abstract one)
    trigger = config.get('trigger')
    # Safety: If config is somehow missing it, regen it
    if not trigger or trigger == "Scottington":
        trigger = utils.obfuscate_trigger(config.get('name', slug))

    path = utils.get_project_path(slug)
    in_dir = path / utils.DIRS.get('clean', '04_clean')
    out_dir = path / utils.DIRS.get('caption', '05_caption')
    out_dir.mkdir(parents=True, exist_ok=True)
    
    if not os.path.exists(QWEN_PATH):
        print(f"❌ Error: Model not found at {QWEN_PATH}")
        return

    print(f"📝 [05_caption] Batch Engine (Batch: {BATCH_SIZE})")
    print(f"   -> Using Abstract Trigger: '{trigger}'")

    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_compute_dtype=torch.float16,
        bnb_4bit_quant_type="nf4"
    )

    try:
        model = Qwen2_5_VLForConditionalGeneration.from_pretrained(
            QWEN_PATH, quantization_config=bnb_config, device_map="auto"
        )
        processor = AutoProcessor.from_pretrained(QWEN_PATH)
    except Exception as e:
        print(f"❌ Error loading model: {e}")
        return

    files = sorted([f for f in os.listdir(in_dir) if f.lower().endswith(('.jpg', '.png', '.jpeg'))])
    
    # Batches
    batches = [files[i:i + BATCH_SIZE] for i in range(0, len(files), BATCH_SIZE)]
    print(f"   -> Processing {len(files)} images in {len(batches)} batches...")

    io_executor = ThreadPoolExecutor(max_workers=4)

    for batch_files in tqdm(batches, desc="Batch Inference"):
        batch_messages = []
        
        # Prepare Batch
        for f in batch_files:
            img_path = in_dir / f
            messages = [{
                "role": "user", 
                "content": [
                    {"type": "image", "image": str(img_path), "max_pixels": 768*768}, 
                    {"type": "text", "text": get_caption_prompt(trigger)}
                ]
            }]
            batch_messages.append(messages)

        # Tokenize & Generate
        texts = [processor.apply_chat_template(msg, tokenize=False, add_generation_prompt=True) for msg in batch_messages]
        image_inputs_list = []
        for msg in batch_messages:
            imgs, _ = process_vision_info(msg)
            image_inputs_list.extend(imgs)

        inputs = processor(
            text=texts,
            images=image_inputs_list,
            padding=True,
            return_tensors="pt"
        ).to(model.device)

        generated_ids = model.generate(**inputs, max_new_tokens=96)
        
        generated_ids_trimmed = [
            out_ids[len(in_ids):] for in_ids, out_ids in zip(inputs.input_ids, generated_ids)
        ]
        output_texts = processor.batch_decode(generated_ids_trimmed, skip_special_tokens=True)

        # Save
        for i, raw_text in enumerate(output_texts):
            filename = batch_files[i]
            final_caption = clean_and_force_trigger(raw_text, trigger)
            
            src_img = in_dir / filename
            dst_img = out_dir / filename
            dst_txt = out_dir / (os.path.splitext(filename)[0] + ".txt")
            
            io_executor.submit(shutil.copy2, src_img, dst_img)
            
            def write_txt(p, c):
                with open(p, "w", encoding="utf-8") as f: f.write(c)
            io_executor.submit(write_txt, dst_txt, final_caption)

    io_executor.shutdown(wait=True)
    print(f"✅ Success. Captions saved to: {out_dir}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        run(sys.argv[1])