import shutil
import time
from pathlib import Path
from tzMCP.common_utils.log_config import log_proxy

def clean_old_profiles(profile_dir: Path, max_age_days: int = 3) -> list[Path]:
    """
    Delete profile directories older than `max_age_days`.
    Returns a list of deleted paths for reporting/logging.
    """
    deleted = []
    now = time.time()
    cutoff = now - (max_age_days * 86400)

    if not profile_dir.exists():
        return deleted

    for item in profile_dir.iterdir():
        try:
            if item.is_dir() and item.stat().st_mtime < cutoff:
                shutil.rmtree(item)
                deleted.append(item)
        except Exception as e:
            log_proxy.warning(f"⚠️ Failed to remove profile {item}: {e}")

    if deleted:
        log_proxy.info(f"🧹 Removed {len(deleted)} expired browser profiles from {profile_dir}")
    else:
        log_proxy.info(f"🧼 No expired browser profiles found in {profile_dir}")

    return deleted