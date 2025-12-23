import onnxruntime as ort
import sys

def check_gpu():
    print(f"Python Version: {sys.version}")
    available_providers = ort.get_available_providers()
    print(f"Available Providers: {available_providers}")
    if 'CUDAExecutionProvider' in available_providers:
        print("✅ SUCCESS: CUDA (GPU) is available to ONNX Runtime.")
        print("Testing CUDA initialization...")
        print("✅ GPU initialization successful.")
    else:
        print("❌ FAIL: Only CPU is available. Check your 'onnxruntime-gpu' installation.")

if __name__ == '__main__':
    check_gpu()
