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
# Since this file is in /core/, parent is root, parent.parent is outside the project
# logic: utils.py is in /core/. 
# Path(__file__).parent is /core/
# Path(__file__).parent.parent is /DG_collect_dataset/ (ROOT)
ROOT_DIR = Path(__file__).parent.parent 
VENV_PATH = ROOT_DIR / ".venv"
REQUIREMENTS_PATH = ROOT_DIR / "core" / "requirements.txt"
LINUX_PROJECTS_ROOT = ROOT_DIR / "outputs"
LINUX_DATASETS_ROOT = ROOT_DIR / "datasets"
DB_PATH = ROOT_DIR / "Database" / "trigger_words.csv"

# --- UNIFIED DIRECTORY SCHEMA (1-6 PIPELINE) ---
DIRS = {
    "scrape": "01_scrape",
    "crop": "02_crop",
    "validate": "03_validate",
    "clean": "04_clean",
    "caption": "05_caption",
    "publish": "06_publish",
    "master": "06_publish/1024",
    "downsample": "06_publish",
}

# Musubi Tuner Paths
MUSUBI_PATHS = {
    'wsl_app': "/home/seanf/ai/apps/musubi-tuner",
    'wsl_models': "/home/seanf/ai/models",
    'win_app': r"C:\AI\apps\musubi-tuner",
    'win_models': r"\\wsl.localhost\Ubuntu\home\seanf\ai\models"
}

# Central Model Store
MODEL_STORE_ROOT = Path("/mnt/c/AI/models/LLM")

# Google Sheets logging defaults
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

def install_package(package_name):
    print(f"📦 Installing missing dependency: {package_name}...")
    try:
        pkgs = package_name.split()
        subprocess.check_call([sys.executable, "-m", "pip", "install"] + pkgs)
        print(f"✅ Installed {package_name}")
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install {package_name}. Error: {e}")

def bootstrap(install_reqs=True):
    if not install_reqs: return
    os.environ['OLLAMA_MODELS'] = str(MODEL_STORE_ROOT)

    try: import deepface
    except ImportError: install_package("deepface tf-keras opencv-python")
    try: import playwright
    except ImportError: 
        install_package("playwright")
        subprocess.run([sys.executable, "-m", "playwright", "install"], check=True)
    try: import huggingface_hub
    except ImportError: install_package("huggingface_hub")
    try: import requests
    except ImportError: install_package("requests")
    try: import diffusers
    except ImportError: install_package("diffusers transformers accelerate scipy")
    try: import sklearn
    except ImportError: install_package("scikit-learn")
    try: import qwen_vl_utils
    except ImportError: install_package("qwen-vl-utils")
    try: import bitsandbytes
    except ImportError: install_package("bitsandbytes")
    try: import accelerate
    except ImportError: install_package("accelerate")
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
    """Create a leetspeak-ish trigger unlikely to collide with pretrained names."""
    subst = {
        'a': '4', 'b': '8', 'e': '3', 'g': '9', 'i': '1', 'l': '1', 'o': '0',
        's': '5', 't': '7', 'z': '2'
    }
    base = slugify(name).replace('_', '')
    if not base:
        base = "anon"
    obf = ''.join(subst.get(ch, ch) for ch in base)
    # pad with random digits to reduce collisions
    suffix = str(random.randint(100, 999))
    return (obf + suffix).upper()


def log_trigger_to_sheet(name: str, trigger: str, sheet_id: str = None, sheet_range: str = "Sheet1!A:C", client_secret: str = None, token_file: str = None):
    """Append trigger/name to Google Sheet. Best-effort; silently skips on missing deps/creds."""
    try:
        from googleapiclient.discovery import build
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google.oauth2 import service_account
        from cryptography.fernet import Fernet
    except Exception:
        print("ℹ️ Sheets logging skipped (google API libs not installed).")
        return

    sheet_id = sheet_id or GOOGLE_SHEET_ID
    client_secret = client_secret or GOOGLE_CLIENT_SECRET
    token_file = token_file or GOOGLE_TOKEN_PATH

    token_path = Path(_normalize_path(str(token_file)))
    client_path = Path(_normalize_path(str(client_secret)))
    key_path = Path(_normalize_path(str(GOOGLE_KEY_PATH)))

    creds: Optional[object] = None

    # Try encrypted token pickle first
    if token_path.exists():
        try:
            with open(token_path, "rb") as token:
                encrypted = pickle.load(token)
            if isinstance(encrypted, bytes) and key_path.exists():
                try:
                    with open(key_path, "rb") as kf:
                        key = kf.read()
                    fernet = Fernet(key)
                    decrypted = fernet.decrypt(encrypted)
                    creds = pickle.loads(decrypted)
                except Exception:
                    creds = None
            elif isinstance(encrypted, bytes):
                try:
                    creds = Credentials.from_authorized_user_info(json.loads(encrypted.decode("utf-8")), scopes=GOOGLE_SCOPES)
                except Exception:
                    creds = None
            else:
                creds = encrypted if hasattr(encrypted, "valid") else None
        except Exception:
            creds = None

    # If still no creds, try service account file
    if creds is None and client_path.exists():
        try:
            creds = service_account.Credentials.from_service_account_file(str(client_path), scopes=GOOGLE_SCOPES)
        except Exception:
            creds = None

    if creds is None:
        print("ℹ️ Sheets logging skipped (no usable credentials).")
        return

    try:
        if getattr(creds, "expired", False) and getattr(creds, "refresh_token", None):
            creds.refresh(Request())
        service = build("sheets", "v4", credentials=creds)
        body = {"values": [[trigger, name, datetime.utcnow().isoformat() + "Z"]]}
        service.spreadsheets().values().append(
            spreadsheetId=sheet_id,
            range=sheet_range,
            valueInputOption="USER_ENTERED",
            body=body,
        ).execute()
        print(f"✅ Logged trigger to Google Sheet for {name}")
    except Exception as e:
        print(f"ℹ️ Sheets logging skipped: {e}")

def get_project_path(slug):
    return LINUX_PROJECTS_ROOT / slug

def load_config(slug):
    path = get_project_path(slug) / "project_config.json"
    if not path.exists(): return None
    with open(path, 'r') as f: return json.load(f)

# --- THE FIX IS HERE ---
def save_config(slug, data):
    path = get_project_path(slug) / "project_config.json"
    # Ensure the directory exists before writing!
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w') as f: json.dump(data, f, indent=4)

def get_windows_unc_path(wsl_path):
    if not wsl_path.startswith("/home"): return wsl_path 
    clean_path = str(wsl_path).replace("/", "\\")
    if clean_path.startswith("\\"): clean_path = clean_path[1:]
    return f"\\\\wsl.localhost\\Ubuntu\\{clean_path}"

def update_trigger_db(slug, trigger, full_name):
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    row = [slug, trigger, full_name]
    file_exists = DB_PATH.exists()
    with open(DB_PATH, 'a', newline='') as f:
        writer = csv.writer(f)
        if not file_exists: writer.writerow(["slug", "trigger", "name"])
        writer.writerow(row)