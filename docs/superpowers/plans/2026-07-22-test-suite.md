# tzMCP Test Suite Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build tzMCP's first automated test suite — unit tests for the pure logic plus integration tests for the mitmproxy addon capture flow — fully isolated from the real config/logs/cache directories.

**Architecture:** pytest suite under `tests/`, split into `unit/` and `integration/`. A shared `conftest.py` provides autouse fixtures that reset the two module-level globals (`config_provider._config_data`, `hash_tracker._db`), neutralize the GUI-log network call, and keep all disk writes inside `tmp_path`. Tests target the *existing* implementation, so each test is expected to PASS immediately; the one known defect (regex-vs-substring domain matching) is captured with `strict=True` xfail tests.

**Tech Stack:** Python 3.13, pytest 9.0.3, Pillow (real PNG bytes), PyYAML, mitmproxy (types only, no live proxy).

## Global Constraints

- Tests MUST run without installing the package: `pyproject.toml` sets `pythonpath = ["src"]`.
- No test may read or write the real `config/`, `logs/`, or `cache/` directories — everything goes under pytest's `tmp_path`.
- No network: the GUI-log POST to `localhost:5001` is monkeypatched to a no-op in an autouse fixture.
- The domain-filter defect is NOT fixed in this pass. Current substring behavior is pinned by passing tests; intended regex behavior is asserted only in `@pytest.mark.xfail(strict=True)` tests.
- Commit after each task with the shown message.

---

## File Structure

- Create `tests/conftest.py` — shared + autouse fixtures.
- Create `tests/__init__.py`, `tests/unit/__init__.py`, `tests/integration/__init__.py` — empty (keeps import paths clean).
- Create `tests/unit/test_save_media_utils.py`
- Create `tests/unit/test_config_manager.py`
- Create `tests/unit/test_hash_tracker.py`
- Create `tests/unit/test_cli.py`
- Create `tests/unit/test_gen_whitelist_regex.py`
- Create `tests/integration/test_media_saver_response.py`
- Modify `pyproject.toml` — add `[tool.pytest.ini_options]`.

---

### Task 1: Test scaffolding, pytest config, and shared fixtures

**Files:**
- Modify: `pyproject.toml`
- Create: `tests/__init__.py`, `tests/unit/__init__.py`, `tests/integration/__init__.py` (all empty)
- Create: `tests/conftest.py`
- Create: `tests/unit/test_scaffolding.py` (temporary sanity test, removed at end of task)

**Interfaces:**
- Produces (fixtures, all in `conftest.py`):
  - `make_png(width: int, height: int) -> bytes` — real PNG bytes.
  - `tiny_png: bytes` — a 500x500 PNG.
  - `not_an_image: bytes` — `b"this is not an image"`.
  - `isolated_config(**overrides) -> Config` — a `Config` with `save_dir` under `tmp_path`, registered via `config_provider.set_config`. Accepts keyword overrides applied to the returned `Config`.
  - `make_flow(url, content, content_length="auto", extra_headers=None)` — a `SimpleNamespace` shaped like `mitmproxy.http.HTTPFlow`.
  - `write_config_file(data: dict) -> Path` — writes YAML into `tmp_path`, returns the path.
- Autouse fixtures (no explicit consumption needed): `_reset_config_provider`, `_reset_hash_db`, `_silence_gui_log`, `_default_isolated_save_dir`.

- [ ] **Step 1: Add pytest config to `pyproject.toml`**

Append this section to `pyproject.toml`:

```toml
[tool.pytest.ini_options]
pythonpath = ["src"]
testpaths = ["tests"]
addopts = "-ra"
```

- [ ] **Step 2: Create empty package-marker files**

Create four empty files: `tests/__init__.py`, `tests/unit/__init__.py`, `tests/integration/__init__.py`. (Content: empty.)

- [ ] **Step 3: Write `tests/conftest.py`**

