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
    # Validation filters through a set, so order is not preserved.
    assert set(validated.allowed_mime_groups) == {"image", "video"}


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
    assert set(reloaded.allowed_mime_groups) == {"image", "video"}
    assert reloaded.log_level == "ERROR"
