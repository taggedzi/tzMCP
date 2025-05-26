# mime_categories.py

from tzMCP.save_media_utils.mime_data_minimal import MIME_TO_EXTENSIONS

# Build category sets based on standard and known nonstandard prefixes
def _matches(mime: str, keyword: str) -> bool:
    return mime.startswith(f"{keyword}/") or keyword in mime

# Define categories from MIME type prefixes and known patterns
MIME_GROUPS = {
    "image": {m for m in MIME_TO_EXTENSIONS if _matches(m, "image")},
    "video": {m for m in MIME_TO_EXTENSIONS if _matches(m, "video")},
    "audio": {m for m in MIME_TO_EXTENSIONS if _matches(m, "audio")},
    "text":  {m for m in MIME_TO_EXTENSIONS if _matches(m, "text")},
    "document": {
        "application/pdf",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.ms-excel",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.ms-powerpoint",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "application/epub+zip",
    },
    "executable": {
        "application/x-msdownload",
        "application/x-executable",
        "application/x-sh",
        "application/x-dosexec",
        "application/x-elf",
        "application/vnd.microsoft.portable-executable",
        "application/x-mach-binary",
    }
}

# Optional: export individual sets if needed elsewhere
IMAGE_TYPES = MIME_GROUPS["image"]
VIDEO_TYPES = MIME_GROUPS["video"]
AUDIO_TYPES = MIME_GROUPS["audio"]
TEXT_TYPES  = MIME_GROUPS["text"]
DOCUMENT_TYPES = MIME_GROUPS["document"]
EXECUTABLE_TYPES = MIME_GROUPS["executable"]
