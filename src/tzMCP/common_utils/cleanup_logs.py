import time
from pathlib import Path
from tzMCP.common_utils.log_config import log_proxy

def clean_old_logs(log_dir: Path, max_age_days: int = 7, extensions=(".log",)) -> list[Path]:
    """
    Delete log files older than `max_age_days`. 
    Only files matching `extensions` are deleted.
    Returns list of deleted paths.
    """
    deleted = []
    now = time.time()
    cutoff = now - (max_age_days * 86400)

    if not log_dir.exists():
        return deleted

    for item in log_dir.iterdir():
        try:
            if item.is_file() and item.suffix in extensions and item.stat().st_mtime < cutoff:
                item.unlink()
                deleted.append(item)
        except Exception as e:
            log_proxy.warning(f"⚠️ Failed to remove log file {item}: {e}")

    if deleted:
        log_proxy.info(f"🧹 Cleaned up {len(deleted)} old log files from {log_dir}")
    else:
        log_proxy.info(f"🧼 No old log files to clean in {log_dir}")

    return deleted