from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional
import yaml
from tzMCP.save_media_utils.mime_categories import MIME_GROUPS


@dataclass
class Config:
    save_dir: Path = Path("E:/Home/Documents/Programming/tzMCP/cache")
    allowed_mime_groups: list[str] = field(default_factory=list)
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
    log_to_file: bool = False
    log_level: str = "INFO"
    auto_reload_config: bool = True


class ConfigManager:
    def __init__(self, config_path: Optional[Path] = None):
        """Initialize with optional config_path; defaults to project/config/media_proxy_config.yaml."""
        self._log_fn = None  # Optional Logging hook
        # Determine config path
        if config_path is None:
            base = Path(__file__).parent.parent.parent.parent
            config_path = base / "config" / "media_proxy_config.yaml"
        self.config_path = config_path
        # Ensure config directory exists
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        # Initialize default config
        self.config = Config()

    def set_logger(self, log_fn):
        """Optional: set a logger function for GUI/system logs."""
        self._log_fn = log_fn

    def _validate_config(self, config: Config) -> Config:
        # Ensure save_dir is absolute and writable
        if not config.save_dir.is_absolute():
            config.save_dir = config.save_dir.resolve()
        try:
            config.save_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            raise ValueError(f"Invalid save_dir: {config.save_dir} ({e})")

        # Validate MIME groups
        before = set(config.allowed_mime_groups)
        config.allowed_mime_groups = [g for g in before if g in MIME_GROUPS]
        dropped = before - set(config.allowed_mime_groups)
        if dropped:
            msg = f"Ignored invalid MIME groups in config: {', '.join(sorted(dropped))}"
            print(f"[WARNING] {msg}")
            if self._log_fn:
                self._log_fn("warn", "orange", msg)

        # Check file size bounds
        ffs = config.filter_file_size
        ffs["min_bytes"] = max(0, ffs.get("min_bytes", 0))
        ffs["max_bytes"] = max(ffs["min_bytes"], ffs.get("max_bytes", 1))

        # Check pixel dimension bounds
        fpd = config.filter_pixel_dimensions
        for key in ["min_width", "min_height", "max_width", "max_height"]:
            fpd[key] = max(0, fpd.get(key, 0))
        fpd["max_width"] = max(fpd["min_width"], fpd["max_width"])
        fpd["max_height"] = max(fpd["min_height"], fpd["max_height"])

        return config

    def load_config(self) -> Config:
        """Load configuration from YAML file, overriding defaults if present."""
        if self.config_path.exists():
            with self.config_path.open("r", encoding="utf-8") as f:
                raw = yaml.safe_load(f) or {}
            if "save_dir" in raw:
                self.config.save_dir = Path(raw["save_dir"])
            if "allowed_mime_groups" in raw and isinstance(raw["allowed_mime_groups"], list):
                self.config.allowed_mime_groups = raw["allowed_mime_groups"]
            if "whitelist" in raw and isinstance(raw["whitelist"], list):
                self.config.whitelist = raw["whitelist"]
            if "blacklist" in raw and isinstance(raw["blacklist"], list):
                self.config.blacklist = raw["blacklist"]
            if "filter_pixel_dimensions" in raw and isinstance(raw["filter_pixel_dimensions"], dict):
                self.config.filter_pixel_dimensions = raw["filter_pixel_dimensions"]
            if "filter_file_size" in raw and isinstance(raw["filter_file_size"], dict):
                self.config.filter_file_size = raw["filter_file_size"]
            if "log_to_file" in raw:
                self.config.log_to_file = bool(raw["log_to_file"])
            if "log_internal_debug" in raw:
                self.config.log_internal_debug = bool(raw["log_internal_debug"])
            if "log_seen_domains" in raw:
                self.config.log_seen_domains = bool(raw["log_seen_domains"])
            if "auto_reload_config" in raw:
                self.config.auto_reload_config = bool(raw["auto_reload_config"])
        self.config = self._validate_config(self.config)
        return self.config

    def save_config(self, config: Config = None) -> None:
        """Save the Config object to YAML file, creating parent dirs if necessary."""
        cfg = config or self.config
        self._validate_config(cfg)
        data = asdict(cfg)
        data["save_dir"] = str(cfg.save_dir)
        # Ensure directory exists
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with self.config_path.open("w", encoding="utf-8") as f:
            yaml.safe_dump(data, f, sort_keys=False)
        self.config = cfg
