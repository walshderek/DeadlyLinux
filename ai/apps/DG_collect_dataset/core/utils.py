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
# logic: utils.py is in /core/. ROOT is one level up.
# Path(__file__).resolve().parent.parent is /DG_collect_dataset/ (ROOT)
ROOT_DIR = Path(__file__).resolve().parent.parent 
VENV_PATH = ROOT_DIR / ".venv"
REQUIREMENTS_PATH = ROOT_DIR / "core" / "requirements.txt"
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
    "summary": "07_summary"
}

# --- MUSUBI PATH CONFIGURATION ---
# Based on project specification for WSL and Windows environments
MODEL_STORE_ROOT = Path("/mnt/c/AI/models")

MUSUBI_PATHS = {
    'wsl_app': "/home/seanf/deadlygraphics/ai/apps/musubi-tuner",
    'wsl_models': "/home/seanf/ai/models",
    'win_app': r"C:\AI\apps\musubi-tuner",
    'win_models': r"C:\AI\models",
    'win_datasets': r"C:\AI\apps\musubi-tuner\files\datasets"
}

# Google Sheets logging defaults
GOOGLE_SHEET_ID = "1RMWaEiBtSfDZXd1jZ00Fg145faXWqB33ssDiq34ZzXo"
GOOGLE_CLIENT_SECRET = r"C:\AI\apps\ComfyUI Desktop\custom_nodes\comfyui-google-sheets-integration\client_secret.json"
GOOGLE_TOKEN_PATH = r"C:\AI\apps\ComfyUI Desktop\custom_nodes\comfyui-google-sheets-integration\token.pickle"
GOOGLE_KEY_PATH = r"C:\AI\apps\ComfyUI Desktop\custom_nodes\comfyui-google-sheets-integration\encryption_key.key"
GOOGLE_SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

# --- CORE UTILITIES ---

def count_images_for_step(slug, step_num):
    """Utility: Count images for a given step to verify dataset persistence."""
    path = get_project_path(slug)
    # Map step to output dir
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
    if not out_dir.exists():
        return 0
    return len([f for f in os.listdir(out_dir) if f.lower().endswith(('.jpg', '.png', '.jpeg', '.webp'))])

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
    """Install package(s) via pip. Supports space-separated multiple packages."""
    print(f"📦 Installing {'(force) ' if force else ''}missing dependency: {package_name}...")
    try:
        pkgs = package_name.split()
        cmd = [sys.executable, "-m", "pip", "install"]
        if force:
            cmd.append("--force-reinstall")
        cmd.extend(pkgs)
        subprocess.check_call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(f"✅ Installed {package_name}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install {package_name}. Error: {e}")
        return False

def _check_package_metadata(package_name):
    """Check if package has valid metadata (catches bitsandbytes broken installs)."""
    try:
        from importlib.metadata import version
        version(package_name)
        return True
    except Exception:
        return False

def bootstrap(install_reqs=True):
    """Initializes environment and required modern training stack."""
    if not install_reqs: return
    os.environ['OLLAMA_MODELS'] = str(MODEL_STORE_ROOT)

    # Core dependencies with metadata verification
    deps_to_check = [
        ("deepface", "deepface tf-keras opencv-python"),
        ("playwright", "playwright"),
        ("huggingface_hub", "huggingface_hub"),
        ("requests", "requests"),
        ("diffusers", "diffusers transformers accelerate scipy"),
        ("sklearn", "scikit-learn"),
        ("qwen_vl_utils", "qwen-vl-utils"),
        ("accelerate", "accelerate"),
    ]
    
    for import_name, pip_name in deps_to_check:
        try:
            __import__(import_name)
        except ImportError:
            install_package(pip_name)

    # Special handling for playwright (needs browser install)
    try:
        import playwright
    except ImportError:
        if install_package("playwright"):
            subprocess.run([sys.executable, "-m", "playwright", "install"], check=False)

    # bitsandbytes needs special handling - check metadata not just import
    try:
        import bitsandbytes
        if not _check_package_metadata("bitsandbytes"):
            raise ImportError("bitsandbytes metadata missing")
    except (ImportError, Exception):
        print("🔧 bitsandbytes needs reinstall (metadata issue)...")
        install_package("bitsandbytes", force=True)

    # Google API dependencies for Sheets logging
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

def slugify(text):
    """Convert human name to filesystem-friendly slug."""
    return re.sub(r'[\W]+', '_', text.lower()).strip('_')

def gen_trigger(name):
    """Generate a standard project trigger word."""
    parts = name.split()
    first = parts[0].upper()[:2]
    last = parts[-1].upper()[0] if len(parts) > 1 else "X"
    return f"{first}{random.randint(100,999)}{last}"

def obfuscate_trigger(name: str) -> str:
    """Create a leetspeak-style trigger to avoid pretrained name collision."""
    subst = {
        'a': '4', 'b': '8', 'e': '3', 'g': '9', 'i': '1', 'l': '1', 'o': '0',
        's': '5', 't': '7', 'z': '2'
    }
    base = slugify(name).replace('_', '')
    if not base:
        base = "anon"
    obf = ''.join(subst.get(ch, ch) for ch in base)
    # deterministic: hash the name for suffix
    import hashlib
    suffix = hashlib.md5(base.encode()).hexdigest()[:4]
    return (obf + suffix).upper()

def log_trigger_to_sheet(name: str, trigger: str, description: str = ""):
    """Append trigger/name to Google Sheet. Supports encrypted tokens and service accounts."""
    try:
        from googleapiclient.discovery import build
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google.oauth2 import service_account
        from cryptography.fernet import Fernet
    except Exception:
        print("ℹ️ Sheets logging skipped (google API libs not installed).")
        return

    token_path = Path(_normalize_path(str(GOOGLE_TOKEN_PATH)))
    client_path = Path(_normalize_path(str(GOOGLE_CLIENT_SECRET)))
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
        body = {"values": [[name, trigger, datetime.utcnow().isoformat() + "Z", description]]}
        service.spreadsheets().values().append(
            spreadsheetId=GOOGLE_SHEET_ID,
            range="Sheet1!A:D",
            valueInputOption="USER_ENTERED",
            body=body,
        ).execute()
        print(f"✅ Logged trigger to Google Sheet for {name}")
    except Exception as e:
        print(f"ℹ️ Sheets logging skipped: {e}")

def get_project_path(slug):
    """Resolves absolute Linux path for project."""
    return LINUX_PROJECTS_ROOT / slug

def load_config(slug):
    """Load project config."""
    path = get_project_path(slug) / "project_config.json"
    if not path.exists(): return None
    with open(path, 'r') as f: return json.load(f)

def save_config(slug, data):
    """Save project config, creating directories if needed."""
    path = get_project_path(slug) / "project_config.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w') as f: json.dump(data, f, indent=4)

def get_windows_forward_path(slug, subfolder="256"):
    """
    Returns absolute Windows path with forward slashes for TOML compatibility.
    Target: C:/AI/apps/musubi-tuner/files/datasets/slug/subfolder.
    """
    base = MUSUBI_PATHS['win_app'].replace("\\", "/")
    return f"{base}/files/datasets/{slug}/{subfolder}"

def update_trigger_db(slug, trigger, full_name):
    """Appends project details to the local project database."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    row = [slug, trigger, full_name]
    file_exists = DB_PATH.exists()
    with open(DB_PATH, 'a', newline='') as f:
        writer = csv.writer(f)
        if not file_exists: writer.writerow(["slug", "trigger", "name"])
        writer.writerow(row)

if __name__ == "__main__":
    print("DG_collect_dataset Master Utility Library Loaded.")
