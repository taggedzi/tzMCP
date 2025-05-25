import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
import yaml
from tzMCP.gui_bits.browser_launcher import launch_browser

CONFIG_PATH = Path(__file__).parent.parent.parent / "config" / "browser_paths.yaml"

class BrowserTab(ttk.Frame):
    def __init__(self, master, proxy_controller):
        super().__init__(master)
        self.proxy_controller = proxy_controller

        self.browser_paths = self._load_browser_paths()
        self.selected_browser = tk.StringVar()
        self.launch_url = tk.StringVar(value="http://mitm.it")
        self.use_incognito = tk.BooleanVar(value=False)

        self._build_widgets()

    def _build_widgets(self):
        row = 0

        ttk.Label(self, text="Select Browser:").grid(row=row, column=0, sticky="e")
        self.browser_menu = ttk.OptionMenu(self, self.selected_browser, None, *self.browser_paths.keys())
        self.browser_menu.grid(row=row, column=1, sticky="ew")

        row += 1
        ttk.Label(self, text="Launch URL:").grid(row=row, column=0, sticky="e")
        ttk.Entry(self, textvariable=self.launch_url, width=40).grid(row=row, column=1, sticky="ew")

        row += 1
        ttk.Checkbutton(self, text="Private / Incognito Mode", variable=self.use_incognito).grid(row=row, columnspan=2, sticky="w")

        row += 1
        ttk.Button(self, text="Launch Browser", command=self._launch_browser).grid(row=row, columnspan=2, pady=5)

        row += 1
        ttk.Button(self, text="Add Portable Browser...", command=self._add_browser).grid(row=row, columnspan=2)

        self.columnconfigure(1, weight=1)

    def _load_browser_paths(self):
        if CONFIG_PATH.exists():
            with CONFIG_PATH.open("r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        return {}

    def _save_browser_paths(self):
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with CONFIG_PATH.open("w", encoding="utf-8") as f:
            yaml.safe_dump(self.browser_paths, f)

    def _add_browser(self):
        path = filedialog.askopenfilename(title="Select Browser Executable")
        if not path:
            return
        name = Path(path).stem.lower()
        if name in self.browser_paths:
            if not messagebox.askyesno("Overwrite?", f"A browser named '{name}' already exists. Overwrite?"):
                return
        self.browser_paths[name] = path
        self._save_browser_paths()
        self._refresh_browser_menu()
        self.selected_browser.set(name)

    def _refresh_browser_menu(self):
        menu = self.browser_menu["menu"]
        menu.delete(0, "end")  # pylint: disable=no-member
        for name in self.browser_paths:
            menu.add_command(label=name, command=lambda v=name: self.selected_browser.set(v))  # pylint: disable=no-member

    def _launch_browser(self):
        name = self.selected_browser.get()
        path = self.browser_paths.get(name)
        if not path:
            messagebox.showerror("Error", f"Browser path for '{name}' not found.")
            return
        try:
            launch_browser(Path(path), self.launch_url.get(), self.proxy_controller.proxy_port, self.use_incognito.get())
        except Exception as e:
            messagebox.showerror("Launch Failed", str(e))
