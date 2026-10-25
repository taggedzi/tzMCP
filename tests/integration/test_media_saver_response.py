import errno

import brotli
import pytest
from mitmproxy import http
from mitmproxy.net import encoding
from packaging.version import Version

from tzMCP.gui_bits.config_manager import Config, ConfigManager
from tzMCP.proxy_runtime import write_config_snapshot
from tzMCP.save_media import MediaSaver
from tzMCP.save_media_utils import config_provider, hash_tracker
from tzMCP.save_media_utils import save_media_utils as smu


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


def test_patched_brotli_decoder_is_loaded():
    assert Version(brotli.__version__) >= Version("1.2.1")


@pytest.mark.parametrize(
    "content", [b"", b"hello world", bytes(range(256)) * 256],
    ids=["empty", "text", "binary"],
)
def test_brotli_response_decodes_and_reencodes(content):
    compressed = brotli.compress(content)
    response = http.Response.make(200, compressed)
    response.headers["Content-Encoding"] = "br"
    assert response.content == content
    response.content = content + b"updated"
    assert brotli.decompress(response.raw_content) == content + b"updated"
    assert encoding.decode_brotli(encoding.encode_brotli(content)) == content


def test_brotli_chunked_image_is_saved_decoded(saver, make_flow, make_png):
    content = make_png(500, 500)
    flow = make_flow("http://site.com/pic.png", b"")
    flow.response = http.Response.make(200, brotli.compress(content))
    flow.response.headers["Content-Encoding"] = "br"
    # Chunked responses do not carry the compressed body's Content-Length.
    del flow.response.headers["Content-Length"]
    flow.response.headers["Transfer-Encoding"] = "chunked"
    saver.response(flow)
    assert [path.read_bytes() for path in _saved_files(saver)] == [content]


def test_truncated_brotli_response_is_rejected():
    compressed = brotli.compress(b"hello world" * 100)
    response = http.Response.make(200, compressed[:-1])
    response.headers["Content-Encoding"] = "br"
    with pytest.raises(ValueError):
        _ = response.content


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


@pytest.mark.parametrize("persistent", [False, True])
def test_failed_save_can_be_retried_after_space_is_freed(
    saver, make_flow, make_png, monkeypatch, tmp_path, persistent
):
    hash_tracker.init_hash_db(persist=persistent, db_path=tmp_path / "seen.sqlite")
    content = make_png(500, 500)
    original_replace = smu.os.replace

    def full_disk(*args, **kwargs):
        raise OSError(errno.ENOSPC, "No space left on device")

    try:
        monkeypatch.setattr(smu.os, "replace", full_disk)
        saver.response(make_flow("http://site.com/retry.png", content))
        assert _saved_files(saver) == []

        monkeypatch.setattr(smu.os, "replace", original_replace)
        saver.response(make_flow("http://site.com/retry.png", content))
        assert [p.read_bytes() for p in _saved_files(saver)] == [content]
        saver.response(make_flow("http://site.com/duplicate.png", content))
        assert len(_saved_files(saver)) == 1
    finally:
        hash_tracker.shutdown_hash_db()


def test_content_length_mismatch_is_skipped(saver, make_flow, make_png):
    flow = make_flow("http://site.com/pic.png", make_png(500, 500),
                     content_length="999999")
    saver.response(flow)
    assert _saved_files(saver) == []


def test_explicit_session_snapshot_controls_addon_without_changing_saved_config(
    tmp_path, monkeypatch, make_flow, make_png
):
    """The GUI/CLI launch snapshot is the config the real addon must use."""
    monkeypatch.setenv("TZMCP_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("TZMCP_AUTO_RELOAD", "0")

    persistent_path = tmp_path / "config" / "media_proxy_config.yaml"
    manager = ConfigManager(persistent_path)
    persistent_config = Config(save_dir=tmp_path / "persistent-captures")
    manager.save_config(persistent_config)
    persistent_before = persistent_path.read_bytes()

    session_config = Config(
        save_dir=tmp_path / "session-captures",
        allowed_mime_groups=["image"],
        whitelist=["allowed.example"],
        blacklist=[],
        filter_file_size={"enabled": True, "min_bytes": 0, "max_bytes": 10_000_000},
        filter_pixel_dimensions={
            "min_width": 1, "min_height": 1,
            "max_width": 10_000, "max_height": 10_000,
        },
        auto_reload_config=False,
    )
    snapshot = write_config_snapshot(session_config, tmp_path / "runtime")
    addon = MediaSaver(config_path=snapshot)

    addon.response(make_flow("http://img.allowed.example/pic.png", make_png(500, 500)))
    addon.response(make_flow("http://blocked.example/pic.png", make_png(500, 500)))

    assert [path.name for path in session_config.save_dir.iterdir()] == ["pic.png"]
    assert persistent_path.read_bytes() == persistent_before
