# log_config.py
import logging
from pathlib import Path
from tzMCP.save_media_utils.config_provider import get_config

# Preloaded global loggers
log_proxy = logging.getLogger("tzMCP.proxy")
log_browser = logging.getLogger("tzMCP.browser")
log_gui = logging.getLogger("tzMCP.gui")

def setup_logging():
    """
    Setup hierarchical logging for tzMCP components.
    Log files are hardcoded to 'logs/tzMCP_proxy.log', etc.
    Enable/disable file logging via config: config.log_to_file
    """
    config = get_config()
    enable_file = getattr(config, "log_to_file", False)

    log_dir = Path(__file__).parent.parent.parent.parent / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    logger_map = {
        log_proxy: log_dir / "tzMCP_proxy.log",
        log_browser: log_dir / "tzMCP_browser.log",
        log_gui: log_dir / "tzMCP_gui.log"
    }

    for logger, file_path in logger_map.items():
        logger.setLevel(logging.DEBUG)

        # Prevent duplicate handlers
        if logger.hasHandlers():
            logger.handlers.clear()

        formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s")

        # Console output
        ch = logging.StreamHandler()
        ch.setFormatter(formatter)
        logger.addHandler(ch)

        # Optional file output
        if enable_file:
            fh = logging.FileHandler(file_path, encoding="utf-8")
            fh.setFormatter(formatter)
            logger.addHandler(fh)

    return {
        "proxy": log_proxy,
        "browser": log_browser,
        "gui": log_gui,
    }
