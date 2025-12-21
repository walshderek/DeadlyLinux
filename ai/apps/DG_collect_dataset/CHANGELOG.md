# Changelog for DG_collect_dataset Modernization (December 2025)

## Major Changes

### 1. Python Environment Fix (WSL)
- Rebuilt Python 3.10.0 from source in WSL with all required system libraries and headers.
- Restored support for C extensions (notably _ctypes), unblocking all scientific/ML packages.
- Recreated the DG_collect_dataset virtual environment using the fixed Python 3.10.0.

### 2. Dependency Modernization
- Updated requirements.txt to remove DeepFace and retinaface (and all TensorFlow 1.x dependencies).
- Switched to `insightface` for all face detection, validation, and embedding tasks.
- Added onnxruntime and onnxruntime-gpu as required by insightface.
- Ensured all dependencies are compatible with CUDA 12.4, torch 2.5.1+cu124, torchvision 0.20.1+cu124, xformers 0.0.28.post3, and triton 3.1.0.

### 3. Pipeline Refactor
- Refactored core/02_crop.py, core/03_validate.py, and core/06_qc.py to use insightface for all face-related operations.
- Removed all DeepFace/retinaface code paths.
- All code paths now use insightface for detection, validation, and embedding.

### 4. Reproducibility & Documentation
- All fixes and reasons for changes are documented here for future reference.
- The environment is now fully reproducible in WSL with a single requirements.txt and venv.

## Rationale for Switching to insightface
- DeepFace and retinaface are no longer actively maintained and have major compatibility issues with modern Python and CUDA stacks.
- insightface is actively maintained, faster, and more accurate, and supports modern ONNX/CUDA workflows.
- This switch ensures long-term maintainability and compatibility with current and future ML pipelines.

---

For any issues or further modernization, see DEPLOYMENT_DOCS.md or contact the maintainers.
