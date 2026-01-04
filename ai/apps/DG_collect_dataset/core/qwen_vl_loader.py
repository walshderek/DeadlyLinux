import os
import torch
from transformers import AutoModel, AutoProcessor

def load_qwen_vl_model(qwen_path):
    print(f"✅ DEBUG: Loading {qwen_path}...")
    
    # 1. Check CUDA availability
    cuda_available = torch.cuda.is_available()
    print(f"🔍 CUDA Available: {cuda_available}")
    
    if cuda_available:
        print(f"✅ Loading {qwen_path} on GPU via transformers...")
        try:
            # Load with GPU support using half precision for lower memory
            model = AutoModel.from_pretrained(
                qwen_path,
                torch_dtype=torch.float16,
                trust_remote_code=True,
                device_map="cuda"
            )
            processor = AutoProcessor.from_pretrained(qwen_path, trust_remote_code=True)
            print("✅ Model loaded successfully on GPU")
            return model, processor
        except Exception as e:
            print(f"❌ GPU loading failed: {e}")
            raise
    else:
        print(f"❌ CUDA not available, cannot load model")
        raise RuntimeError("CUDA is not available")
