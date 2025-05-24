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
from time import perf_counter
from tzMCP.save_media_utils.config_provider import get_config
from urllib.parse import urlparse
from mitmproxy import ctx
from threading import Thread

ENABLE_PERFORMANCE_CHECK = True

# ----------------------------------
# Utility functions
# ----------------------------------

def log_duration(label, start_time):
    if ENABLE_PERFORMANCE_CHECK:
        duration = time.perf_counter() - start_time
        print(f"[PROFILE] {label} took {duration:.4f}s", flush=True)

def send_log_to_gui(entry):
    def _post():
        try:
            requests.post("http://localhost:5001", json=entry, timeout=0.1)
        except requests.exceptions.RequestException:
            pass
    Thread(target=_post, daemon=True).start()

def log(level: str, color: str, *lines: str):
    """Log a message to the console and optionally to the GUI"""
    # only skip if it is a debug messsage and debug messages are not wanted.
    if level.lower() == "debug" and not get_config().log_internal_debug:
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

def is_extension_blocked(ext:str = None, fname:str = None):
    """Test Extensions against config file requested extensions"""
    start_is_extension_blocked_check = perf_counter()
    response = False
    allowed_exts = set(e.lower() for e in get_config().extensions)
    if ext.lower() not in allowed_exts:
        ctx.log.info(f"Skipping file with extension {ext.lower()} because it is not in the config's extensions list.")
        log("warn", "orange", f"⏭ Skipped file {fname}", f"\tReason: {ext.lower()} is not in the config's extensions list.")
        response = True
    log_duration("is_extension_blocked() ", start_is_extension_blocked_check)
    return response

def is_file_size_out_of_bounds(size:int, fname:str = None):
    """Test Size against config file requested size"""
    start_is_domain_blocked_by_whitelist_check = perf_counter()
    response = False
    config = get_config()
    if config.filter_file_size.get("enabled"):
        min_b = config.filter_file_size["min_bytes"]
        max_b = config.filter_file_size["max_bytes"]
        if not min_b <= size <= max_b:
            # log("warn", "orange",
            #     f"⏭ Skipped {fname}", f"\tReason: {size} b not between [{min_b},{max_b}] bytes.")
            response = True
    log_duration("is_file_size_out_of_bounds() ", start_is_domain_blocked_by_whitelist_check)
    return response

def is_domain_blocked_by_whitelist(url:str, fname:str = None):
    """
    Check domain whitelist 
    IF whitelist is NOT set (ie []), then allow all domains
    IF whitelist is set, then only allow domains that are in the list
    """
    start_is_domain_blocked_by_whitelist_check = perf_counter()
    response = False
    config = get_config()
    if config.whitelist:
        netloc = urlparse(url).hostname or ""
        if not any(domain in netloc for domain in config.whitelist):
            log("warn", "orange",
                f"⏭ Skipped {fname}", f"\tURL: {url}", "\tReason: domain not in whitelist.")
            response = True
    log_duration("is_domain_blocked_by_whitelist() ", start_is_domain_blocked_by_whitelist_check)
    return response

def is_domain_blacklisted(url:str, fname:str = None):
    """
    Check domain blacklist 
    IF blacklist is NOT set (ie []), then allow all domains
    IF blacklist is set, then only allow domains that are not in the list
    """
    start_is_domian_blacklisted_check = perf_counter()
    response = False
    config = get_config()
    if config.blacklist:
        netloc = urlparse(url).hostname or ""
        if any(domain in netloc for domain in config.blacklist):
            log("warn", "orange",
                f"⏭ Skipped {fname}", f"\tURL: {url}", "\tReason: domain in blacklist.")
            response = True
    log_duration("is_domain_blacklisted() ", start_is_domian_blacklisted_check)
    return response

def is_valid_image(content: bytes):
    start_is_valid_image_check = perf_counter()
    response = False
    try:
        img = Image.open(BytesIO(content))
        img.verify()  # Verify header-only, no full decode
        response = True
    except Exception:
        response = False
    log_duration("is_valid_image() ", start_is_valid_image_check)
    return response

def is_image_size_out_of_bounds(content: bytes, fname: str = None):
    start_is_image_size_out_of_bounds_check = perf_counter()
    response = False
    config = get_config()
    if config.filter_pixel_dimensions:
        try:
            img = Image.open(BytesIO(content))
            w, h = img.size
            min_w = config.filter_pixel_dimensions.get("min_width", 1)
            max_w = config.filter_pixel_dimensions.get("max_width", 999999)
            min_h = config.filter_pixel_dimensions.get("min_height", 1)
            max_h = config.filter_pixel_dimensions.get("max_height", 999999)
            if w < min_w or w > max_w or h < min_h or h > max_h:
                log("warn", "orange", f"⏭ Skipped file {fname}", f"\tReason: ({w}x{h} not in allowed ranges)")
                response = True
        except Exception as e:
            log("error", "red", f"⛔ Pixel check failed: {e}")
    log_duration("is_image_size_out_of_bounds() ", start_is_image_size_out_of_bounds_check)
    return response

def does_header_match_size(content_length, actual, url):
    """Verifies that the content length of a file matches the actual size."""
    response = True
    if content_length is not None:
        try:
            expected = int(content_length)
            if expected != actual:
                log("error", "red", f"⛔ Content-Length mismatch: expected {expected}, got {actual}", f"\tURL: {url}")
                response = False
        except ValueError:
            log("error","red", f"⚠ Invalid Content-Length header: {content_length}", f"\tURL: {url}")
    return response
