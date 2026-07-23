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
