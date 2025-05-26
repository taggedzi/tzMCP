# pylint: disable=logging-fstring-interpolation,redefined-outer-name,broad-exception-caught
import hashlib
import os
import re
import time
from io import BytesIO
from pathlib import Path
from tempfile import NamedTemporaryFile
from time import perf_counter
from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode
import filetype
from PIL import Image
from tzMCP.save_media_utils.config_provider import get_config
from tzMCP.save_media_utils.mime_data_minimal import MIME_TO_EXTENSIONS
from tzMCP.save_media_utils.mime_categories import MIME_GROUPS
from tzMCP.common_utils.log_config import setup_logging, log_proxy

# Configure log_proxy
setup_logging()

ENABLE_PERFORMANCE_CHECK = True
SENSITIVE_KEYS = {"token", "access_token", "auth", "session", "key"}

# Inverted map: ext -> mime
EXTENSION_TO_MIME = {}
for mime, extensions in MIME_TO_EXTENSIONS.items():
    for ext in extensions:
        EXTENSION_TO_MIME[ext.lower()] = mime

# ----------------------------------
# Utility functions
# ----------------------------------

def log_duration(label, start_time):
    """log performance tests."""
    if ENABLE_PERFORMANCE_CHECK:
        duration = time.perf_counter() - start_time
        log_proxy.debug(f"[PROFILE] {label} took {duration:.4f}s")

def sanitize_filename(filename: str, fallback_url: str = "") -> str:
    """Check filenames for bad/malformed/corrupt/malicious data."""
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
        log_proxy.info(f"File name {filename} is a reserved windows name. It has been renamed: {name}")
    return name

def safe_filename(raw_name: str, ext: str, fallback_url: str = "") -> str:
    """Make a file name safe to use. if possible."""
    if not raw_name or "." not in raw_name:
        raw_name = f"file_{int(time.time() * 1000)}{ext}"
    elif not os.path.splitext(raw_name)[1]:
        raw_name += ext
    return sanitize_filename(raw_name, fallback_url)

def detect_mime_and_extension(byte_data: bytes, fallback_url: str = "") -> tuple[str, str]:
    """
    Try to detect the MIME type and extension:
    1. From the URL's extension first (most reliable for plain/text)
    2. Fallback to filetype-based guessing
    """
    # --- Step 1: Try based on URL extension ---
    if fallback_url:
        base = os.path.basename(fallback_url.split("?", 1)[0])
        ext = os.path.splitext(base)[1].lower()
        if ext in EXTENSION_TO_MIME:
            log_proxy.info(f"URL extension found: {ext}. Using MIME type: {EXTENSION_TO_MIME[ext]}")
            return EXTENSION_TO_MIME[ext], ext
    log_proxy.debug("No extension found in url.")
        
    # --- Step 2: Fallback to content-based detection ---
    kind = filetype.guess(byte_data)
    if kind:
        mime = kind.mime
        extensions = MIME_TO_EXTENSIONS.get(mime)
        ext = f".{kind.extension}" if not extensions else extensions[0]
        log_proxy.info(f"Filetype tested as: {ext}. Using MIME type: {mime}")
        return mime, ext
    
    log_proxy.debug("No mime or extension found via 'filetype' guessing.")

    # --- Final fallback ---
    log_proxy.info("No extension determined autoassign '.bin'.")
    return "application/octet-stream", ".bin"

def sanitize_url(url: str) -> str:
    """Strip or redact sensitive query params from URLs."""
    parsed = urlparse(url)
    query = parse_qsl(parsed.query, keep_blank_values=True)
    redacted = [(k, "[REDACTED]" if k.lower() in SENSITIVE_KEYS else v) for k, v in query]
    clean_query = urlencode(redacted)
    return urlunparse(parsed._replace(query=clean_query))

def is_mime_type_allowed(mime_type: str, fname: str = None) -> bool:
    """Check if MIME type is in one of the allowed MIME groups."""
    start_check = perf_counter()
    config = get_config()

    allowed_types = set()
    for group in config.allowed_mime_groups:
        allowed_types.update(MIME_GROUPS.get(group, []))

    result = True
    if mime_type not in allowed_types:
        log_proxy.info(f"⏭ Skipped file {fname} Reason: MIME type {mime_type} not allowed.")
        result = False

    log_duration("is_mime_type_allowed()", start_check)
    return result


