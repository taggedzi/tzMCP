import argparse
import sys
import yaml
from pathlib import Path
from tzMCP.gui_bits.config_manager import ConfigManager, Config

def parse_args():
    parser = argparse.ArgumentParser(description="tzMCP CLI Media Proxy")

    parser.add_argument('--config', type=str, help='Path to YAML config file')

    # Explicit overrides (match config fields)
    parser.add_argument('--save-dir', type=str, help='Directory to save media files')
    parser.add_argument('--mime-groups', nargs='*', help='List of allowed MIME groups')
    parser.add_argument('--whitelist', nargs='*', help='Domain whitelist (regex or substring)')
    parser.add_argument('--blacklist', nargs='*', help='Domain blacklist (regex or substring)')
    parser.add_argument('--min-bytes', type=int, help='Minimum file size in bytes')
    parser.add_argument('--max-bytes', type=int, help='Maximum file size in bytes')
    parser.add_argument('--min-width', type=int, help='Minimum image width')
    parser.add_argument('--max-width', type=int, help='Maximum image width')
    parser.add_argument('--min-height', type=int, help='Minimum image height')
    parser.add_argument('--max-height', type=int, help='Maximum image height')
    parser.add_argument('--log-to-file', action='store_true', help='Enable file logging')
    parser.add_argument('--log-level', type=str, choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], help='Set log level')
    parser.add_argument('--dedup', action='store_true', help='Enable persistent deduplication')
    parser.add_argument('--no-auto-reload', dest='auto_reload', action='store_false', help='Disable config auto-reload')

    return parser.parse_args()

def build_config(args) -> Config:
    # Load config file if provided
    config_file = Path(args.config).resolve() if args.config else None
    cfg_mgr = ConfigManager(config_file)
    config = cfg_mgr.load_config()

    # Override with command-line arguments if present
    if args.save_dir:
        config.save_dir = Path(args.save_dir).resolve()
    if args.mime_groups:
        config.allowed_mime_groups = args.mime_groups
    if args.whitelist:
        config.whitelist = args.whitelist
    if args.blacklist:
        config.blacklist = args.blacklist
    if args.min_bytes is not None:
        config.filter_file_size["min_bytes"] = args.min_bytes
    if args.max_bytes is not None:
        config.filter_file_size["max_bytes"] = args.max_bytes
    if args.min_width is not None:
        config.filter_pixel_dimensions["min_width"] = args.min_width
    if args.max_width is not None:
        config.filter_pixel_dimensions["max_width"] = args.max_width
    if args.min_height is not None:
        config.filter_pixel_dimensions["min_height"] = args.min_height
    if args.max_height is not None:
        config.filter_pixel_dimensions["max_height"] = args.max_height
    if args.log_to_file:
        config.log_to_file = True
    if args.log_level:
        config.log_level = args.log_level
    if args.dedup:
        config.enable_persistent_dedup = True
    if args.auto_reload is not None:
        config.auto_reload_config = args.auto_reload

    return config

def main():
    args = parse_args()
    config = build_config(args)

    # OPTIONAL: save resolved config if you want to persist merged settings
    ConfigManager().save_config(config)

    # Set it globally for utilities that call get_config()
    from tzMCP.save_media_utils import config_provider
    config_provider.set_config(config)

    # Start mitmdump with this config
    from tzMCP.save_media import MediaSaver
    from mitmproxy.tools.main import mitmdump
    # This will behave like mitmproxy's -s entry point:
    mitmdump(["-s", str(Path(__file__).parent / "save_media.py")])

if __name__ == "__main__":
    main()