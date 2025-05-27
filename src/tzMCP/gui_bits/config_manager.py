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
    enable_persistent_dedup: bool = False
    auto_reload_config: bool = True


class ConfigManager:
    def __init__(self, config_path: Optional[Path] = None):
        if config_path is None:
            base = Path(__file__).parent.parent.parent.parent
            config_path = base / "config" / "media_proxy_config.yaml"
        self.config_path = config_path
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        self._log_fn = None
        self.config = Config()

    def set_logger(self, log_fn):
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

        # File size sanity checks
        ffs = config.filter_file_size
        ffs["min_bytes"] = max(0, ffs.get("min_bytes", 0))
        ffs["max_bytes"] = max(ffs["min_bytes"], ffs.get("max_bytes", 1))

        # Pixel dimensions sanity
        fpd = config.filter_pixel_dimensions
        for key in ["min_width", "min_height", "max_width", "max_height"]:
            fpd[key] = max(0, fpd.get(key, 0))
        fpd["max_width"] = max(fpd["min_width"], fpd["max_width"])
        fpd["max_height"] = max(fpd["min_height"], fpd["max_height"])

        # Log level normalization
        config.log_level = config.log_level.upper()
        if config.log_level not in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
            config.log_level = "INFO"

        return config

    def load_config(self) -> Config:
        if self.config_path.exists():
            with self.config_path.open("r", encoding="utf-8") as f:
                raw = yaml.safe_load(f) or {}
            for key in asdict(self.config):
                if key in raw:
                    value = raw[key]
                    if key == "save_dir":
                        self.config.save_dir = Path(value)
                    else:
                        setattr(self.config, key, value)
        self.config = self._validate_config(self.config)
        return self.config

    def save_config(self, config: Config = None) -> None:
        cfg = config or self.config
        self._validate_config(cfg)
        data = asdict(cfg)
        data["save_dir"] = str(cfg.save_dir)
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with self.config_path.open("w", encoding="utf-8") as f:
            yaml.safe_dump(data, f, sort_keys=False)
        self.config = cfg