```python
"""Shared fixtures for the tzMCP test suite.

All isolation fixtures are autouse so ordering can never leak global state
between tests, and no test can touch the real config/logs/cache directories.
"""
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml
from PIL import Image

from tzMCP.gui_bits.config_manager import Config
from tzMCP.save_media_utils import config_provider
from tzMCP.save_media_utils import hash_tracker
from tzMCP.common_utils import log_config


# --------------------------------------------------------------------------
# Autouse isolation fixtures
# --------------------------------------------------------------------------
@pytest.fixture(autouse=True)
def _reset_config_provider():
    """Restore the global config-provider state around every test."""
    saved = config_provider.get_config()
    yield
    config_provider.set_config(saved if saved else {})
    config_provider.set_config({})


@pytest.fixture(autouse=True)
def _reset_hash_db():
    """Reset the module-level hash DB before and after each test."""
    hash_tracker.shutdown_hash_db()
    hash_tracker._db = None
    yield
    hash_tracker.shutdown_hash_db()
    hash_tracker._db = None


@pytest.fixture(autouse=True)
def _silence_gui_log(monkeypatch):
    """Stop every log record from spawning a requests.post thread."""
    monkeypatch.setattr(log_config, "send_log_to_gui", lambda entry: None)


@pytest.fixture(autouse=True)
def _default_isolated_save_dir(tmp_path, monkeypatch):
    """Point the default Config.save_dir at tmp_path so any bare Config()
    that gets validated never mkdirs the real cache directory."""
    monkeypatch.setattr(
        Config, "save_dir", tmp_path / "cache", raising=False
    )


# --------------------------------------------------------------------------
# Data + factory fixtures
# --------------------------------------------------------------------------
@pytest.fixture
def make_png():
    def _make(width, height):
        buf = BytesIO()
        Image.new("RGB", (width, height), (120, 120, 120)).save(buf, "PNG")
        return buf.getvalue()
    return _make


@pytest.fixture
def tiny_png(make_png):
    return make_png(500, 500)


@pytest.fixture
def not_an_image():
    return b"this is not an image"


@pytest.fixture
def isolated_config(tmp_path):
    def _make(**overrides):
        cfg = Config()
        cfg.save_dir = tmp_path / "cache"
        for key, value in overrides.items():
            setattr(cfg, key, value)
        config_provider.set_config(cfg)
        return cfg
    return _make


@pytest.fixture
def make_flow():
    def _make(url, content, content_length="auto", extra_headers=None):
        if content_length == "auto":
            content_length = str(len(content))
        headers = {}
        if content_length is not None:
            headers["Content-Length"] = content_length
        if extra_headers:
            headers.update(extra_headers)
        return SimpleNamespace(
            request=SimpleNamespace(pretty_url=url),
            response=SimpleNamespace(content=content, headers=headers),
        )
    return _make


@pytest.fixture
def write_config_file(tmp_path):
    def _write(data):
        path = tmp_path / "media_proxy_config.yaml"
        with path.open("w", encoding="utf-8") as f:
            yaml.safe_dump(data, f)
        return path
    return _write
```

- [ ] **Step 4: Write a temporary scaffolding sanity test**

Create `tests/unit/test_scaffolding.py`:

```python
def test_fixtures_wire_up(isolated_config, make_flow, tiny_png):
    cfg = isolated_config(allowed_mime_groups=["image"])
    assert cfg.allowed_mime_groups == ["image"]
    assert str(cfg.save_dir).endswith("cache")
    flow = make_flow("http://x/pic.png", tiny_png)
    assert flow.request.pretty_url == "http://x/pic.png"
    assert flow.response.headers.get("Content-Length") == str(len(tiny_png))
    assert tiny_png[:8] == b"\x89PNG\r\n\x1a\n"
```

- [ ] **Step 5: Run the sanity test — expect PASS**

Run: `venv/Scripts/python.exe -m pytest tests/unit/test_scaffolding.py -v`
Expected: 1 passed. (If import errors occur, the `pythonpath` config is wrong — fix Step 1.)

- [ ] **Step 6: Delete the temporary sanity test**

Delete `tests/unit/test_scaffolding.py` (its job was to prove the scaffolding works).

- [ ] **Step 7: Commit**

```bash
git add pyproject.toml tests/
git commit -m "test: add pytest scaffolding and shared isolation fixtures"
```

---

### Task 2: Unit tests for `save_media_utils`

**Files:**
- Create: `tests/unit/test_save_media_utils.py`

**Interfaces:**
- Consumes: `isolated_config`, `make_png`, `not_an_image` fixtures from Task 1.

- [ ] **Step 1: Write the test file**

Create `tests/unit/test_save_media_utils.py`:

