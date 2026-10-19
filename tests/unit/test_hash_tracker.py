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


def test_persistent_dedup_ignores_session_log_override(tmp_path, monkeypatch):
    monkeypatch.setenv("TZMCP_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("TZMCP_LOG_DIR", str(tmp_path / "session" / "logs"))

    hash_tracker.init_hash_db(persist=True)
    expected = tmp_path / "data" / "logs" / "hashes_seen.sqlite"
    assert expected.is_file()
    assert not (tmp_path / "session" / "logs" / "hashes_seen.sqlite").exists()
    assert hash_tracker.is_duplicate(b"payload") is False
    hash_tracker.shutdown_hash_db()

    hash_tracker.init_hash_db(persist=True)
    assert hash_tracker.is_duplicate(b"payload") is True
    assert expected.is_file()
    hash_tracker.shutdown_hash_db()


def test_sqlite_creates_file(tmp_path):
    db_path = tmp_path / "nested" / "hashes.sqlite"
    hash_tracker.init_hash_db(persist=True, db_path=db_path)
    hash_tracker.is_duplicate(b"x")
    assert db_path.exists()
    hash_tracker.shutdown_hash_db()
