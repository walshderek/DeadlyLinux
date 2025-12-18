import sys
import os
import subprocess
import torch
import torchvision
import pkg_resources

# Attempt to import AI-specific libraries
try:
    import xformers
    xformers_version = xformers.__version__
except ImportError:
    xformers_version = "not installed or cannot be imported"

try:
    import flash_attn
    flash_attn_version = flash_attn.__version__
except ImportError:
    flash_attn_version = "not installed or cannot be imported"

try:
    import triton
    triton_version = triton.__version__
except ImportError:
    triton_version = "not installed or cannot be imported"

try:
    import sageattention
    sageattention_version = getattr(sageattention, '__version__', "installed but has no __version__ attribute")
except ImportError:
    sageattention_version = "not installed or cannot be imported"

# Python and system info
print("python version:", sys.version)
print("python version info:", sys.version_info)
print("platform:", sys.platform)  # e.g., win32, linux
print("executable path:", sys.executable)  # Path to Python executable

# PyTorch and related
print("torch version:", torch.__version__)
print("cuda version (torch):", torch.version.cuda)
print("torchvision version:", torchvision.__version__)
print("cuda available:", torch.cuda.is_available())
if torch.cuda.is_available():
    print("cuda device count:", torch.cuda.device_count())
    print("cuda devices:", [torch.cuda.get_device_name(i) for i in range(torch.cuda.device_count())])
    print("cuda current device:", torch.cuda.current_device())
    print("torch cuda arch list:", torch.cuda.get_arch_list())  # Supported GPU architectures

# AI library versions
print("xformers version:", xformers_version)
print("flash-attn version:", flash_attn_version)
print("triton version:", triton_version)
print("sageattention version:", sageattention_version)

# Check cl.exe location (Windows-specific)
if sys.platform == "win32":
    cl_path = None
    for path in os.environ.get("PATH", "").split(";"):
        cl_full_path = os.path.join(path.strip(), "cl.exe")
        if os.path.isfile(cl_full_path):
            cl_path = cl_full_path
            break
    print("cl.exe location:", cl_path if cl_path else "not found in PATH")

# CUDA toolkit version (if nvcc is available)
nvcc_path = os.path.join(os.environ.get("CUDA_PATH", "C:\\Program Files\\NVIDIA GPU Computing Toolkit\\CUDA"), "bin", "nvcc.exe") if sys.platform == "win32" else "nvcc"
try:
    nvcc_version = subprocess.check_output([nvcc_path, "--version"], text=True, stderr=subprocess.STDOUT).strip()
    print("nvcc version (CUDA toolkit):", nvcc_version)
except (subprocess.CalledProcessError, FileNotFoundError):
    print("nvcc version (CUDA toolkit): not found or accessible")

# PyTorch build config for troubleshooting
print("torch build config:", torch.__config__.show())

# Run pip check for dependency conflicts
try:
    pip_check = subprocess.check_output([sys.executable, "-m", "pip", "check"], text=True, stderr=subprocess.STDOUT)
    print("pip check result:")
    print(pip_check if pip_check else "No dependency conflicts found")
except subprocess.CalledProcessError as e:
    print("pip check result: Error -", e.output if e.output else "pip check failed")
except FileNotFoundError:
    print("pip check result: pip not found in this environment")

# Additional AI-relevant info
print("pip list (installed packages):")
for dist in pkg_resources.working_set:
    print(f"{dist.project_name}=={dist.version}")