```python
from pathlib import Path

import pytest

from tzMCP.save_media_utils import save_media_utils as smu


# ---- sanitize_filename ----------------------------------------------------
def test_sanitize_filename_replaces_illegal_chars():
    assert smu.sanitize_filename("a b/c*d.png") == "a_b_c_d.png"


def test_sanitize_filename_truncates_to_255():
    long_name = "x" * 400
    assert len(smu.sanitize_filename(long_name)) == 255


def test_sanitize_filename_reserved_name_gets_hashed():
    result = smu.sanitize_filename("CON", fallback_url="http://x/y")
    assert result.startswith("file_")
    assert result != "CON"


def test_sanitize_filename_empty_gets_hashed():
    result = smu.sanitize_filename("", fallback_url="http://x/y")
    assert result.startswith("file_")


# ---- safe_filename --------------------------------------------------------
def test_safe_filename_no_dot_generates_name():
    result = smu.safe_filename("noext", ".png", fallback_url="http://x/y")
    assert result.startswith("file_")
    assert result.endswith(".png")


def test_safe_filename_missing_extension_appended():
    # ".gitignore" has a dot but no real extension -> ext is appended.
    assert smu.safe_filename(".gitignore", ".png") == ".gitignore.png"


def test_safe_filename_passthrough_sanitized():
    assert smu.safe_filename("good name.png", ".png") == "good_name.png"


# ---- detect_mime_and_extension -------------------------------------------
def test_detect_mime_from_url_extension():
    assert smu.detect_mime_and_extension(b"", "http://x/pic.png") == \
        ("image/png", ".png")


def test_detect_mime_from_content(make_png):
    mime, ext = smu.detect_mime_and_extension(make_png(10, 10), "")
    assert mime == "image/png"


def test_detect_mime_fallback_octet_stream():
    assert smu.detect_mime_and_extension(b"\x00\x01garbage", "") == \
        ("application/octet-stream", ".bin")


# ---- sanitize_url ---------------------------------------------------------
def test_sanitize_url_redacts_sensitive_keys():
    out = smu.sanitize_url("http://x/y?token=abc&auth=z&page=1")
    assert "%5BREDACTED%5D" in out  # url-encoded [REDACTED]
    assert "page=1" in out
    assert "abc" not in out


def test_sanitize_url_keeps_blank_values():
    out = smu.sanitize_url("http://x/y?empty=&page=1")
    assert "empty=" in out


# ---- is_mime_type_allowed -------------------------------------------------
def test_mime_allowed_in_group(isolated_config):
    isolated_config(allowed_mime_groups=["image"])
    assert smu.is_mime_type_allowed("image/png") is True


def test_mime_not_in_group(isolated_config):
    isolated_config(allowed_mime_groups=["image"])
    assert smu.is_mime_type_allowed("text/plain") is False


def test_mime_empty_groups_disallows(isolated_config):
    isolated_config(allowed_mime_groups=[])
    assert smu.is_mime_type_allowed("image/png") is False


# ---- is_file_size_out_of_bounds ------------------------------------------
def test_size_within_bounds(isolated_config):
    isolated_config(filter_file_size={"enabled": True, "min_bytes": 10,
                                      "max_bytes": 1000})
    assert smu.is_file_size_out_of_bounds(500) is False


def test_size_below_min(isolated_config):
    isolated_config(filter_file_size={"enabled": True, "min_bytes": 100,
                                      "max_bytes": 1000})
    assert smu.is_file_size_out_of_bounds(50) is True


def test_size_above_max(isolated_config):
    isolated_config(filter_file_size={"enabled": True, "min_bytes": 10,
                                      "max_bytes": 100})
    assert smu.is_file_size_out_of_bounds(500) is True


def test_size_filter_disabled(isolated_config):
    isolated_config(filter_file_size={"enabled": False, "min_bytes": 10,
                                      "max_bytes": 100})
    assert smu.is_file_size_out_of_bounds(999999) is False


# ---- is_domain_blocked_by_whitelist (current SUBSTRING behavior) ---------
def test_whitelist_empty_allows_all(isolated_config):
    isolated_config(whitelist=[])
    assert smu.is_domain_blocked_by_whitelist("http://any.com/x") is False


def test_whitelist_substring_match_allows(isolated_config):
    isolated_config(whitelist=["example.com"])
    assert smu.is_domain_blocked_by_whitelist("http://www.example.com/x") is False


def test_whitelist_non_match_blocks(isolated_config):
    isolated_config(whitelist=["example.com"])
    assert smu.is_domain_blocked_by_whitelist("http://other.org/x") is True


# ---- is_domain_blacklisted (current SUBSTRING behavior) ------------------
def test_blacklist_empty_allows_all(isolated_config):
    isolated_config(blacklist=[])
    assert smu.is_domain_blacklisted("http://any.com/x") is False


def test_blacklist_substring_match_blocks(isolated_config):
    isolated_config(blacklist=["doubleclick.net"])
    assert smu.is_domain_blacklisted("http://ads.doubleclick.net/x") is True


def test_blacklist_non_match_allows(isolated_config):
    isolated_config(blacklist=["doubleclick.net"])
    assert smu.is_domain_blacklisted("http://good.com/x") is False


# ---- KNOWN DEFECT: matcher uses substring, not regex ---------------------
# See docs/superpowers/specs/2026-07-22-test-suite-design.md.
# These document the *intended* regex behavior; they xpass the day the
# matcher is fixed (strict=True turns an unexpected pass into a failure).
@pytest.mark.xfail(strict=True,
                   reason="matcher uses substring, not regex; default "
                          "blacklist should block ads.doubleclick.net")
def test_blacklist_default_regex_should_block(isolated_config):
    isolated_config()  # default blacklist ships regex entries
    assert smu.is_domain_blacklisted("http://ads.doubleclick.net/img.png") is True


@pytest.mark.xfail(strict=True,
                   reason="matcher uses substring, not regex; a regex "
                          "whitelist entry should allow a matching host")
def test_whitelist_regex_should_allow(isolated_config):
    isolated_config(whitelist=[r".*\.example\.com"])
    assert smu.is_domain_blocked_by_whitelist("http://cdn.example.com/x") is False


# ---- is_valid_image -------------------------------------------------------
def test_is_valid_image_true(make_png):
    assert smu.is_valid_image(make_png(10, 10)) is True


def test_is_valid_image_false(not_an_image):
    assert smu.is_valid_image(not_an_image) is False


# ---- is_image_size_out_of_bounds -----------------------------------------
def test_image_within_pixel_bounds(isolated_config, make_png):
    isolated_config(filter_pixel_dimensions={"min_width": 100, "min_height": 100,
                                             "max_width": 1000, "max_height": 1000})
    assert smu.is_image_size_out_of_bounds(make_png(500, 500)) is False


def test_image_too_small(isolated_config, make_png):
    isolated_config(filter_pixel_dimensions={"min_width": 100, "min_height": 100,
                                             "max_width": 1000, "max_height": 1000})
    assert smu.is_image_size_out_of_bounds(make_png(10, 10)) is True


def test_image_pixel_filter_disabled_via_empty_dict(isolated_config, make_png):
    isolated_config(filter_pixel_dimensions={})
    assert smu.is_image_size_out_of_bounds(make_png(10, 10)) is False


# ---- does_header_match_size ----------------------------------------------
def test_header_none_matches():
    assert smu.does_header_match_size(None, 100, "http://x") is True


def test_header_equal_matches():
    assert smu.does_header_match_size("100", 100, "http://x") is True


def test_header_mismatch():
    assert smu.does_header_match_size("100", 50, "http://x") is False


def test_header_non_integer_is_tolerated():
    assert smu.does_header_match_size("abc", 50, "http://x") is True


# ---- is_directory_traversal_attempted ------------------------------------
def test_traversal_inside_save_dir(isolated_config):
    cfg = isolated_config()
    cfg.save_dir.mkdir(parents=True, exist_ok=True)
    inside = (cfg.save_dir / "file.png").resolve()
    assert smu.is_directory_traversal_attempted(inside) is False


def test_traversal_outside_save_dir(isolated_config):
    cfg = isolated_config()
    cfg.save_dir.mkdir(parents=True, exist_ok=True)
    outside = Path("C:/Windows/system32/evil.png").resolve()
    assert smu.is_directory_traversal_attempted(outside) is True


# ---- atomic_save ----------------------------------------------------------
def test_atomic_save_writes_file(isolated_config):
    cfg = isolated_config()
    cfg.save_dir.mkdir(parents=True, exist_ok=True)
    target = cfg.save_dir / "out.txt"
    smu.atomic_save(b"hello", target, 5)
    assert target.read_bytes() == b"hello"


def test_atomic_save_collision_suffix(isolated_config):
    cfg = isolated_config()
    cfg.save_dir.mkdir(parents=True, exist_ok=True)
    target = cfg.save_dir / "out.txt"
    smu.atomic_save(b"first", target, 5)
    smu.atomic_save(b"second", target, 6)
    assert (cfg.save_dir / "out.txt").read_bytes() == b"first"
    assert (cfg.save_dir / "out_1.txt").read_bytes() == b"second"


# ---- cleanup_temp_file ----------------------------------------------------
def test_cleanup_temp_file_removes(tmp_path):
    p = tmp_path / "temp.bin"
    p.write_bytes(b"x")
    smu.cleanup_temp_file(p)
    assert not p.exists()


def test_cleanup_temp_file_missing_is_noop(tmp_path):
    smu.cleanup_temp_file(tmp_path / "does_not_exist.bin")  # must not raise
```