def is_file_size_out_of_bounds(size:int, fname:str = None):
    """Test Size against config file requested size"""
    start_is_domain_blocked_by_whitelist_check = perf_counter()
    response = False
    config = get_config()
    if config.filter_file_size.get("enabled"):
        min_b = config.filter_file_size["min_bytes"]
        max_b = config.filter_file_size["max_bytes"]
        if not min_b <= size <= max_b:
            log_proxy.info(f"⏭ Skipped {fname} Reason: {size} b not between [{min_b},{max_b}] bytes.")
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
            log_proxy.info(f"⏭ Skipped {fname} URL: {sanitize_url(url)} Reason: domain not in whitelist.")
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
            log_proxy.info(f"⏭ Skipped {fname} URL: {sanitize_url(url)} Reason: domain in blacklist.")
            response = True
    log_duration("is_domain_blacklisted() ", start_is_domian_blacklisted_check)
    return response

def is_valid_image(content: bytes):
    """Use the image library to determine if a content blob is a legitimate image."""
    start_is_valid_image_check = perf_counter()
    response = False
    try:
        img = Image.open(BytesIO(content))
        img.verify()  # Verify header-only, no full decode
        response = True
    except Exception:
        log_proxy.info("Not a valid image.")
        response = False
    log_duration("is_valid_image() ", start_is_valid_image_check)
    return response

def is_image_size_out_of_bounds(content: bytes, fname: str = None):
    """Check the size of an image and see if we want it."""
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
                log_proxy.info(f"⏭ Skipped file {fname} Reason: ({w}x{h} not in allowed ranges)")
                response = True
        except Exception as e:
            log_proxy.error(f"⛔ Pixel check failed: {e}")
    log_duration("is_image_size_out_of_bounds() ", start_is_image_size_out_of_bounds_check)
    return response

def does_header_match_size(content_length, actual, url):
    """Verifies that the content length of a file matches the actual size."""
    response = True
    if content_length is not None:
        try:
            expected = int(content_length)
            if expected != actual:
                log_proxy.warning(f"⛔ Content-Length mismatch: expected {expected}, got {actual} URL: {sanitize_url(url)}")
                response = False
        except ValueError:
            log_proxy.error(f"⚠ Invalid Content-Length header: {content_length} URL: {sanitize_url(url)}")
    return response

def cleanup_temp_file(tmp_path: Path):
    """Remove the temp files crated by browser profiles."""
    if tmp_path and tmp_path.exists():
        try:
            tmp_path.unlink()
            log_proxy.info(f"🧹 Cleaned up temp file → {tmp_path}")
        except Exception as cleanup_error:
            log_proxy.error(f"⚠ Failed to clean up temp file: {cleanup_error}")
            
def is_directory_traversal_attempted(save_path:str):
    """Check to see if a file or url is trying to do directory traversal"""
    start_check = perf_counter()
    response = False
    config = get_config()
    
    if not str(save_path).startswith(str(config.save_dir.resolve())):
        log_proxy.critical(f"❌ Security error this file attempted path traversal blocked → {save_path}")
        response = True
    else:
        # Ensure save directory exists
        config.save_dir.mkdir(parents=True, exist_ok=True)
    log_duration("is_directory_traversal_attempted() ", start_check)
    return response

def atomic_save(content: bytes, save_path: Path, size: int):
    """
    Write content to a temporary file and atomically move it to the final path.
    Ensures no partial file writes and handles cleanup on failure.
    """
    tmp_path = None
    try:
        with NamedTemporaryFile('wb', delete=False, dir=save_path.parent) as tmp:
            tmp.write(content)
            tmp_path = Path(tmp.name)

        final_path = save_path
        counter = 1
        while final_path.exists():
            final_path = save_path.with_stem(f"{save_path.stem}_{counter}")
            counter += 1

        os.replace(tmp_path, final_path)
        log_proxy.info(f"💾 Saved → {final_path} ({size} B)")

    except PermissionError:
        log_proxy.error(f"❌ Permission denied: {save_path}")
        cleanup_temp_file(tmp_path)

    except OSError as e:
        log_proxy.error(f"❌ OS error while saving: {e}")
        cleanup_temp_file(tmp_path)

    except Exception as e:
        log_proxy.error(f"❌ Unexpected save failure: {e}")
        cleanup_temp_file(tmp_path)
