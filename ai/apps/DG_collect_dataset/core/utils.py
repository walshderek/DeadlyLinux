import sys
import os
import subprocess
import re
import json
import random
import csv
import pickle
from datetime import datetime
from pathlib import Path
from typing import Optional

# --- CONFIGURATION ---
# utils.py is in /core/, so parent.parent is the Project Root
ROOT_DIR = Path(__file__).parent.parent 
VENV_PATH = ROOT_DIR / "venv" 

# [FIX] User specified requirements.txt lives inside venv
REQUIREMENTS_PATH = VENV_PATH / "requirements.txt"

LINUX_PROJECTS_ROOT = ROOT_DIR / "outputs"
LINUX_DATASETS_ROOT = ROOT_DIR / "datasets"
DB_PATH = ROOT_DIR / "Database" / "trigger_words.csv"

# --- UNIFIED DIRECTORY SCHEMA (1-7 PIPELINE) ---
DIRS = {
    "scrape": "01_setup_scrape",
    "crop": "02_crop",
    "validate": "03_validate",
    "clean": "04_clean",
    "caption": "05_caption",
    "publish": "06_publish",
    "summary": "07_summary",
}

# Musubi Tuner Paths
MUSUBI_PATHS = {
    'wsl_app': "/home/seanf/ai/apps/musubi-tuner",
    'wsl_models': "/home/seanf/ai/models",
    'win_app': r"C:\AI\apps\musubi-tuner",
    'win_models': r"\\wsl.localhost\Ubuntu\home\seanf\ai\models"
}

# Central Model Store
_llm_path_upper = Path("/mnt/c/AI/models/LLM")
_llm_path_lower = Path("/mnt/c/AI/models/llm")
MODEL_STORE_ROOT = _llm_path_upper if _llm_path_upper.exists() else _llm_path_lower

# Google Sheets Defaults
GOOGLE_SHEET_ID = "1RMWaEiBtSfDZXd1jZ00Fg145faXWqB33ssDiq34ZzXo"
GOOGLE_CLIENT_SECRET = r"C:\AI\apps\ComfyUI Desktop\custom_nodes\comfyui-google-sheets-integration\client_secret.json"
GOOGLE_TOKEN_PATH = r"C:\AI\apps\ComfyUI Desktop\custom_nodes\comfyui-google-sheets-integration\token.pickle"
GOOGLE_KEY_PATH = r"C:\AI\apps\ComfyUI Desktop\custom_nodes\comfyui-google-sheets-integration\encryption_key.key"
GOOGLE_SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

def _normalize_path(path_str: str) -> str:
    """Convert Windows path to WSL mount form when running under Linux."""
    if os.name == "nt":
        return path_str
    if len(path_str) > 1 and path_str[1] == ":" and path_str[0].isalpha():
        drive = path_str[0].lower()
        rest = path_str[2:].replace("\\", "/")
        return f"/mnt/{drive}{rest}"
    return path_str

def install_package(package_name, force=False):
    """Install package(s) via pip."""
    print(f"📦 Installing {'(force) ' if force else ''}missing dependency: {package_name}...")
    try:
        pkgs = package_name.split()
        cmd = [sys.executable, "-m", "pip", "install"]
        if force: cmd.append("--force-reinstall")
        cmd.extend(pkgs)
        subprocess.check_call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(f"✅ Installed {package_name}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install {package_name}. Error: {e}")
        return False

def _check_package_metadata(package_name):
    """Check if package has valid metadata."""
    try:
        from importlib.metadata import version
        version(package_name)
        return True
    except Exception:
        return False

def bootstrap(install_reqs=True):
    if not install_reqs: return
    os.environ['OLLAMA_MODELS'] = str(MODEL_STORE_ROOT)

    # Core dependencies check
    deps_to_check = [
        ("deepface", "deepface tf-keras opencv-python"),
        ("playwright", "playwright"),
        ("huggingface_hub", "huggingface_hub"),
        ("requests", "requests"),
        ("diffusers", "diffusers transformers accelerate scipy"),
        ("qwen_vl_utils", "qwen-vl-utils"),
        ("accelerate", "accelerate"),
        ("insightface", "insightface onnxruntime-gpu"),
    ]
    
    for import_name, pip_name in deps_to_check:
        try:
            __import__(import_name)
        except ImportError:
            install_package(pip_name)

    # Simple Lama check
    try:
        from simple_lama_inpainting import SimpleLama
    except ImportError:
        install_package("simple-lama-inpainting")

    # Playwright browser check
    try:
        import playwright
    except ImportError:
        if install_package("playwright"):
            subprocess.run([sys.executable, "-m", "playwright", "install"], check=False)

    # bitsandbytes metadata check
    try:
        import bitsandbytes
        if not _check_package_metadata("bitsandbytes"):
            raise ImportError("bitsandbytes metadata missing")
    except (ImportError, Exception):
        print("🔧 bitsandbytes issue detected. Reinstalling...")
        install_package("bitsandbytes", force=True)

    # Google API dependencies
    google_deps = [
        ("googleapiclient", "google-api-python-client"),
        ("google.auth", "google-auth google-auth-httplib2 google-auth-oauthlib"),
        ("cryptography", "cryptography"),
    ]
    for import_name, pip_name in google_deps:
        try:
            __import__(import_name)
        except ImportError:
            install_package(pip_name)

    # Download Qwen model if not present
    from huggingface_hub import snapshot_download
    qwen_dir = MODEL_STORE_ROOT / "QWEN" / "Qwen2.5-VL-3B-Instruct"
    if not qwen_dir.exists():
        try:
            qwen_dir.mkdir(parents=True, exist_ok=True)
            snapshot_download(repo_id="Qwen/Qwen2.5-VL-3B-Instruct", local_dir=qwen_dir)
        except: pass