- [ ] **Step 2: Run the tests — expect PASS (with 2 xfail)**

Run: `venv/Scripts/python.exe -m pytest tests/unit/test_save_media_utils.py -v`
Expected: all pass; the two `test_*_should_*` tests report `XFAIL`. If any xfail unexpectedly `XPASS`es, the matcher was already fixed — stop and tell the user.

- [ ] **Step 3: Commit**

```bash
git add tests/unit/test_save_media_utils.py
git commit -m "test: cover save_media_utils filters, sanitizers, and atomic save"
```

---

### Task 3: Unit tests for `config_manager`

**Files:**
- Create: `tests/unit/test_config_manager.py`

**Interfaces:**
- Consumes: `tmp_path` (pytest builtin).

- [ ] **Step 1: Write the test file**

Create `tests/unit/test_config_manager.py`:

```python
from pathlib import Path

import yaml

from tzMCP.gui_bits.config_manager import Config, ConfigManager


def _mgr(tmp_path):
    return ConfigManager(tmp_path / "config" / "media_proxy_config.yaml")


def test_config_defaults():
    cfg = Config()
    assert cfg.log_level == "INFO"
    assert cfg.enable_persistent_dedup is False
    assert cfg.auto_reload_config is True
    assert cfg.allowed_mime_groups == []


def test_validate_drops_invalid_mime_groups(tmp_path):
    mgr = _mgr(tmp_path)
    cfg = Config()
    cfg.save_dir = tmp_path / "cache"
    cfg.allowed_mime_groups = ["image", "not_a_group", "video"]
    validated = mgr._validate_config(cfg)
    assert validated.allowed_mime_groups == ["image", "video"]


def test_validate_clamps_file_size(tmp_path):
    mgr = _mgr(tmp_path)
    cfg = Config()
    cfg.save_dir = tmp_path / "cache"
    cfg.filter_file_size = {"enabled": True, "min_bytes": -5, "max_bytes": -100}
    validated = mgr._validate_config(cfg)
    assert validated.filter_file_size["min_bytes"] == 0
    assert validated.filter_file_size["max_bytes"] >= validated.filter_file_size["min_bytes"]


def test_validate_clamps_pixel_dims(tmp_path):
    mgr = _mgr(tmp_path)
    cfg = Config()
    cfg.save_dir = tmp_path / "cache"
    cfg.filter_pixel_dimensions = {"min_width": 500, "min_height": 500,
                                   "max_width": 100, "max_height": 100}
    validated = mgr._validate_config(cfg)
    assert validated.filter_pixel_dimensions["max_width"] >= 500
    assert validated.filter_pixel_dimensions["max_height"] >= 500


def test_validate_normalizes_log_level(tmp_path):
    mgr = _mgr(tmp_path)
    cfg = Config()
    cfg.save_dir = tmp_path / "cache"
    cfg.log_level = "bogus"
    assert mgr._validate_config(cfg).log_level == "INFO"

    cfg.log_level = "debug"
    assert mgr._validate_config(cfg).log_level == "DEBUG"


def test_validate_makes_save_dir_absolute(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    mgr = _mgr(tmp_path)
    cfg = Config()
    cfg.save_dir = Path("relative_cache")
    validated = mgr._validate_config(cfg)
    assert validated.save_dir.is_absolute()


def test_load_config_reads_yaml(tmp_path):
    path = tmp_path / "config" / "media_proxy_config.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        yaml.safe_dump({
            "save_dir": str(tmp_path / "cache"),
            "allowed_mime_groups": ["image"],
            "log_level": "WARNING",
        }, f)
    mgr = ConfigManager(path)
    cfg = mgr.load_config()
    assert cfg.allowed_mime_groups == ["image"]
    assert cfg.log_level == "WARNING"
    assert isinstance(cfg.save_dir, Path)
    assert str(cfg.save_dir).endswith("cache")


def test_load_config_missing_file_uses_defaults(tmp_path):
    path = tmp_path / "config" / "media_proxy_config.yaml"
    mgr = ConfigManager(path)
    cfg = mgr.load_config()
    assert cfg.log_level == "INFO"


def test_save_config_roundtrip(tmp_path):
    path = tmp_path / "config" / "media_proxy_config.yaml"
    mgr = ConfigManager(path)
    cfg = Config()
    cfg.save_dir = tmp_path / "cache"
    cfg.allowed_mime_groups = ["image", "video"]
    cfg.log_level = "ERROR"
    mgr.save_config(cfg)

    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(raw["save_dir"], str)

    reloaded = ConfigManager(path).load_config()
    assert reloaded.allowed_mime_groups == ["image", "video"]
    assert reloaded.log_level == "ERROR"
```

