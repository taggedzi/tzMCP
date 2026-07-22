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
