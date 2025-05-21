from mitmproxy import http
import os
import re
import yaml
import time
import threading
from pathlib import Path

CONFIG_PATH = "config.yaml"
DOMAINS_LOG_PATH = "domains_seen.txt"
CONFIG_POLL_INTERVAL = 5  # seconds

class MediaSaver:
    def __init__(self):
        self.load_config()
        if self.auto_reload_config:
            threading.Thread(target=self.watch_config, daemon=True).start()

    def load_config(self):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
        except Exception as e:
            print(f"[!] Failed to load config: {e}")
            config = {}

        self.save_dir = Path(config.get("save_dir", "mitmproxy_media"))
        self.extensions = set(ext.lower() for ext in config.get("extensions", []))
        self.whitelist = [re.compile(p) for p in config.get("whitelist", [])]
        self.blacklist = [re.compile(p) for p in config.get("blacklist", [])]
        self.log_seen_domains = config.get("log_seen_domains", True)
        self.auto_reload_config = config.get("auto_reload_config", False)
        self.last_config_time = os.path.getmtime(CONFIG_PATH)
        self.save_dir.mkdir(parents=True, exist_ok=True)
        self.seen_domains = set()
        print(f"[+] Media will be saved to: {self.save_dir}")

    def watch_config(self):
        print("[*] Watching config for changes...")
        while True:
            try:
                time.sleep(CONFIG_POLL_INTERVAL)
                new_time = os.path.getmtime(CONFIG_PATH)
                if new_time != self.last_config_time:
                    print("[~] Detected config.yaml change. Reloading...")
                    self.last_config_time = new_time
                    self.load_config()
            except Exception as e:
                print(f"[!] Error watching config file: {e}")

    def is_allowed_domain(self, domain):
        if any(p.search(domain) for p in self.blacklist):
            return False
        if not self.whitelist:
            return True
        return any(p.search(domain) for p in self.whitelist)

    def log_domain(self, domain):
        if not self.log_seen_domains:
            return
        if domain not in self.seen_domains:
            self.seen_domains.add(domain)
            print(f"[?] New domain seen: {domain}")
            try:
                with open(DOMAINS_LOG_PATH, "a", encoding="utf-8") as f:
                    f.write(domain + "\n")
            except Exception as e:
                print(f"[!] Failed to log domain: {e}")

    def response(self, flow: http.HTTPFlow):
        url = flow.request.pretty_url
        domain = flow.request.host
        ext = os.path.splitext(url.split("?")[0])[-1].lower()

        self.log_domain(domain)

        if ext not in self.extensions:
            return

        if not self.is_allowed_domain(domain):
            print(f"[-] Skipping {url} (domain filtered)")
            return

        filename = os.path.basename(url.split("/")[-1].split("?")[0])
        filepath = self.save_dir / filename

        try:
            with open(filepath, "wb") as f:
                f.write(flow.response.content)
            print(f"[+] Saved: {filepath}")
        except Exception as e:
            print(f"[!] Error saving {url} to {filepath}: {e}")

addons = [MediaSaver()]