- [ ] **Step 2: Run the tests — expect PASS**

Run: `venv/Scripts/python.exe -m pytest tests/unit/test_config_manager.py -v`
Expected: all pass.

- [ ] **Step 3: Commit**

```bash
git add tests/unit/test_config_manager.py
git commit -m "test: cover ConfigManager validation, load, and save round-trip"
```

---

### Task 4: Unit tests for `hash_tracker`

**Files:**
- Create: `tests/unit/test_hash_tracker.py`

**Interfaces:**
- Consumes: the autouse `_reset_hash_db` fixture (Task 1) guarantees a clean global `_db` per test.

- [ ] **Step 1: Write the test file**

Create `tests/unit/test_hash_tracker.py`:

```python
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
```

- [ ] **Step 2: Run the tests — expect PASS**

Run: `venv/Scripts/python.exe -m pytest tests/unit/test_hash_tracker.py -v`
Expected: all pass.

- [ ] **Step 3: Commit**

```bash
git add tests/unit/test_hash_tracker.py
git commit -m "test: cover hash_tracker in-memory and sqlite dedup modes"
```

---

### Task 5: Unit tests for `cli.build_config`

**Files:**
- Create: `tests/unit/test_cli.py`

**Interfaces:**
- Consumes: `tmp_path`. Builds an `argparse.Namespace` directly (does not invoke `parse_args`).

