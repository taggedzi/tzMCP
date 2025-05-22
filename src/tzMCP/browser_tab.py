import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path

from tzMCP.browser_launcher import launch_browser, LAUNCH_COMMANDS
from tzMCP.proxy_control import ProxyController


class BrowserTab(ttk.Frame):
    """Tab for launching browsers through the proxy."""
    def __init__(self, parent, proxy_controller: ProxyController):
        super().__init__(parent)
        self.proxy_controller = proxy_controller
        self._build_ui()

    def _build_ui(self):
        ttk.Label(self, text="Browser:").grid(row=0, column=0, padx=5, pady=5)
        self.browser_var = tk.StringVar()
        browsers = list(LAUNCH_COMMANDS.keys())
        self.browser_combo = ttk.Combobox(self, textvariable=self.browser_var, values=browsers, state='readonly')
        if browsers:
            self.browser_combo.current(0)
        self.browser_combo.grid(row=0, column=1, sticky='ew')

        ttk.Label(self, text="URL:").grid(row=1, column=0, padx=5, pady=5)
        self.url_var = tk.StringVar(value="http://mitm.it")
        ttk.Entry(self, textvariable=self.url_var).grid(row=1, column=1, columnspan=2, sticky='ew')

        ttk.Label(self, text="Profile Dir:").grid(row=2, column=0, padx=5, pady=5)
        self.profile_var = tk.StringVar()
        ttk.Entry(self, textvariable=self.profile_var).grid(row=2, column=1, sticky='ew')
        ttk.Button(self, text="Browse...", command=self._browse).grid(row=2, column=2)

        ttk.Button(self, text="Launch", command=self._launch).grid(row=3, column=0, columnspan=3, pady=10)

        for i in range(3):
            self.columnconfigure(i, weight=1)

    def _browse(self):
        path = filedialog.askdirectory()
        if path:
            self.profile_var.set(path)

    def _launch(self):
        try:
            launch_browser(
                self.browser_var.get(),
                self.url_var.get(),
                proxy_port=self.proxy_controller.proxy_port,
                user_data_dir=Path(self.profile_var.get()) if self.profile_var.get() else None
            )
        except Exception as e:
            messagebox.showerror("Error", f"{e}")
