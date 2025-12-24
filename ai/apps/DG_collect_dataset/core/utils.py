# core/utils.py
import sys
import os
import subprocess
import re
import json
import random
import csv
import pickle
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Optional

# --- CORE PATH DISCOVERY ---
# Path logic: utils.py is in /core/. ROOT is one level up.
ROOT_DIR = Path(__file__).resolve().parent.parent 
VENV_PATH = ROOT_DIR / ".venv"
REQUIREMENTS_PATH = ROOT_DIR / "core" / "requirements.txt"
LINUX_PROJECTS_ROOT = ROOT_DIR / "outputs"
LINUX_DATASETS_ROOT = ROOT_DIR / "datasets"
DB_PATH = ROOT_DIR / "Database" / "trigger_words.csv"

# --- UNIFIED DIRECTORY SCHEMA ---
DIRS = {
    "scrape": "01_setup_scrape",
    "crop": "02_crop",
    "validate": "03_validate",
    "clean": "04_clean",
    "caption": "05_caption",
    "publish": "06_publish",
    "summary": "07_summary"
}

# --- MUSUBI PATH CONFIGURATION ---
# WSL finds models at /mnt/c/AI/models/
MODEL_STORE_ROOT = Path("/mnt/c/AI/models")

MUSUBI_PATHS = {
    'wsl_app': "/home/seanf/ai/apps/musubi-tuner",
    'wsl_models': "/home/seanf/ai/models",
    'win_app': r"C:\AI\apps\musubi-tuner",
    'win_models': r"C:\AI\models"
}

# Google Sheets logging defaults
GOOGLE_SHEET_ID = "1RMWaEiBtSfDZXd1jZ00Fg145faXWqB33ssDiq34ZzXo"
GOOGLE_CLIENT_SECRET = r"C:\AI\apps\ComfyUI Desktop\custom_nodes\comfyui-google-sheets-integration\client_secret.json"
GOOGLE_TOKEN_PATH = r"C:\AI\apps\ComfyUI Desktop\custom_nodes\comfyui-google-sheets-integration\token.pickle"
GOOGLE_KEY_PATH = r"C:\AI\apps\ComfyUI Desktop\custom_nodes\comfyui-google-sheets-integration\encryption_key.key"
GOOGLE_SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

# --- CORE UTILITIES ---

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
    out_dir = path / step_to_dir.get(step_num, '')
    if not out_dir.exists(): return 0
    return len([f for f in os.listdir(out_dir) if f.lower().endswith(('.jpg', '.png', '.jpeg', '.webp'))])

def _normalize_path(path_str: str) -> str:
    """Convert Windows path to WSL mount form."""
    if os.name == "nt": return path_str
    if len(path_str) > 1 and path_str[1] == ":" and path_str[0].isalpha():
        drive = path_str[0].lower()
        rest = path_str[2:].replace("\\", "/")
        return f"/mnt/{drive}{rest}"
    return path_str

def install_package(package_name, force=False):
    try:
        pkgs = package_name.split()
        cmd = [sys.executable, "-m", "pip", "install"]
        if force: cmd.append("--force-reinstall")
        cmd.extend(pkgs)
        subprocess.check_call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except: return False

def _check_package_metadata(package_name):
    try:
        from importlib.metadata import version
        version(package_name)
        return True
    except: return False

def bootstrap(install_reqs=True):
    if not install_reqs: return
    os.environ['OLLAMA_MODELS'] = str(MODEL_STORE_ROOT)
    deps = [
        ("deepface", "deepface tf-keras opencv-python"),
        ("playwright", "playwright"),
        ("huggingface_hub", "huggingface_hub"),
        ("requests", "requests"),
        ("diffusers", "diffusers transformers accelerate scipy"),
        ("sklearn", "scikit-learn"),
        ("qwen_vl_utils", "qwen-vl-utils"),
        ("accelerate", "accelerate"),
    ]
    for import_name, pip_name in deps:
        try: __import__(import_name)
        except ImportError: install_package(pip_name)
    try: import playwright
    except ImportError:
        if install_package("playwright"):
            subprocess.run([sys.executable, "-m", "playwright", "install"], check=False)
    try:
        import bitsandbytes
        if not _check_package_metadata("bitsandbytes"): raise ImportError()
    except: install_package("bitsandbytes", force=True)
    
    google_deps = [("googleapiclient", "google-api-python-client"), ("google.auth", "google-auth google-auth-httplib2 google-auth-oauthlib"), ("cryptography", "cryptography")]
    for import_name, pip_name in google_deps:
        try: __import__(import_name)
        except ImportError: install_package(pip_name)

