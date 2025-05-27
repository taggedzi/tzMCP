# pylint: disable=global-statement,logging-fstring-interpolation,invalid-name
import sqlite3
import hashlib
from pathlib import Path
from tzMCP.common_utils.log_config import setup_logging, log_proxy

setup_logging()
_db = None

def init_hash_db(persist: bool = True, db_path: Path = None):
    """Initialize a hash database."""
    global _db

    # if SQLite Not used, Save hashes to Memory Set.
    if not persist:
        _db = set()
        log_proxy.debug("Persistent DeDuping not enabled using in memory set().")
        return

    if db_path is None:
        db_path = Path(__file__).parent.parent.parent.parent / "logs" / "hashes_seen.sqlite"
        log_proxy.debug(f"Dedupe DB setups at: {db_path}.")
    db_path.parent.mkdir(parents=True, exist_ok=True)

    log_proxy.info("Staring SQLite3 database and initializing.")
    _db = sqlite3.connect(db_path)
    _db.execute("CREATE TABLE IF NOT EXISTS hashes (hash TEXT PRIMARY KEY)")
    _db.commit()

def is_duplicate(content: bytes) -> bool:
    """Generate a hash for a file, and compare to db to see if already in existence."""
    h = hashlib.sha256(content).hexdigest()

    if isinstance(_db, set):
        if h in _db:
            log_proxy.debug("Hash found in set this is a Duplicate file.")
            return True
        log_proxy.debug("Hash not found in set, adding.")
        _db.add(h)
        return False


    cur = _db.execute("SELECT 1 FROM hashes WHERE hash = ?", (h,))
    if cur.fetchone():
        log_proxy.debug("Hash found in DB.")
        return True
    log_proxy.debug("Hash not foundin DB, adding.")
    _db.execute("INSERT INTO hashes (hash) VALUES (?)", (h,))
    _db.commit()
    return False

def shutdown_hash_db():
    """Shutdown DB connection if it exists."""
    if isinstance(_db, sqlite3.Connection):
        log_proxy.info("Shutting down sqlite3 databse.")
        _db.close()
