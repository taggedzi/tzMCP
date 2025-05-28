# 🛰️ tzMCP - Taggedz Media Capture Proxy

**tzMCP** is a GUI and CLI tool that uses [mitmproxy](https://mitmproxy.org/) to intercept and selectively save media from web traffic — including images, videos, HTML, CSS, JavaScript, and other downloadable files.

It is secure-by-default, lightweight, and designed to be cross-platform and user-friendly.

---

## ✨ Features

- ✅ **GUI with Tabbed Interface**
- 🕵️‍♂️ **Runs a MITM Proxy (mitmdump)**
- 📂 **Media filtering** by:
  - MIME group (e.g., `image`, `video`, `html`)
  - File size range
  - Pixel dimensions
  - Domain whitelists / blacklists
- 🧠 **Smart MIME detection** using byte scanning (not just Content-Type)
- 🧹 **Automatic cleanup** of expired logs and browser profiles
- 🔐 **Security-first**:
  - Directory traversal protection
  - Executable file type warnings
  - SHA256-based deduplication
- 💬 **Real-time log stream** to GUI (via internal log server)
- 🧪 Optional persistent deduplication (SQLite-backed)
- 🚀 Portable browser launcher with proxy preconfiguration

---

## 🖥️ GUI Overview

- **Proxy Control Tab**: Start/Stop mitmdump and view logs
- **Browser Launch Tab**: Manage and launch portable browsers
- **Configuration Tab**: Modify save filters, MIME groups, domain settings, and logging

---

## 🚀 Quick Start

### 1. Clone the repository

```bash
git clone https://github.com/taggedzi/tzMCP
cd tzmcp
````

### 2. Install dependencies (recommended inside a virtualenv)

```bash
pip install -r requirements.txt
```

> Or, if installing via PyPI (coming soon):
>
> ```bash
> pip install tzmcp
> ```

### 3. Launch the GUI

```bash
python -m tzMCP.gui
```

---

## ⚙️ Configuration

Located at: `config/media_proxy_config.yaml`

You can modify it via the GUI or manually.

### Example config snippet:

```yaml
save_dir: E:/Home/Documents/Programming/tzMCP/cache
allowed_mime_groups:
  - image
  - video
filter_pixel_dimensions:
  enabled: true
  min_width: 300
  min_height: 300
  max_width: 12000
  max_height: 12000
filter_file_size:
  enabled: true
  min_bytes: 10240         # 10KB
  max_bytes: 157286400     # 150MB
whitelist: []
blacklist:
  - ads\..*
  - .*\.doubleclick\.net
log_to_file: true
log_level: INFO
auto_reload_config: true
enable_persistent_dedup: false
```

---

## 🔧 CLI Support

CLI is supported. Here are the parameters for the CLI.

```bash
usage: tzMCP-cli [-h] [--config CONFIG] [--save-dir SAVE_DIR] [--mime-groups [MIME_GROUPS ...]]
                 [--whitelist [WHITELIST ...]] [--blacklist [BLACKLIST ...]] [--min-bytes MIN_BYTES]
                 [--max-bytes MAX_BYTES] [--min-width MIN_WIDTH] [--max-width MAX_WIDTH] [--min-height MIN_HEIGHT]
                 [--max-height MAX_HEIGHT] [--log-to-file] [--log-level {DEBUG,INFO,WARNING,ERROR,CRITICAL}] [--dedup]
                 [--no-auto-reload]

tzMCP CLI Media Capture Proxy

options:
  -h, --help            show this help message and exit
  --config CONFIG       Path to YAML config file
  --save-dir SAVE_DIR   Directory to save media files
  --mime-groups [MIME_GROUPS ...]
                        List of allowed MIME groups
  --whitelist [WHITELIST ...]
                        Domain whitelist (regex or substring)
  --blacklist [BLACKLIST ...]
                        Domain blacklist (regex or substring)
  --min-bytes MIN_BYTES
                        Minimum file size in bytes
  --max-bytes MAX_BYTES
                        Maximum file size in bytes
  --min-width MIN_WIDTH
                        Minimum image width
  --max-width MAX_WIDTH
                        Maximum image width
  --min-height MIN_HEIGHT
                        Minimum image height
  --max-height MAX_HEIGHT
                        Maximum image height
  --log-to-file         Enable file logging
  --log-level {DEBUG,INFO,WARNING,ERROR,CRITICAL}
                        Set log level
  --dedup               Enable persistent deduplication
  --no-auto-reload      Disable config auto-reload
```

---

## 🔒 Security Notes

* MIME detection uses both extension and byte-scanning (via `filetype`)
* File extensions are **never guessed**
* Executables are blocked unless explicitly allowed
* File names are sanitized to prevent directory traversal or reserved name collisions
* SHA256 deduplication prevents accidental overwrites or re-saves

---

## 📦 Packaging

When published on PyPI:

```bash
pip install tzmcp
tzmcp   # launch GUI (entry point)
```

### Project Metadata

* **Python version**: 3.8+
* **Platform**: Windows, Linux, macOS (via tkinter + mitmproxy)
* **License**: MIT
* **Dependencies**:

  * mitmproxy
  * Pillow
  * filetype
  * psutil
  * pyyaml
  * watchdog
  * requests

---

## 📁 Folder Layout

```
├── .github\
├── .gitignore
├── .pylintrc
├── .treeignore
├── cache\
├── config\
│   ├── browser_paths.yaml
│   └── media_proxy_config.yaml
├── docs\
├── LICENSE
├── pyproject.toml
├── README.md
├── requirements.txt
├── scripts\
│   ├── clean_unused_packages.py
│   └── tree_maker.py
├── src\
│   ├── config\
│   │   └── browser_paths.yaml
│   └── tzMCP\
│       ├── __init__.py
│       ├── browser_plugins\
│       │   ├── __init__.py
│       │   ├── brave.py
│       │   ├── chrome.py
│       │   ├── firefox.py
│       │   ├── iron.py
│       │   ├── kmeleon.py
│       │   ├── librewolf.py
│       │   ├── opera.py
│       │   ├── seamonkey.py
│       │   └── vivaldi.py
│       ├── cli.py
│       ├── common_utils\
│       │   ├── __init__.py
│       │   ├── cleanup_logs.py
│       │   ├── cleanup_profiles.py
│       │   └── log_config.py
│       ├── gui.py
│       ├── gui_bits\
│       │   ├── __init__.py
│       │   ├── app_constants.py
│       │   ├── browser_launcher.py
│       │   ├── browser_tab.py
│       │   ├── config_manager.py
│       │   ├── config_tab.py
│       │   ├── log_server.py
│       │   ├── proxy_control.py
│       │   ├── proxy_tab.py
│       │   └── status_bar.py
│       ├── save_media.py
│       └── save_media_utils\
│           ├── __init__.py
│           ├── config_provider.py
│           ├── gen_whitelist_regex.py
│           ├── hash_tracker.py
│           ├── mime_categories.py
│           ├── mime_data_minimal.py
│           └── save_media_utils.py
├── tasks.py
└── tests\
```

---

## 🧪 Testing (Coming Soon)

We're planning unit tests for:

* config validation
* MIME filters
* duplicate handling
* CLI interface

---

## 📝 License

MIT License. See `LICENSE` file for full text.

---

## 🙌 Acknowledgements

* Built on top of [mitmproxy](https://mitmproxy.org/)
* Inspired by the need for a safe, auditable web media capture tool

---

## Leagal:

Please understand and read the terms of this software before using it located they are located [here](./CYA_NOTICE.md)