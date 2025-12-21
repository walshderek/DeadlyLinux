# DG_collect_dataset Modernization (December 2025)

## Summary
This pipeline has been modernized for long-term maintainability and compatibility with current ML tools. All face detection, validation, and embedding now use `insightface` (replacing DeepFace/retinaface). The environment is fully reproducible in WSL with Python 3.10.0 and a single requirements.txt.

## Key Changes
- Python 3.10.0 rebuilt in WSL with all system libraries (fixes C extension issues)
- All DeepFace/retinaface code removed; replaced with insightface
- requirements.txt updated for modern CUDA, torch, and insightface stack
- onnxruntime and onnxruntime-gpu added for ONNX model support
- All pipeline scripts (02_crop.py, 03_validate.py, 06_qc.py) refactored for insightface

## Why insightface?
- Faster, more accurate, and actively maintained
- Compatible with modern CUDA, ONNX, and Python
- Ensures future-proofing and easier upgrades

## How to Reproduce
1. Ensure WSL has Python 3.10.0 built with all system headers (see CHANGELOG.md)
2. Create a new venv: `python3.10 -m venv venv && source venv/bin/activate`
3. Install dependencies: `pip install --upgrade pip && pip install -r requirements.txt`
4. Run pipeline scripts as usual

See CHANGELOG.md for full details and rationale.
