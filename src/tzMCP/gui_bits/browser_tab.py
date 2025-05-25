import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
import yaml
from tzMCP.gui_bits.browser_launcher import launch_browser, detect_browser_name

CONFIG_PATH = Path(__file__).parent.parent.parent / "config" / "browser_paths.yaml"

class BrowserTab(ttk.Frame):
    def __init__(self, master, proxy_controller):
        super().__init__(master)
        self.proxy_controller = proxy_controller

        self.browser_paths = self._load_browser_paths()
        self.display_names = {k: k for k in self.browser_paths}
        self.selected_browser = tk.StringVar()
        self.launch_url = tk.StringVar(value="http://mitm.it")
        self.use_incognito = tk.BooleanVar(value=False)

        self._build_widgets()

    def _build_widgets(self):
        row = 0

        ttk.Label(self, text="Select Browser:").grid(row=row, column=0, sticky="e")
        self.browser_menu = ttk.OptionMenu(self, self.selected_browser, None, *self.display_names.values())
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

        path_obj = Path(path)

        try:
            browser_name = detect_browser_name(path_obj)
        except ValueError:
            messagebox.showerror("Error", "Unsupported or unknown browser type.")
            return

        if path_obj.stem.lower() in {"iron", "firefoxportable", "braveportable"}:
            messagebox.showwarning(
                "Unsupported Wrapper",
                f"The selected binary ({path_obj.name}) may be a wrapper. Please choose the actual browser binary inside the application folder."
            )

        display_name = f"{browser_name} ({path_obj.name})"

        if browser_name in self.browser_paths:
            if not messagebox.askyesno("Overwrite?", f"A browser named '{browser_name}' already exists. Overwrite?"):
                return

        self.browser_paths[browser_name] = str(path_obj)
        self.display_names[browser_name] = display_name
        self._save_browser_paths()
        self._refresh_browser_menu()
        self.selected_browser.set(display_name)

    def _refresh_browser_menu(self):
        menu = self.browser_menu["menu"]  # type: ignore
        menu.delete(0, "end")
        for name, label in self.display_names.items():
            menu.add_command(label=label, command=lambda v=label: self.selected_browser.set(v))

    def _launch_browser(self):
        selected_label = self.selected_browser.get()
        # Reverse lookup the internal name
        internal_name = next((k for k, v in self.display_names.items() if v == selected_label), None)
        if not internal_name:
            messagebox.showerror("Error", f"Browser path not found for selection: {selected_label}")
            return

        path = self.browser_paths.get(internal_name)
        if not path:
            messagebox.showerror("Error", f"Browser path for '{internal_name}' not found.")
            return
        try:
            launch_browser(Path(path), self.launch_url.get(), self.proxy_controller.proxy_port, self.use_incognito.get())
        except Exception as e:
            messagebox.showerror("Launch Failed", str(e))
