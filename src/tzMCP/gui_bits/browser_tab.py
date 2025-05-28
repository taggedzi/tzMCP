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
        # Frame: Browser Management
        mgmt_frame = ttk.LabelFrame(self, text="Manage Browsers")
        mgmt_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")

        ttk.Label(mgmt_frame, text="Selected:").grid(row=0, column=0, sticky="e", padx=5, pady=2)
        self.browser_menu = ttk.OptionMenu(mgmt_frame, self.selected_browser, None, *self.display_names.values())
        self.browser_menu.grid(row=0, column=1, sticky="ew", padx=5, pady=2)

        add_btn = ttk.Button(mgmt_frame, text="Add...", command=self._add_browser)
        add_btn.grid(row=0, column=2, padx=5)

        remove_btn = ttk.Button(mgmt_frame, text="Remove", command=self._remove_browser)
        remove_btn.grid(row=0, column=3, padx=5)

        mgmt_frame.columnconfigure(1, weight=1)

        # Frame: Launch Options
        launch_frame = ttk.LabelFrame(self, text="Launch Options")
        launch_frame.grid(row=1, column=0, padx=10, pady=10, sticky="ew")

        ttk.Label(launch_frame, text="Launch URL:").grid(row=0, column=0, sticky="e", padx=5, pady=2)
        ttk.Entry(launch_frame, textvariable=self.launch_url, width=40).grid(row=0, column=1, columnspan=2, sticky="ew", padx=5, pady=2)

        ttk.Checkbutton(launch_frame, text="Private / Incognito Mode", variable=self.use_incognito).grid(row=1, column=0, columnspan=3, sticky="w", padx=5, pady=2)

        launch_btn = ttk.Button(launch_frame, text="Launch Browser", command=self._launch_browser)
        launch_btn.grid(row=2, column=0, columnspan=3, pady=5)

        launch_frame.columnconfigure(1, weight=1)

        # Let main frame stretch with window
        self.columnconfigure(0, weight=1)

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

    def _remove_browser(self):
        selected_label = self.selected_browser.get()
        internal_name = next((k for k, v in self.display_names.items() if v == selected_label), None)

        if not internal_name:
            messagebox.showerror("Error", "No browser selected.")
            return

        if not messagebox.askyesno("Confirm Delete", f"Remove '{selected_label}' from browser list?"):
            return

        self.browser_paths.pop(internal_name, None)
        self.display_names.pop(internal_name, None)
        self._save_browser_paths()
        self._refresh_browser_menu()
        self.selected_browser.set("")

    def _refresh_browser_menu(self):
        menu = self.browser_menu["menu"]  # type: ignore
        menu.delete(0, "end")
        for name, label in self.display_names.items():
            menu.add_command(label=label, command=lambda v=label: self.selected_browser.set(v))

    def _launch_browser(self):
        selected_label = self.selected_browser.get()
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
