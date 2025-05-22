import tkinter as tk
from tkinter import ttk, messagebox
from tkinter.scrolledtext import ScrolledText
import subprocess
import threading
import os
import signal
import socket
import atexit
import yaml
import re
import platform

CONFIG_FILE = "config.yaml"
DOMAINS_FILE = "domains_seen.txt"
BROWSER_PATHS_FILE = "browser_paths.yaml"
MAX_LOG_LINES = 2000  # Maximum number of lines in the console output
PROXY_PORT = 8080      # Default port for mitmdump


class ProxyControlTab(ttk.Frame):
    def __init__(self, parent, status_callback):
        super().__init__(parent)
        self.proc = None
        self.status_callback = status_callback
        self.browser_paths = self.load_browser_paths()

        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        self.toggle_btn = ttk.Button(self, text="Start Proxy", command=self.toggle_proxy)
        self.toggle_btn.grid(row=0, column=0, pady=10, sticky="ew")

        self.output = ScrolledText(self, wrap=tk.WORD)
        self.output.configure(state="disabled")
        self.output.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")

        self.setup_tags()

        # Browser launch button frame with Safari for macOS
        browser_frame = ttk.LabelFrame(self, text="Launch Browser with Proxy")
        browser_frame.grid(row=2, column=0, padx=10, pady=(0, 10), sticky="ew")

        ttk.Button(browser_frame, text="Launch Chrome", command=self.launch_chrome).pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Button(browser_frame, text="Launch Firefox", command=self.launch_firefox).pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Button(browser_frame, text="Launch Brave", command=self.launch_brave).pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Button(browser_frame, text="Launch Safari", command=self.launch_safari).pack(side=tk.LEFT, padx=5, pady=5)

    def load_browser_paths(self):
        default_paths = {
            "chrome": r"C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
            "firefox": r"C:\\Program Files\\Mozilla Firefox\\firefox.exe",
            "brave": r"C:\\Program Files\\BraveSoftware\\Brave-Browser\\Application\\brave.exe",
            "safari": "/Applications/Safari.app"
        }
        try:
            if os.path.exists(BROWSER_PATHS_FILE):
                with open(BROWSER_PATHS_FILE, "r", encoding="utf-8") as f:
                    user_paths = yaml.safe_load(f) or {}
                    default_paths.update(user_paths)
        except Exception as e:
            self.insert_output_line(f"[!] Failed to load browser paths: {e}\n")
        return default_paths

    def is_port_in_use(self, port):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(("127.0.0.1", port)) == 0

    def toggle_proxy(self):
        if self.proc is None:
            self.start_proxy()
        else:
            self.stop_proxy()

    def start_proxy(self):
        if self.is_port_in_use(PROXY_PORT):
            self.insert_output_line(f"[!] Port {PROXY_PORT} is already in use. Cannot start proxy.\n")
            self.status_callback("Port Conflict", "orange")
            return

        script = os.path.abspath("save_media.py")
        self.proc = subprocess.Popen(
            ["mitmdump", "--listen-port", str(PROXY_PORT), "-s", script],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        self.toggle_btn.config(text="Stop Proxy")
        self.status_callback("Proxy Running", "green")
        threading.Thread(target=self.read_output, daemon=True).start()

    def stop_proxy(self):
        if self.proc:
            self.proc.terminate()
            self.proc = None
            self.toggle_btn.config(text="Start Proxy")
            self.status_callback("Proxy Stopped", "red")
            self.insert_output_line("[!] Proxy stopped.\n")

    def read_output(self):
        for line in self.proc.stdout:
            self.insert_output_line(line)
        self.proc = None
        self.toggle_btn.config(text="Start Proxy")
        self.status_callback("Proxy Exited", "orange")

    def write_output(self, text, tag=None):
        self.output.configure(state="normal")
        if tag:
            self.output.insert(tk.END, text, tag)
        else:
            self.output.insert(tk.END, text)

        # Trim lines if over MAX_LOG_LINES
        lines = int(self.output.index('end-1c').split('.')[0])
        if lines > MAX_LOG_LINES:
            self.output.delete("1.0", f"{lines - MAX_LOG_LINES + 1}.0")

        self.output.see(tk.END)
        self.output.configure(state="disabled")

    def setup_tags(self):
        self.output.tag_config("info", foreground="green")
        self.output.tag_config("warning", foreground="orange")
        self.output.tag_config("error", foreground="red")
        self.output.tag_config("debug", foreground="blue")

    def launch_chrome(self):
        path = self.browser_paths.get("chrome")
        if path and os.path.exists(path):
            subprocess.Popen([path, f"--proxy-server=127.0.0.1:{PROXY_PORT}", "--new-window", "http://mitm.it"])
            self.insert_output_line(f"[+] Launched Chrome with proxy on port {PROXY_PORT}\n")
        else:
            self.insert_output_line("[!] Chrome not found at configured path.\n")

    def launch_firefox(self):
        path = self.browser_paths.get("firefox")
        if path and os.path.exists(path):
            subprocess.Popen([path, "-new-window", "http://mitm.it"])
            self.insert_output_line("[+] Launched Firefox (manual proxy configuration may be needed).\n")
        else:
            self.insert_output_line("[!] Firefox not found at configured path.\n")

    def launch_brave(self):
        path = self.browser_paths.get("brave")
        if path and os.path.exists(path):
            subprocess.Popen([path, f"--proxy-server=127.0.0.1:{PROXY_PORT}", "--new-window", "http://mitm.it"])
            self.insert_output_line(f"[+] Launched Brave with proxy on port {PROXY_PORT}\n")
        else:
            self.insert_output_line("[!] Brave not found at configured path.\n")

    def launch_safari(self):
        if platform.system().lower() == "darwin":
            try:
                subprocess.Popen([
                    "open", "-a", "Safari", "--args", "http://mitm.it"
                ])
                self.insert_output_line("[+] Launched Safari (system proxy must be pre-configured).\n")
            except Exception as e:
                self.insert_output_line(f"[!] Failed to launch Safari: {e}\n")
        else:
            self.insert_output_line("[!] Safari launch is only supported on macOS.\n")

    def insert_output_line(self, text):
        if "[!]" in text:
            self.write_output(text, "warning")
        elif "[+]" in text:
            self.write_output(text, "info")
        elif "[-]" in text:
            self.write_output(text, "debug")
        else:
            self.write_output(text)


class ConfigEditorTab(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)

        self.text = ScrolledText(self, height=30, width=100)
        self.text.pack(padx=10, pady=10, expand=True, fill=tk.BOTH)

        btn_frame = ttk.Frame(self)
        btn_frame.pack(pady=5)

        ttk.Button(btn_frame, text="Load", command=self.load_config).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Save", command=self.save_config).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Reset", command=self.reset_config).pack(side=tk.LEFT, padx=5)

        self.load_config()

    def load_config(self):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                content = f.read()
                self.text.delete(1.0, tk.END)
                self.text.insert(tk.END, content)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load config: {e}")

    def save_config(self):
        try:
            content = self.text.get(1.0, tk.END)
            yaml.safe_load(content)
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                f.write(content)
            messagebox.showinfo("Success", "Config saved successfully.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save config: {e}")

    def reset_config(self):
        self.load_config()


