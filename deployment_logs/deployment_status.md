# Deployment Status Report (apps)
Generated on Sun Dec 14 20:25:51 GMT 2025
## 1. Engine Room Check
Python path: /home/seanf/mambaforge/envs/deadlygraphics/bin/python
- Python: 3.11.14
- PyTorch: 2.6.0+cu124 (CUDA: True)
2025-12-14 20:25:54.721267: I tensorflow/core/platform/cpu_feature_guard.cc:210] This TensorFlow binary is optimized to use available CPU instructions in performance-critical operations.
To enable the following instructions: AVX2 FMA, in other operations, rebuild TensorFlow with the appropriate compiler flags.
- TensorFlow: 2.20.0

## 2. Repo Audit (apps)

### Repo: ComfyUI
- requirements.txt: FOUND
- Installing filtered requirements...
- **Install**: SUCCESS (Filtered)
- **Acceleration Check**:
  - xformers: INSTALLED
  - sage-attention: MISSING
- **Runtime import checks**:
WARNING[XFORMERS]: xFormers can't load C++/CUDA extensions. xFormers was built for:
    PyTorch 2.9.1+cu128 with CUDA 1208 (you have 2.6.0+cu124)
    Python  3.10.19 (you have 3.11.14)
  Please reinstall xformers (see https://github.com/facebookresearch/xformers#installing-xformers)
  Memory-efficient attention, SwiGLU, sparse and more won't be available.
  Set XFORMERS_MORE_DETAILS=1 for more details
xformers import_ok
sage-attention import_fail ModuleNotFoundError("No module named 'sage_attention'")
sage-attention import_fail ModuleNotFoundError("No module named 'sage'")

### Repo: DG_collect_dataset
- requirements.txt: MISSING
- **Acceleration Check**:
  - xformers: INSTALLED
  - sage-attention: MISSING
- **Runtime import checks**:
WARNING[XFORMERS]: xFormers can't load C++/CUDA extensions. xFormers was built for:
    PyTorch 2.9.1+cu128 with CUDA 1208 (you have 2.6.0+cu124)
    Python  3.10.19 (you have 3.11.14)
  Please reinstall xformers (see https://github.com/facebookresearch/xformers#installing-xformers)
  Memory-efficient attention, SwiGLU, sparse and more won't be available.
  Set XFORMERS_MORE_DETAILS=1 for more details
xformers import_ok
sage-attention import_fail ModuleNotFoundError("No module named 'sage_attention'")
sage-attention import_fail ModuleNotFoundError("No module named 'sage'")

### Repo: DG_vibecoder
- requirements.txt: MISSING
- **Acceleration Check**:
  - xformers: INSTALLED
  - sage-attention: MISSING
- **Runtime import checks**:
WARNING[XFORMERS]: xFormers can't load C++/CUDA extensions. xFormers was built for:
    PyTorch 2.9.1+cu128 with CUDA 1208 (you have 2.6.0+cu124)
    Python  3.10.19 (you have 3.11.14)
  Please reinstall xformers (see https://github.com/facebookresearch/xformers#installing-xformers)
  Memory-efficient attention, SwiGLU, sparse and more won't be available.
  Set XFORMERS_MORE_DETAILS=1 for more details
xformers import_ok
sage-attention import_fail ModuleNotFoundError("No module named 'sage_attention'")
sage-attention import_fail ModuleNotFoundError("No module named 'sage'")

### Repo: OneTrainer
- requirements.txt: FOUND
- Installing filtered requirements...
- **Install**: FAILED (See /home/seanf/deadlygraphics/ai/apps/OneTrainer/install.log)
- **Acceleration Check**:
  - xformers: INSTALLED
  - sage-attention: MISSING
- **Runtime import checks**:
WARNING[XFORMERS]: xFormers can't load C++/CUDA extensions. xFormers was built for:
    PyTorch 2.9.1+cu128 with CUDA 1208 (you have 2.6.0+cu124)
    Python  3.10.19 (you have 3.11.14)
  Please reinstall xformers (see https://github.com/facebookresearch/xformers#installing-xformers)
  Memory-efficient attention, SwiGLU, sparse and more won't be available.
  Set XFORMERS_MORE_DETAILS=1 for more details
xformers import_ok
sage-attention import_fail ModuleNotFoundError("No module named 'sage_attention'")
sage-attention import_fail ModuleNotFoundError("No module named 'sage'")

### Repo: ai-toolkit
- requirements.txt: FOUND
- Installing filtered requirements...
- **Install**: SUCCESS (Filtered)
- **Acceleration Check**:
  - xformers: INSTALLED
  - sage-attention: MISSING
- **Runtime import checks**:
WARNING[XFORMERS]: xFormers can't load C++/CUDA extensions. xFormers was built for:
    PyTorch 2.9.1+cu128 with CUDA 1208 (you have 2.6.0+cu124)
    Python  3.10.19 (you have 3.11.14)
  Please reinstall xformers (see https://github.com/facebookresearch/xformers#installing-xformers)
  Memory-efficient attention, SwiGLU, sparse and more won't be available.
  Set XFORMERS_MORE_DETAILS=1 for more details
xformers import_ok
sage-attention import_fail ModuleNotFoundError("No module named 'sage_attention'")
sage-attention import_fail ModuleNotFoundError("No module named 'sage'")

### Repo: musubi-tuner
- requirements.txt: MISSING
- **Acceleration Check**:
  - xformers: INSTALLED
  - sage-attention: MISSING
- **Runtime import checks**:
WARNING[XFORMERS]: xFormers can't load C++/CUDA extensions. xFormers was built for:
    PyTorch 2.9.1+cu128 with CUDA 1208 (you have 2.6.0+cu124)
    Python  3.10.19 (you have 3.11.14)
  Please reinstall xformers (see https://github.com/facebookresearch/xformers#installing-xformers)
  Memory-efficient attention, SwiGLU, sparse and more won't be available.
  Set XFORMERS_MORE_DETAILS=1 for more details
xformers import_ok
sage-attention import_fail ModuleNotFoundError("No module named 'sage_attention'")
sage-attention import_fail ModuleNotFoundError("No module named 'sage'")
