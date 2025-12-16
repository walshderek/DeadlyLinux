import sys
import os
import time
import torch
import re
import importlib
from pathlib import Path

# --- BOOTSTRAP PATHS ---
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)
import utils

# Force localhost for WSL
OLLAMA_HOST = "http://127.0.0.1:11434"
os.environ["OLLAMA_HOST"] = OLLAMA_HOST
os.environ["OLLAMA_MODELS"] = str(utils.MODEL_STORE_ROOT)

def get_system_instruction(trigger, real_name):
    return f"""
You are captioning images for fine-tuning. The subject's secret trigger is "{trigger}" which refers to {real_name}.

Ground rules:
- START the caption with "{trigger}".
- DO NOT describe the subject's intrinsic appearance (face, head shape, skin tone, hair, eyes, age, build, lips, nose, ears, cheeks, jaw).
- Focus on everything else: clothing, accessories, pose, hands, body orientation, background, setting, props, lighting, camera angle, depth of field, mood.
- No Markdown or lists; single concise sentence(s).
- Avoid phrases like "photo of" or "image of".

Examples of allowed details: "{trigger} wearing a navy suit and red tie, standing at a podium with blurred flags behind, rim-lit from stage lights, shot at medium close-up, f/2.8 shallow depth of field."
"""

def clean_caption(text, trigger):
    # 1. Kill the specific bad phrases if Qwen ignores us
    text = re.sub(r"(?i)^(the image features|the image shows|a photo of|an image of)\s*", "", text.strip())
    # 2. Remove Markdown bolding/italics
    text = text.replace("**", "").replace("*", "")
    # 3. Clean whitespace
    text = text.strip(" ,.:")
    # 4. Ensure it starts with trigger
    if not text.lower().startswith(trigger.lower()):
        text = f"{trigger}, {text}"
    return text

def run(slug):
    config = utils.load_config(slug)
    if not config: return
    
    trigger = config['trigger']
    model = config.get('model', 'qwen-vl')
    real_name = config.get('name', slug)
    gender_str = 'person'

    path = utils.get_project_path(slug)
    
    # --- PAPER TRAIL ARCHITECTURE (Section XIX) ---
    # INPUT:  04_clean (cleaned images, no captions)
    # OUTPUT: 05_caption (images COPIED here + .txt captions generated)
    
    in_dir = path / utils.DIRS.get('clean', '04_clean')
    
    if not in_dir.exists():
        print(f"⚠️ '{in_dir.name}' not found. Checking validation folder...")
        in_dir = path / utils.DIRS.get('validate', '03_validate')
    
    if not in_dir.exists():
        print(f"❌ Error: No input images found in {path}")
        return

    # Create output directory for captioned images (05_caption)
    out_dir = path / utils.DIRS.get('caption', '05_caption')
    out_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"📝 [05_caption] Paper Trail Architecture")
    print(f"   INPUT:  {in_dir}")
    print(f"   OUTPUT: {out_dir}")
    
    # Qwen Setup (4-bit Turbo)
    if model == "qwen-vl":
        try:
            print("⏳ Loading Qwen2.5-VL...")
            from transformers import Qwen2_5_VLForConditionalGeneration, AutoProcessor, BitsAndBytesConfig
            
            qwen_path = utils.MODEL_STORE_ROOT / "QWEN" / "Qwen2.5-VL-3B-Instruct"
            
            bnb_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_compute_dtype=torch.float16,
                bnb_4bit_quant_type="nf4"
            )
            
            qwen_model_obj = Qwen2_5_VLForConditionalGeneration.from_pretrained(
                str(qwen_path),
                quantization_config=bnb_config,
                device_map="auto",
            )
            qwen_processor = AutoProcessor.from_pretrained(str(qwen_path))
        except Exception as e:
            print(f"❌ Failed to load Qwen: {e}")
            return
    else:
        # Fallback setup if needed
        pass

    files = sorted([f for f in os.listdir(in_dir) if f.lower().endswith(('.jpg', '.png'))])
    system_instruction = get_system_instruction(trigger, real_name)
    
    print(f"   Found {len(files)} images to process...")

    for i, f in enumerate(files, 1):
        # Output paths in 05_caption folder
        out_img_path = out_dir / f
        txt_path = out_dir / (os.path.splitext(f)[0] + ".txt")
        
        # Skip if already captioned
        if txt_path.exists() and out_img_path.exists(): 
            print(f"   [{i}/{len(files)}] {f}... (skipped, already done)")
            continue
        
        print(f"   [{i}/{len(files)}] {f}...", end="", flush=True)
        
        try:
            # Copy image to output folder first
            import shutil
            if not out_img_path.exists():
                shutil.copy2(in_dir / f, out_img_path)
            
            # Inference Logic
            if model == "qwen-vl":
                from qwen_vl_utils import process_vision_info
                
                messages = [
                    {
                        "role": "user",
                        "content": [
                            {"type": "image", "image": str(in_dir/f), "max_pixels": 768*768},
                            {"type": "text", "text": system_instruction},
                        ],
                    }
                ]
                
                text_input = qwen_processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
                image_inputs, video_inputs = process_vision_info(messages)
                
                inputs = qwen_processor(
                    text=[text_input],
                    images=image_inputs,
                    videos=video_inputs,
                    padding=True,
                    return_tensors="pt",
                ).to(qwen_model_obj.device)

                generated_ids = qwen_model_obj.generate(**inputs, max_new_tokens=256)
                
                generated_ids_trimmed = [
                    out_ids[len(in_ids) :] for in_ids, out_ids in zip(inputs.input_ids, generated_ids)
                ]
                caption = qwen_processor.batch_decode(
                    generated_ids_trimmed, skip_special_tokens=True, clean_up_tokenization_spaces=False
                )[0]
                
            else:
                caption = f"{trigger}, a {gender_str}."

            caption = clean_caption(caption, trigger)
            with open(txt_path, "w", encoding="utf-8") as tf: tf.write(caption)
            print(" Done.")
            
        except Exception as e:
            print(f" Error: {e}")

    print("✅ Captioning complete.")