- [ ] **Step 1: Write the test file**

Create `tests/unit/test_cli.py`:

```python
from argparse import Namespace
from pathlib import Path

from tzMCP import cli


def _args(tmp_path, **overrides):
    """A Namespace matching parse_args() defaults, with a tmp config path."""
    base = dict(
        config=str(tmp_path / "config" / "media_proxy_config.yaml"),
        save_dir=None, mime_groups=None, whitelist=None, blacklist=None,
        min_bytes=None, max_bytes=None, min_width=None, max_width=None,
        min_height=None, max_height=None, log_to_file=False, log_level=None,
        dedup=False, auto_reload=True,
    )
    base.update(overrides)
    return Namespace(**base)


def test_build_config_defaults(tmp_path):
    cfg = cli.build_config(_args(tmp_path))
    assert cfg.log_level == "INFO"
    assert cfg.auto_reload_config is True
    assert cfg.enable_persistent_dedup is False


def test_build_config_applies_overrides(tmp_path):
    cfg = cli.build_config(_args(
        tmp_path,
        save_dir=str(tmp_path / "custom"),
        mime_groups=["image", "video"],
        whitelist=["a.com"],
        blacklist=["b.com"],
        min_bytes=0,
        max_bytes=999,
        min_width=10, max_width=20, min_height=30, max_height=40,
        log_to_file=True,
        log_level="DEBUG",
        dedup=True,
        auto_reload=False,
    ))
    assert cfg.save_dir == Path(tmp_path / "custom").resolve()
    assert cfg.allowed_mime_groups == ["image", "video"]
    assert cfg.whitelist == ["a.com"]
    assert cfg.blacklist == ["b.com"]
    assert cfg.filter_file_size["min_bytes"] == 0
    assert cfg.filter_file_size["max_bytes"] == 999
    assert cfg.filter_pixel_dimensions["min_width"] == 10
    assert cfg.filter_pixel_dimensions["max_width"] == 20
    assert cfg.filter_pixel_dimensions["min_height"] == 30
    assert cfg.filter_pixel_dimensions["max_height"] == 40
    assert cfg.log_to_file is True
    assert cfg.log_level == "DEBUG"
    assert cfg.enable_persistent_dedup is True
    assert cfg.auto_reload_config is False


def test_build_config_min_bytes_zero_is_applied(tmp_path):
    # min_bytes=0 is falsy but must still be applied (guarded by `is not None`).
    cfg = cli.build_config(_args(tmp_path, min_bytes=0))
    assert cfg.filter_file_size["min_bytes"] == 0
```

