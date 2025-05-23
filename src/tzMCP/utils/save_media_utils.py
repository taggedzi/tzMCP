from io import BytesIO
import hashlib
import re
import os
import time
import json
import requests
import magic
from PIL import Image

# ----------------------------------
# Utility functions
# ----------------------------------

def log_duration(label, start_time):
    duration = time.perf_counter() - start_time
    print(f"[PROFILE] {label} took {duration:.4f}s", flush=True)

def send_log_to_gui(entry):
    try:
        requests.post("http://localhost:5001", json=entry, timeout=0.5)
    except requests.exceptions.RequestException:
        pass

def structured_log(color: str, *lines: str):
    entry = {
        "color": color,
        "weight": "bold",
        "lines": list(lines)
    }
    if not _config.get("suppress_diagnostics"):
        print(json.dumps(entry), flush=True)
        send_log_to_gui(entry)

def structured_debug(msg: str):
    if _config.get("debug", False):
        print(f"[DEBUG] {msg}", flush=True)

def sanitize_filename(filename: str, fallback_url: str = "") -> str:
    name = re.sub(r"[^\w\-_. ]", "_", filename)
    name = re.sub(r"\s+", "_", name.strip())
    name = name[:255]
    WINDOWS_RESERVED_NAMES = {
        "CON", "PRN", "AUX", "NUL",
        "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9",
        "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9"
    }
    if not name or name.upper() in WINDOWS_RESERVED_NAMES:
        hash_val = hashlib.sha256(fallback_url.encode()).hexdigest()[:12]
        name = f"file_{hash_val}"
    return name

def safe_filename(raw_name: str, ext: str, fallback_url: str = "") -> str:
    if not raw_name or "." not in raw_name:
        raw_name = f"file_{int(time.time() * 1000)}{ext}"
    elif not os.path.splitext(raw_name)[1]:
        raw_name += ext
    return sanitize_filename(raw_name, fallback_url)

def detect_mime(data: bytes) -> str:
    try:
        img = Image.open(BytesIO(data))
        return Image.MIME.get(img.format, "application/octet-stream")
    except Exception:
        try:
            return magic.from_buffer(data, mime=True)
        except Exception:
            return "application/octet-stream"

def domain_matches(url: str, domain_list: list[str]) -> bool:
    return any(domain in url for domain in domain_list)

_config = {}