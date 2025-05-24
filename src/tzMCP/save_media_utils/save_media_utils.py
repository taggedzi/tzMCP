from io import BytesIO
from pathlib import Path
import hashlib
import json
import os
import re
import time
import yaml
from PIL import Image
import requests
import magic
from tzMCP.save_media_utils.config_provider import get_config

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

def log(level: str, color: str, *lines: str):
    config = get_config()
    if config is None or not config.log_internal_debug:
        raise ValueError("Config not found")
    level = level.lower()
    
    # only skip if it is a debug messsage and debug messages are not wanted.
    if level == "debug" and not config.log_internal_debug:
        return
    
    # Print to console
    print("\n".join(list(lines)), flush=True)
    
    # Send to GUI
    entry = {
        "color": color,
        "weight": "bold",
        "lines": list(lines)
    }
    send_log_to_gui(entry)

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