def slugify(text):
    return re.sub(r'[\W]+', '_', text.lower()).strip('_')

def gen_trigger(name):
    parts = name.split()
    first = parts[0].upper()[:2]
    last = parts[-1].upper()[0] if len(parts) > 1 else "X"
    return f"{first}{random.randint(100,999)}{last}"

def obfuscate_trigger(name: str) -> str:
    """Create a leetspeak-ish trigger."""
    subst = {'a': '4', 'b': '8', 'e': '3', 'g': '9', 'i': '1', 'l': '1', 'o': '0', 's': '5', 't': '7', 'z': '2'}
    base = slugify(name).replace('_', '') or "anon"
    obf = ''.join(subst.get(ch, ch) for ch in base)
    import hashlib
    suffix = hashlib.md5(base.encode()).hexdigest()[:4]
    return (obf + suffix).upper()

def log_trigger_to_sheet(name: str, trigger: str):
    """Append trigger/name to Google Sheet."""
    try:
        from googleapiclient.discovery import build
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google.oauth2 import service_account
        from cryptography.fernet import Fernet
    except Exception:
        print("ℹ️ Sheets logging skipped (libs missing).")
        return

    # Normalize Paths
    token_path = Path(_normalize_path(GOOGLE_TOKEN_PATH))
    client_path = Path(_normalize_path(GOOGLE_CLIENT_SECRET))
    key_path = Path(_normalize_path(GOOGLE_KEY_PATH))

    creds = None

    # Method 1: Decrypt Token
    if token_path.exists() and key_path.exists():
        try:
            with open(token_path, "rb") as token, open(key_path, "rb") as kf:
                encrypted = pickle.load(token)
                key = kf.read()
                fernet = Fernet(key)
                decrypted = fernet.decrypt(encrypted)
                creds = pickle.loads(decrypted)
        except Exception: creds = None

    # Method 2: Service Account
    if not creds and client_path.exists():
        try:
            creds = service_account.Credentials.from_service_account_file(str(client_path), scopes=GOOGLE_SCOPES)
        except Exception: creds = None

    if not creds:
        print("ℹ️ Sheets logging skipped (No credentials found).")
        return

    try:
        if getattr(creds, "expired", False) and getattr(creds, "refresh_token", None):
            creds.refresh(Request())
        service = build("sheets", "v4", credentials=creds)
        body = {"values": [[trigger, name, datetime.utcnow().isoformat() + "Z"]]}
        service.spreadsheets().values().append(
            spreadsheetId=GOOGLE_SHEET_ID,
            range="Sheet1!A:C",
            valueInputOption="USER_ENTERED",
            body=body,
        ).execute()
        print(f"✅ Logged to Google Sheet: {trigger} | {name}")
    except Exception as e:
        print(f"ℹ️ Sheets logging failed: {e}")

def get_project_path(slug):
    return LINUX_PROJECTS_ROOT / slug

def load_config(slug):
    path = get_project_path(slug) / "project_config.json"
    if not path.exists(): return None
    with open(path, 'r') as f: return json.load(f)

def save_config(slug, data):
    path = get_project_path(slug) / "project_config.json"
    path.parent.mkdir(parents=True, exist_ok=True) # Critical Fix
    with open(path, 'w') as f: json.dump(data, f, indent=4)

def count_images_for_step(slug, step_num):
    path = get_project_path(slug)
    step_to_dir = {
        1: DIRS['scrape'],
        2: DIRS['crop'],
        3: DIRS['validate'],
        4: DIRS['clean'],
        5: DIRS['caption'],
        6: '06_publish/256',
        7: '07_summary',
    }
    dir_name = step_to_dir.get(step_num)
    if not dir_name: return 0
    
    out_dir = path / dir_name
    if not out_dir.exists(): return 0
    return len([f for f in os.listdir(out_dir) if f.lower().endswith(('.jpg', '.png', '.jpeg', '.webp'))])

def get_windows_unc_path(wsl_path):
    r"""Translates /home/seanf/... to \\wsl.localhost\Ubuntu\home\seanf\..."""
    if not wsl_path.startswith("/home"): return wsl_path 
    clean_path = str(wsl_path).replace("/", "\\")
    if clean_path.startswith("\\"): clean_path = clean_path[1:]
    return f"\\\\wsl.localhost\\Ubuntu\\{clean_path}"

def update_trigger_db(slug, trigger, full_name):
    """Updates the local CSV database of triggers."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    row = [slug, trigger, full_name]
    file_exists = DB_PATH.exists()
    
    try:
        with open(DB_PATH, 'a', newline='') as f:
            writer = csv.writer(f)
            if not file_exists: writer.writerow(["slug", "trigger", "name"])
            writer.writerow(row)
    except Exception as e:
        print(f"⚠️ Failed to update local trigger DB: {e}")