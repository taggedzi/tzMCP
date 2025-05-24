# save_media_utilities/config_provider.py
_config_data = {}

def set_config(new_config: dict):
    global _config_data
    _config_data = new_config

def get_config() -> dict:
    return _config_data
