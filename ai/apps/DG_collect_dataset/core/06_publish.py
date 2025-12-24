# 06_publish.py
# Generates:
# - files/tomls/{slug}_win.toml  (from config_template.toml)
# - train_{slug}_{res}.bat       (from train_template.bat)
#
# Requires:
# - C:\AI\apps\musubi-tuner\files\tomls\config_template.toml
# - C:\AI\apps\musubi-tuner\train_template.bat

from __future__ import annotations

import sys
from pathlib import Path


# --- EDIT THESE DEFAULTS IF YOU WANT ---
WAN_ROOT_DEFAULT = r"C:\AI\apps\musubi-tuner"
MODELS = {
    "DIT_LOW":  r"C:\AI\models\diffusion_models\Wan\Wan2.2\14B\Wan_2_2_T2V\bf16\Wan-2.2-T2V-Low-Noise-BF16.safetensors",
    "DIT_HIGH": r"C:\AI\models\diffusion_models\Wan\Wan2.2\14B\Wan_2_2_T2V\bf16\Wan-2.2-T2V-High-Noise-BF16.safetensors",
    "VAE":      r"C:\AI\models\vae\WAN\Wan2.1_VAE.pth",
    "T5":       r"C:\AI\models\clip\models_t5_umt5-xxl-enc-bf16.pth",
}

TRAIN_DEFAULTS = {
    "LEARNING_RATE": "0.0001",
    "NETWORK_ALPHA": "128",
    "NETWORK_DIM": "128",
    "N_WORKERS": "4",
    "EPOCHS": "10",
    "GRAD_ACCUM": "1",
}


def _norm_toml_path(p: str) -> str:
    # TOML wants forward slashes reliably across platforms.
    return p.replace("\\", "/")


def _read_text(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"Missing required file: {path}")
    return path.read_text(encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def fill_placeholders(template: str, mapping: dict[str, str]) -> str:
    out = template
    for k, v in mapping.items():
        out = out.replace(f"@{k}@", str(v))
    return out


def publish(slug: str, res: int, wan_root: str = WAN_ROOT_DEFAULT) -> None:
    wan_root_path = Path(wan_root)

    # Inputs (templates)
    local_template_path = Path(__file__).parent / "templates" / "config_template.toml"
    toml_template_path = local_template_path if local_template_path.exists() else wan_root_path / "files" / "tomls" / "config_template.toml"
    local_bat_template_path = Path(__file__).parent / "templates" / "train_template.bat"
    bat_template_path = local_bat_template_path if local_bat_template_path.exists() else wan_root_path / "train_template.bat"

    toml_template = _read_text(toml_template_path)
    bat_template = _read_text(bat_template_path)

    # Output locations
    dataset_dir = wan_root_path / "files" / "datasets" / slug / str(res)
    cache_dir = dataset_dir / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)

    out_toml_path = wan_root_path / "files" / "tomls" / f"{slug}_win.toml"
    out_bat_path = wan_root_path / f"train_{slug}_{res}.bat"

    # Build replacements for TOML template
    toml_map: dict[str, str] = {}
    toml_map["DATASET_PATH"] = _norm_toml_path(str(dataset_dir))
    toml_map["CACHE_PATH"] = _norm_toml_path(str(cache_dir))

    # Training placeholder vars from your template
    toml_map.update(TRAIN_DEFAULTS)

    # Fill TOML
    toml_out = fill_placeholders(toml_template, toml_map)

    # Hard sanity checks
    if "@DATASET_PATH@" in toml_out or "@CACHE_PATH@" in toml_out:
        raise RuntimeError(
            "TOML publish failed: @DATASET_PATH@ or @CACHE_PATH@ still present after replacement."
        )

    # Warn if other placeholders remain
    if "@" in toml_out:
        print(
            "WARNING: TOML still contains '@' tokens. "
            "Your template likely has additional placeholders not filled by this script.",
            file=sys.stderr,
        )

    _write_text(out_toml_path, toml_out)

    # Build replacements for BAT template
    out_dir = wan_root_path / "outputs" / slug
    log_dir = wan_root_path / "logs"

    bat_map: dict[str, str] = {
        "WAN": str(wan_root_path),
        "CFG": str(out_toml_path),
        "DIT_LOW": MODELS["DIT_LOW"],
        "DIT_HIGH": MODELS["DIT_HIGH"],
        "VAE": MODELS["VAE"],
        "T5": MODELS["T5"],
        "OUT": str(out_dir),
        "OUTNAME": slug,
        "LOGDIR": str(log_dir),
        # If your BAT template includes these placeholders too, fill them:
        **TRAIN_DEFAULTS,
    }

    bat_out = fill_placeholders(bat_template, bat_map)

    if "@CFG@" in bat_out or "@WAN@" in bat_out:
        raise RuntimeError("BAT publish failed: @CFG@ or @WAN@ still present after replacement.")

    _write_text(out_bat_path, bat_out)

    print(f"✅ Published: {slug} ({res})")
    print(f"   TOML: {out_toml_path}")
    print(f"   BAT : {out_bat_path}")
    print(f"   DATA: {dataset_dir}")
    print(f"   CACHE DIR (created/ensured): {cache_dir}")


# -----------------------------
# Backwards-compatible entrypoint
# Some parts of your workflow call run(slug) directly.
# -----------------------------
def run(slug: str, res: int = 256, wan_root: str = WAN_ROOT_DEFAULT) -> None:
    publish(slug=slug, res=res, wan_root=wan_root)


def main() -> None:
    # Usage:
    #   python 06_publish.py theresa_may
    #   python 06_publish.py theresa_may 256
    #   python 06_publish.py theresa_may 256 "C:\AI\apps\musubi-tuner"
    if len(sys.argv) < 2:
        print("Usage: python 06_publish.py <slug> [resolution=256] [wan_root=C:\\AI\\apps\\musubi-tuner]")
        raise SystemExit(2)

    slug = sys.argv[1]
    res = int(sys.argv[2]) if len(sys.argv) >= 3 else 256
    wan_root = sys.argv[3] if len(sys.argv) >= 4 else WAN_ROOT_DEFAULT

    run(slug=slug, res=res, wan_root=wan_root)


if __name__ == "__main__":
    main()