- [ ] **Step 2: Run the tests — expect PASS**

Run: `venv/Scripts/python.exe -m pytest tests/unit/test_cli.py -v`
Expected: all pass.

- [ ] **Step 3: Commit**

```bash
git add tests/unit/test_cli.py
git commit -m "test: cover cli.build_config default and override merging"
```

---

### Task 6: Unit tests for `gen_whitelist_regex.smart_regex`

**Files:**
- Create: `tests/unit/test_gen_whitelist_regex.py`

**Interfaces:**
- Consumes: nothing (pure function).

- [ ] **Step 1: Write the test file**

Create `tests/unit/test_gen_whitelist_regex.py`:

```python
from tzMCP.save_media_utils.gen_whitelist_regex import smart_regex


def test_two_part_domain_is_escaped():
    assert smart_regex("example.com") == r"example\.com"


def test_three_part_non_numeric_subdomain():
    assert smart_regex("cdn.example.com") == r".*\.example\.com"


def test_three_part_numeric_subdomain_double_escaped():
    # Documents the actual (quirky) output: the generated [0-9]+ is itself
    # re.escape'd. See the domain-matcher defect note in the spec.
    assert smart_regex("cdn12.example.com") == r"cdn\[0\-9\]\+\.example\.com"
```

- [ ] **Step 2: Run the tests — expect PASS**

Run: `venv/Scripts/python.exe -m pytest tests/unit/test_gen_whitelist_regex.py -v`
Expected: all pass.

- [ ] **Step 3: Commit**

```bash
git add tests/unit/test_gen_whitelist_regex.py
git commit -m "test: cover gen_whitelist_regex.smart_regex output"
```

---

### Task 7: Integration tests for `MediaSaver.response`

**Files:**
- Create: `tests/integration/test_media_saver_response.py`

**Interfaces:**
- Consumes: `isolated_config`, `make_png`, `make_flow` fixtures from Task 1.
- Note: constructs `MediaSaver` via `__new__` to skip `__init__` (which would start a watchdog observer and read the real config). Only `self.config` is needed by `response()`; the module helpers read the shared config via `config_provider`.

- [ ] **Step 1: Write the test file**

Create `tests/integration/test_media_saver_response.py`:

```python
import pytest

from tzMCP.save_media import MediaSaver
from tzMCP.save_media_utils import config_provider, hash_tracker


@pytest.fixture
def saver(isolated_config, make_png):
    """A MediaSaver wired to an isolated config, with permissive filters
    and no watchdog/observer or real hash DB."""
    cfg = isolated_config(
        allowed_mime_groups=["image"],
        whitelist=[],
        blacklist=[],
        filter_file_size={"enabled": True, "min_bytes": 0, "max_bytes": 10_000_000},
        filter_pixel_dimensions={},  # empty dict disables the pixel check
    )
    cfg.save_dir.mkdir(parents=True, exist_ok=True)
    config_provider.set_config(cfg)
    hash_tracker.init_hash_db(persist=False)

    instance = MediaSaver.__new__(MediaSaver)  # skip __init__ side effects
    instance.config = cfg
    return instance


def _saved_files(saver):
    return [p for p in saver.config.save_dir.iterdir() if p.is_file()]


def test_allowed_image_is_saved(saver, make_flow, make_png):
    flow = make_flow("http://site.com/pic.png", make_png(500, 500))
    saver.response(flow)
    assert len(_saved_files(saver)) == 1


def test_disallowed_mime_is_skipped(saver, make_flow, make_png):
    saver.config.allowed_mime_groups = ["video"]
    config_provider.set_config(saver.config)
    flow = make_flow("http://site.com/pic.png", make_png(500, 500))
    saver.response(flow)
    assert _saved_files(saver) == []


def test_size_out_of_bounds_is_skipped(saver, make_flow, make_png):
    saver.config.filter_file_size = {"enabled": True, "min_bytes": 10_000_000,
                                     "max_bytes": 20_000_000}
    config_provider.set_config(saver.config)
    flow = make_flow("http://site.com/pic.png", make_png(500, 500))
    saver.response(flow)
    assert _saved_files(saver) == []


def test_blacklisted_domain_is_skipped(saver, make_flow, make_png):
    saver.config.blacklist = ["blocked.com"]
    config_provider.set_config(saver.config)
    flow = make_flow("http://blocked.com/pic.png", make_png(500, 500))
    saver.response(flow)
    assert _saved_files(saver) == []


def test_non_whitelisted_domain_is_skipped(saver, make_flow, make_png):
    saver.config.whitelist = ["allowed.com"]
    config_provider.set_config(saver.config)
    flow = make_flow("http://other.com/pic.png", make_png(500, 500))
    saver.response(flow)
    assert _saved_files(saver) == []


def test_duplicate_content_saved_once(saver, make_flow, make_png):
    content = make_png(500, 500)
    saver.response(make_flow("http://site.com/a.png", content))
    saver.response(make_flow("http://site.com/b.png", content))
    assert len(_saved_files(saver)) == 1


def test_content_length_mismatch_is_skipped(saver, make_flow, make_png):
    flow = make_flow("http://site.com/pic.png", make_png(500, 500),
                     content_length="999999")
    saver.response(flow)
    assert _saved_files(saver) == []
```

