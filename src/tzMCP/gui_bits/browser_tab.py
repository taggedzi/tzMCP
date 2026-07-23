import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
import yaml
from tzMCP.gui_bits.browser_launcher import launch_browser, detect_browser_name
from tzMCP.paths import config_dir
from tzMCP.common_utils.log_config import log_gui

CONFIG_PATH = config_dir() / "browser_paths.yaml"

class BrowserTab(ttk.Frame):
    """Guided, safety-first capture session setup and browser launcher."""
    def __init__(self, master, proxy_controller, status_bar=None, activity_logger=None):
        super().__init__(master)
        self.proxy_controller = proxy_controller
        self.status_bar = status_bar
        self.activity_logger = activity_logger

        self.browser_paths = self._load_browser_paths()
        self.display_names = {k: k for k in self.browser_paths}
        self.selected_browser = tk.StringVar()
        self.launch_url = tk.StringVar(value="http://mitm.it")
        self.use_incognito = tk.BooleanVar(value=False)
        self.safe_browser_acknowledged = tk.BooleanVar(value=False)

        self._build_widgets()

    def _build_widgets(self):
        intro = ttk.Frame(self, padding=(18, 16, 18, 8))
        intro.grid(row=0, column=0, sticky="ew")
        ttk.Label(intro, text="Capture session", style="Title.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(
            intro,
            text="Start the local proxy, then launch an isolated browser prepared for capture.",
            style="Subtitle.TLabel",
        ).grid(row=1, column=0, sticky="w", pady=(3, 0))

        warning = tk.Label(
            self,
            text=("Safety notice: tzMCP decrypts web traffic through mitmproxy. Do not enter passwords, "
                  "payment details, or other sensitive credentials while capturing. Use a dedicated portable "
                  "browser only—using an installed everyday browser can damage or lock its normal profile."),
            background="#fff3cd", foreground="#5f4300", justify="left", anchor="w", wraplength=760,
            padx=12, pady=10,
        )
        warning.grid(row=1, column=0, padx=18, pady=(4, 10), sticky="ew")

        proxy_frame = ttk.LabelFrame(self, text="1. Start capture proxy", padding=12)
        proxy_frame.grid(row=2, column=0, padx=18, pady=6, sticky="ew")
        self.proxy_state = ttk.Label(proxy_frame, text="Stopped — start this before launching a browser.")
        self.proxy_state.grid(row=0, column=0, sticky="w")
        self.start_btn = ttk.Button(proxy_frame, text="Start proxy", command=self._start_proxy, style="Accent.TButton")
        self.start_btn.grid(row=0, column=1, padx=(16, 6))
        self.stop_btn = ttk.Button(proxy_frame, text="Stop", command=self._stop_proxy, state="disabled")
        self.stop_btn.grid(row=0, column=2)
        proxy_frame.columnconfigure(0, weight=1)

        # Browser management
        mgmt_frame = ttk.LabelFrame(self, text="2. Choose a dedicated portable browser", padding=12)
        mgmt_frame.grid(row=3, column=0, padx=18, pady=6, sticky="ew")

        ttk.Label(mgmt_frame, text="Selected:").grid(row=0, column=0, sticky="e", padx=5, pady=2)
        self.browser_menu = ttk.OptionMenu(mgmt_frame, self.selected_browser, None, *self.display_names.values())
        self.browser_menu.grid(row=0, column=1, sticky="ew", padx=5, pady=2)

        add_btn = ttk.Button(mgmt_frame, text="Add...", command=self._add_browser)
        add_btn.grid(row=0, column=2, padx=5)

        remove_btn = ttk.Button(mgmt_frame, text="Remove", command=self._remove_browser)
        remove_btn.grid(row=0, column=3, padx=5)

        mgmt_frame.columnconfigure(1, weight=1)

        # Launch options
        launch_frame = ttk.LabelFrame(self, text="3. Launch browser", padding=12)
        launch_frame.grid(row=4, column=0, padx=18, pady=6, sticky="ew")

        ttk.Label(launch_frame, text="Launch URL:").grid(row=0, column=0, sticky="e", padx=5, pady=2)
        ttk.Entry(launch_frame, textvariable=self.launch_url, width=40).grid(row=0, column=1, columnspan=2, sticky="ew", padx=5, pady=2)

        ttk.Checkbutton(launch_frame, text="Private / Incognito Mode", variable=self.use_incognito).grid(row=1, column=0, columnspan=3, sticky="w", padx=5, pady=2)

        acknowledge = ttk.Checkbutton(
            launch_frame,
            text="I confirm this is a dedicated portable browser, not my everyday installed browser.",
            variable=self.safe_browser_acknowledged,
            command=self._update_launch_state,
        )
        acknowledge.grid(row=2, column=0, columnspan=3, sticky="w", padx=5, pady=(7, 2))

        self.launch_btn = ttk.Button(launch_frame, text="Launch safe browser", command=self._launch_browser, state="disabled", style="Accent.TButton")
        self.launch_btn.grid(row=3, column=0, columnspan=3, pady=(8, 2))

        launch_frame.columnconfigure(1, weight=1)

        # Let main frame stretch with window
        self.columnconfigure(0, weight=1)

    def _append_activity(self, line, color="blue"):
        if self.activity_logger:
            self.activity_logger({"color": color, "lines": [line]})

    def _start_proxy(self):
        try:
            self.proxy_controller.start_proxy()
            self.start_btn.config(state="disabled")
            self.stop_btn.config(state="normal")
            self.proxy_state.config(text=f"Running on 127.0.0.1:{self.proxy_controller.proxy_port}")
            if self.status_bar:
                self.status_bar.set_state("running")
            self._append_activity("Proxy started successfully.")
            self._update_launch_state()
        except Exception as exc:  # pylint: disable=broad-exception-caught
            log_gui.exception("Could not start the capture proxy.")
            self.proxy_state.config(text=f"Could not start proxy: {exc}")
            if self.status_bar:
                self.status_bar.set_state("error")
            self._append_activity(f"Error starting proxy: {exc}", "red")

    def _stop_proxy(self):
        try:
            self.proxy_controller.stop_proxy()
            self.start_btn.config(state="normal")
            self.stop_btn.config(state="disabled")
            self.proxy_state.config(text="Stopped — start this before launching a browser.")
            if self.status_bar:
                self.status_bar.set_state("stopped")
            self._append_activity("Proxy stopped successfully.")
            self._update_launch_state()
        except Exception as exc:  # pylint: disable=broad-exception-caught
            log_gui.exception("Could not stop the capture proxy.")
            self._append_activity(f"Failed to stop proxy: {exc}", "red")

    def _update_launch_state(self):
        proxy_running = self.proxy_controller.process is not None and self.proxy_controller.process.poll() is None
        self.launch_btn.config(state="normal" if self.safe_browser_acknowledged.get() and proxy_running else "disabled")

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
        if not messagebox.askyesno(
            "Use a portable browser",
            "Only add an executable from a dedicated portable browser installation.\n\n"
            "tzMCP uses a separate capture profile, but launching an everyday installed browser can still "
            "interfere with or change its normal profile. Continue only if this is a portable browser.",
        ):
            return
        path = filedialog.askopenfilename(title="Select Browser Executable")
        if not path:
            return

        path_obj = Path(path)

        try:
            browser_name = detect_browser_name(path_obj)
        except ValueError:
            log_gui.warning(
                "Unsupported browser selected: %s. Choose a supported browser executable "
                "(Chrome, Firefox, Brave, Opera, Vivaldi, Iron, K-Meleon, LibreWolf, or SeaMonkey).",
                path_obj,
            )
            messagebox.showerror("Error", "Unsupported or unknown browser type.")
            return

        if path_obj.stem.lower() in {"iron", "firefoxportable", "braveportable"}:
            log_gui.warning(
                "Selected browser binary may be a wrapper: %s. Choose the browser executable "
                "inside the application folder if launching fails.",
                path_obj,
            )
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
        self._update_launch_state()
        if self.launch_btn.cget("state") == "disabled":
            messagebox.showwarning(
                "Complete the capture session",
                "Start the proxy and confirm that you are using a dedicated portable browser before launching.",
            )
            return
        selected_label = self.selected_browser.get()
        internal_name = next((k for k, v in self.display_names.items() if v == selected_label), None)
        if not internal_name:
            log_gui.warning("Browser launch requested without a selected configured browser.")
            messagebox.showerror("Error", f"Browser path not found for selection: {selected_label}")
            return

        path = self.browser_paths.get(internal_name)
        if not path:
            log_gui.warning(
                "Configured browser entry %r has no executable path. Remove or re-add it "
                "in the Browser Launch tab.",
                internal_name,
            )
            messagebox.showerror("Error", f"Browser path for '{internal_name}' not found.")
            return
        try:
            launch_browser(Path(path), self.launch_url.get(), self.proxy_controller.proxy_port, self.use_incognito.get())
            self._append_activity(f"Launched isolated {internal_name} browser session.")
        except Exception as e:
            log_gui.exception(
                "Could not launch the browser. Confirm that its executable still exists and "
                "is allowed to start, then retry."
            )
            messagebox.showerror("Launch Failed", str(e))