def slugify(text):
    return re.sub(r'[\W]+', '_', text.lower()).strip('_')

def gen_trigger(name):
    parts = name.split()
    first = parts[0].upper()[:2]
    last = parts[-1].upper()[0] if len(parts) > 1 else "X"
    return f"{first}{random.randint(100,999)}{last}"

def obfuscate_trigger(name: str) -> str:
    subst = {'a': '4', 'b': '8', 'e': '3', 'g': '9', 'i': '1', 'l': '1', 'o': '0', 's': '5', 't': '7', 'z': '2'}
    base = slugify(name).replace('_', '') or "anon"
    obf = ''.join(subst.get(ch, ch) for ch in base)
    suffix = hashlib.md5(base.encode()).hexdigest()[:4]
    return (obf + suffix).upper()

def log_trigger_to_sheet(name: str, trigger: str, description: str = ""):
    """Best-effort Google Sheet logging using Service Account or Token."""
    try:
        from googleapiclient.discovery import build
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google.oauth2 import service_account
        from cryptography.fernet import Fernet
        
        token_path = Path(_normalize_path(str(GOOGLE_TOKEN_PATH)))
        client_path = Path(_normalize_path(str(GOOGLE_CLIENT_SECRET)))
        key_path = Path(_normalize_path(str(GOOGLE_KEY_PATH)))
        creds = None

        if token_path.exists():
            try:
                with open(token_path, "rb") as token: encrypted = pickle.load(token)
                if isinstance(encrypted, bytes) and key_path.exists():
                    with open(key_path, "rb") as kf: key = kf.read()
                    fernet = Fernet(key)
                    creds = pickle.loads(fernet.decrypt(encrypted))
                else: creds = encrypted if hasattr(encrypted, "valid") else None
            except: pass

        if creds is None and client_path.exists():
            try: creds = service_account.Credentials.from_service_account_file(str(client_path), scopes=GOOGLE_SCOPES)
            except: pass

        if creds:
            if getattr(creds, "expired", False) and getattr(creds, "refresh_token", None): creds.refresh(Request())
            service = build("sheets", "v4", credentials=creds)
            body = {"values": [[name, trigger, datetime.utcnow().isoformat() + "Z", description]]}
            service.spreadsheets().values().append(
                spreadsheetId=GOOGLE_SHEET_ID, range="Sheet1!A:D", valueInputOption="USER_ENTERED", body=body
            ).execute()
            print(f"✅ Sheets: Logged {name}")
    except Exception as e: print(f"ℹ️ Sheets log skipped: {e}")

def get_project_path(slug):
    return LINUX_PROJECTS_ROOT / slug

def load_config(slug):
    path = get_project_path(slug) / "project_config.json"
    if not path.exists(): return None
    with open(path, 'r') as f: return json.load(f)

def save_config(slug, data):
    path = get_project_path(slug) / "project_config.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w') as f: json.dump(data, f, indent=4)

def get_windows_unc_path(wsl_path):
    """Translates WSL path to the //wsl.localhost/Ubuntu/... forward-slash format for TOML."""
    path_str = str(wsl_path)
    if not path_str.startswith("/home"): return path_str
    # Requirement: //wsl.localhost/Ubuntu/home/seanf/...
    return f"//wsl.localhost/Ubuntu{path_str}"

def update_trigger_db(slug, trigger, full_name):
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    row = [slug, trigger, full_name]
    file_exists = DB_PATH.exists()
    with open(DB_PATH, 'a', newline='') as f:
        writer = csv.writer(f)
        if not file_exists: writer.writerow(["slug", "trigger", "name"])
        writer.writerow(row)