- [ ] **Step 2: Run the tests — expect PASS**

Run: `venv/Scripts/python.exe -m pytest tests/integration/test_media_saver_response.py -v`
Expected: all pass.

- [ ] **Step 3: Run the full suite**

Run: `venv/Scripts/python.exe -m pytest -v`
Expected: all pass, 2 xfail, no errors, no files created outside `tmp_path`.

- [ ] **Step 4: Commit**

```bash
git add tests/integration/test_media_saver_response.py
git commit -m "test: cover MediaSaver.response filter pipeline end to end"
```

---

### Task 8: Coverage check and README update

**Files:**
- Modify: `README.md` (the "Testing (Coming Soon)" section)

**Interfaces:**
- Consumes: the completed suite.

- [ ] **Step 1: Run coverage for the in-scope modules**

Run: `venv/Scripts/python.exe -m pytest --cov=tzMCP --cov-report=term-missing`
Expected: a coverage report prints; `save_media_utils`, `config_manager`, `hash_tracker`, `cli`, `gen_whitelist_regex`, and `save_media` show meaningful coverage. (No hard threshold this pass — record the number.)

- [ ] **Step 2: Update the README Testing section**

Replace the `## 🧪 Testing (Coming Soon)` section of `README.md` with:

```markdown
## 🧪 Testing

Run the suite with pytest (no install required — `pyproject.toml` sets
`pythonpath = ["src"]`):

```bash
pytest              # or: invoke test
pytest --cov=tzMCP  # or: invoke coverage
```

The suite covers the media filters and sanitizers, config validation and
load/save, hash-based deduplication, the CLI config merge, and the
`MediaSaver.response()` capture pipeline (driven by mocked mitmproxy flows).
It is fully isolated and never touches your real `config/`, `logs/`, or
`cache/` directories.

> Two `xfail` tests document a known defect: the domain whitelist/blacklist
> matches by substring rather than regex, so regex entries in the default
> config do not fire. See
> `docs/superpowers/specs/2026-07-22-test-suite-design.md`.
```

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs: document the test suite in the README"
```

---

## Self-Review

**Spec coverage:** Every in-scope module in the spec maps to a task — save_media_utils (T2), config_manager (T3), hash_tracker (T4), cli (T5), gen_whitelist_regex (T6), MediaSaver.response (T7). All seven conftest fixtures and four autouse isolation fixtures are defined in T1. The known-defect xfail requirement is covered in T2. Isolation requirements (no real dirs, no network, globals reset) are enforced by T1's autouse fixtures and referenced throughout. README/coverage success criteria covered in T8.

**Placeholder scan:** No TBD/TODO/"add error handling"/"similar to" placeholders. Every code step contains complete, runnable code.

**Type consistency:** Fixture names and signatures used in Tasks 2–7 (`isolated_config(**overrides)`, `make_png(w, h)`, `make_flow(url, content, content_length=...)`, `tiny_png`, `not_an_image`, `write_config_file`) match their definitions in Task 1. Function names under test match the source (`is_domain_blocked_by_whitelist`, `is_domain_blacklisted`, `detect_mime_and_extension`, `build_config`, `smart_regex`, `init_hash_db(persist=..., db_path=...)`, `MediaSaver.response`).

**One known behavioral note for the implementer:** these tests target *existing* code, so the normal TDD red-then-green is inverted — each test is expected to PASS on first run. A test that fails unexpectedly means a real regression or a wrong assumption in the plan; investigate rather than "make it pass." The two xfail tests are the deliberate exception.