class DomainViewerTab(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.domains = []

        self.listbox = tk.Listbox(self, height=20, width=80)
        self.listbox.pack(padx=10, pady=5, fill=tk.BOTH, expand=True)

        self.regex_label = tk.Label(self, text="Suggested Regex:", anchor="w")
        self.regex_label.pack(fill=tk.X, padx=10)

        self.regex_entry = tk.Entry(self, width=100)
        self.regex_entry.pack(padx=10, pady=(0, 10), fill=tk.X)

        btn_frame = ttk.Frame(self)
        btn_frame.pack(pady=5)

        ttk.Button(btn_frame, text="Copy to Clipboard", command=self.copy_to_clipboard).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Refresh", command=self.load_domains).pack(side=tk.LEFT, padx=5)

        self.listbox.bind("<<ListboxSelect>>", self.on_select)
        self.load_domains()

    def load_domains(self):
        self.listbox.delete(0, tk.END)
        self.domains = []
        try:
            with open(DOMAINS_FILE, "r", encoding="utf-8") as f:
                seen = set()
                for line in f:
                    domain = line.strip()
                    if domain and domain not in seen:
                        seen.add(domain)
                        self.domains.append(domain)
                        self.listbox.insert(tk.END, domain)
        except FileNotFoundError:
            messagebox.showwarning("No Data", f"{DOMAINS_FILE} not found.")

    def on_select(self, event):
        selection = event.widget.curselection()
        if selection:
            index = selection[0]
            domain = self.domains[index]
            regex = self.smart_regex(domain)
            self.regex_entry.delete(0, tk.END)
            self.regex_entry.insert(0, regex)

    def smart_regex(self, domain):
        parts = domain.split('.')
        if len(parts) >= 3:
            domain_core = '.'.join(parts[-2:])
            subdomain = parts[0]
            if re.match(r'^[a-zA-Z\-]*\d+[a-zA-Z\-]*$', subdomain):
                sub_regex = re.sub(r'\d+', r'[0-9]+', subdomain)
                return f"{re.escape(sub_regex)}\\.{re.escape(domain_core)}"
            else:
                return f".*\\.{re.escape(domain_core)}"
        return re.escape(domain)

    def copy_to_clipboard(self):
        regex = self.regex_entry.get()
        self.clipboard_clear()
        self.clipboard_append(regex)
        messagebox.showinfo("Copied", "Regex copied to clipboard.")


class MainApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Media Capture Proxy")

        self.tabs = ttk.Notebook(self)
        self.tabs.pack(expand=1, fill="both")

        self.status_bar = tk.Label(self, text="Status: Idle", bg="grey", fg="white")
        self.status_bar.pack(fill=tk.X, side=tk.BOTTOM)

        self.proxy_tab = ProxyControlTab(self.tabs, self.update_status)
        atexit.register(self.proxy_tab.stop_proxy)
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        self.config_tab = ConfigEditorTab(self.tabs)
        self.domains_tab = DomainViewerTab(self.tabs)

        self.tabs.add(self.proxy_tab, text="Proxy Control")
        self.tabs.add(self.config_tab, text="Config Editor")
        self.tabs.add(self.domains_tab, text="Domain Viewer")

    def update_status(self, message, color):
        self.status_bar.config(text=f"Status: {message}", bg=color)

    def on_close(self):
        self.proxy_tab.stop_proxy()
        self.destroy()


def main():
    app = MainApp()
    app.mainloop()
