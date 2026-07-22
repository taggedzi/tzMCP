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
