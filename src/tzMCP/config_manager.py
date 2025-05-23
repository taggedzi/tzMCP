from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional
import yaml


@dataclass
class Config:
    save_dir: Path = Path("E:/Home/Documents/Programming/mitmproxy/cache/mitmproxy_media")
    extensions: List[str] = field(default_factory=lambda: [
        ".jpg", ".jpeg", ".png", ".gif", ".webp", ".mp4", ".webm", ".mov"
    ])
    whitelist: List[str] = field(default_factory=list)
    blacklist: List[str] = field(default_factory=lambda: ["ads\\..*", ".*\\.doubleclick\\.net"])
    filter_pixel_dimensions: Dict[str, Any] = field(default_factory=lambda: {
        "enabled": True,
        "min_width": 301,
        "min_height": 301,
        "max_width": 12000,
        "max_height": 12000
    })
    filter_file_size: Dict[str, Any] = field(default_factory=lambda: {
        "enabled": True,
        "min_bytes": 10240,
        "max_bytes": 157286400
    })
    log_seen_domains: bool = True
    auto_reload_config: bool = True


class ConfigManager:
    def __init__(self, config_path: Optional[Path] = None):
        """Initialize with optional config_path; defaults to project/config/media_proxy_config.yaml."""
        # Determine config path
        if config_path is None:
            base = Path(__file__).parent.parent.parent
            config_path = base / "config" / "media_proxy_config.yaml"
        self.config_path = config_path
        # Ensure config directory exists
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        # Initialize default config
        self.config = Config()

    def load_config(self) -> Config:
        """Load configuration from YAML file, overriding defaults if present."""
        if self.config_path.exists():
            with self.config_path.open("r", encoding="utf-8") as f:
                raw = yaml.safe_load(f) or {}
            if "save_dir" in raw:
                self.config.save_dir = Path(raw["save_dir"])
            if "extensions" in raw and isinstance(raw["extensions"], list):
                self.config.extensions = raw["extensions"]
            if "whitelist" in raw and isinstance(raw["whitelist"], list):
                self.config.whitelist = raw["whitelist"]
            if "blacklist" in raw and isinstance(raw["blacklist"], list):
                self.config.blacklist = raw["blacklist"]
            if "filter_pixel_dimensions" in raw and isinstance(raw["filter_pixel_dimensions"], dict):
                self.config.filter_pixel_dimensions = raw["filter_pixel_dimensions"]
            if "filter_file_size" in raw and isinstance(raw["filter_file_size"], dict):
                self.config.filter_file_size = raw["filter_file_size"]
            if "log_seen_domains" in raw:
                self.config.log_seen_domains = bool(raw["log_seen_domains"])
            if "auto_reload_config" in raw:
                self.config.auto_reload_config = bool(raw["auto_reload_config"])
        return self.config

    def save_config(self, config: Config = None) -> None:
        """Save the Config object to YAML file, creating parent dirs if necessary."""
        cfg = config or self.config
        data = asdict(cfg)
        data["save_dir"] = str(cfg.save_dir)
        # Ensure directory exists
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with self.config_path.open("w", encoding="utf-8") as f:
            yaml.safe_dump(data, f, sort_keys=False)
        self.config = cfg
