from tzMCP.save_media_utils import hash_tracker


def test_in_memory_dedup():
    hash_tracker.init_hash_db(persist=False)
    assert hash_tracker.is_duplicate(b"hello") is False
    assert hash_tracker.is_duplicate(b"hello") is True
    assert hash_tracker.is_duplicate(b"world") is False


def test_sqlite_dedup_and_persistence(tmp_path):
    db_path = tmp_path / "hashes.sqlite"

    hash_tracker.init_hash_db(persist=True, db_path=db_path)
    assert hash_tracker.is_duplicate(b"payload") is False
    assert hash_tracker.is_duplicate(b"payload") is True
    hash_tracker.shutdown_hash_db()

    # Fresh connection to the same file still remembers the hash.
    hash_tracker.init_hash_db(persist=True, db_path=db_path)
    assert hash_tracker.is_duplicate(b"payload") is True
    hash_tracker.shutdown_hash_db()


def test_sqlite_creates_file(tmp_path):
    db_path = tmp_path / "nested" / "hashes.sqlite"
    hash_tracker.init_hash_db(persist=True, db_path=db_path)
    hash_tracker.is_duplicate(b"x")
    assert db_path.exists()
    hash_tracker.shutdown_hash_db()
