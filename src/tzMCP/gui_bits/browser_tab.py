import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import shutil
from pathlib import Path
import yaml
from tzMCP.gui_bits.browser_launcher import launch_browser, detect_browser_name
from tzMCP.paths import config_dir
from tzMCP.common_utils.log_config import log_gui
from tzMCP.sessions.manager import SessionManager
from tzMCP.sessions.models import SessionRecord, SessionState
from tzMCP.appliance import is_appliance_mode
from tzMCP.browser.firefox_session import FirefoxSession
from tzMCP.paths import appliance_browser_dir, ca_dir
from tzMCP.sessions.export_service import ExportService
from tzMCP.sessions.versions import collect_versions

CONFIG_PATH = config_dir() / "browser_paths.yaml"

class BrowserTab(ttk.Frame):
    """Guided, safety-first capture session setup and browser launcher."""
    def __init__(self, master, proxy_controller, status_bar=None, activity_logger=None,
                 session_manager: SessionManager | None = None, config=None, persistent_config_path=None):
        super().__init__(master)
        self.proxy_controller = proxy_controller
        self.status_bar = status_bar
        self.activity_logger = activity_logger
        self.session_manager = session_manager if is_appliance_mode() else None
        self.config = config
        self.persistent_config_path = Path(persistent_config_path) if persistent_config_path else None
        self.session: SessionRecord | None = None
        self.firefox_session: FirefoxSession | None = None
        self.export_service = ExportService(self.session_manager.storage) if self.session_manager else None

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

        appliance_mode = is_appliance_mode()
        warning_text = (
            "Safety notice: tzMCP decrypts web traffic inside this appliance. "
            "Do not enter passwords, payment details, or other sensitive credentials while capturing."
            if appliance_mode else
            "Safety notice: tzMCP decrypts web traffic through mitmproxy. Do not enter passwords, "
            "payment details, or other sensitive credentials while capturing. Use a dedicated portable "
            "browser only; using an installed everyday browser can damage or lock its normal profile."
        )
        warning = tk.Label(
            self,
            text=warning_text,
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
        if appliance_mode:
            self.session_summary = ttk.Label(proxy_frame, text="No capture session.")
            self.session_summary.grid(row=1, column=0, columnspan=3, sticky="w", pady=(8, 0))
            self.after(2000, self._refresh_session_summary)

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
        if appliance_mode:
            mgmt_frame.grid_remove()

        # Launch options
        launch_frame = ttk.LabelFrame(
            self, text="2. Launch managed Firefox" if appliance_mode else "3. Launch browser", padding=12
        )
        launch_frame.grid(row=4, column=0, padx=18, pady=6, sticky="ew")

        ttk.Label(launch_frame, text="Launch URL:").grid(row=0, column=0, sticky="e", padx=5, pady=2)
        ttk.Entry(launch_frame, textvariable=self.launch_url, width=40).grid(row=0, column=1, columnspan=2, sticky="ew", padx=5, pady=2)

        incognito = ttk.Checkbutton(launch_frame, text="Private / Incognito Mode", variable=self.use_incognito)
        incognito.grid(row=1, column=0, columnspan=3, sticky="w", padx=5, pady=2)

        acknowledge = ttk.Checkbutton(
            launch_frame,
            text="I confirm this is a dedicated portable browser, not my everyday installed browser.",
            variable=self.safe_browser_acknowledged,
            command=self._update_launch_state,
        )
        acknowledge.grid(row=2, column=0, columnspan=3, sticky="w", padx=5, pady=(7, 2))
        if appliance_mode:
            incognito.grid_remove()
            acknowledge.grid_remove()

        self.launch_btn = ttk.Button(
            launch_frame,
            text="Launch Firefox" if appliance_mode else "Launch safe browser",
            command=self._launch_browser,
            state="disabled",
            style="Accent.TButton",
        )
        self.launch_btn.grid(row=3, column=0, columnspan=3, pady=(8, 2))
        self.export_btn = ttk.Button(launch_frame, text="Export Session", command=self._export_session, state="disabled")
        if appliance_mode:
            self.export_btn.grid(row=4, column=0, columnspan=3, pady=(4, 2))

        launch_frame.columnconfigure(1, weight=1)

        # Let main frame stretch with window
        self.columnconfigure(0, weight=1)
        self._update_launch_state()

    def _refresh_session_summary(self):
        if self.session is None or self.session_manager is None:
            text = "No capture session."
        else:
            try:
                record = self.session_manager.get_summary(self.session.session_id)
                text = (
                    f"Session {record.session_id} | {record.state}\n"
                    f"{record.capture_count:,} files | {record.capture_bytes:,} bytes"
                )
            except (OSError, ValueError):
                text = "Session summary unavailable. Review Activity for errors."
        self.session_summary.config(text=text)
        self.after(2000, self._refresh_session_summary)

    def restore_recovered_session(self, record: SessionRecord) -> None:
        """Expose a recovered session for export before another capture starts."""
        self.session = record
        if record.state in (SessionState.ENDED, SessionState.INTERRUPTED):
            state = "interrupted" if record.state is SessionState.INTERRUPTED else "ended"
            self.proxy_state.config(
                text=f"Recovered {state} session. Export it before starting another session."
            )
            self._append_activity(f"Recovered {state} session {record.session_id} for export.")
        self._update_launch_state()

    def _append_activity(self, line, color="blue"):
        if self.activity_logger:
            self.activity_logger({"color": color, "lines": [line]})

    def _start_proxy(self):
        created_session = None
        try:
            if self.session_manager is not None:
                if self.config is None:
                    raise RuntimeError("Cannot start a session without validated configuration")
                created_session = self.session_manager.create_session(self.config)
                self.session = created_session
                self.proxy_controller.config_path = (
                    self.session_manager.storage.session_dir(created_session.session_id)
                    / "metadata" / "capture-config.yaml"
                )
                self.proxy_controller.on_process_started = lambda identity: self.session_manager.record_process(
                    created_session.session_id, "proxy", identity
                )
            self.proxy_controller.start_proxy()
            if self.session_manager is not None and self.session is not None:
                self.session = self.session_manager.transition(self.session.session_id, SessionState.RUNNING)
            self.start_btn.config(state="disabled")
            self.stop_btn.config(state="normal")
            self.proxy_state.config(text=f"Running on 127.0.0.1:{self.proxy_controller.proxy_port}")
            if self.status_bar:
                self.status_bar.set_state("running")
            self._append_activity("Proxy started successfully.")
            self._update_launch_state()
        except Exception as exc:  # pylint: disable=broad-exception-caught
            if created_session is not None and self.session_manager is not None:
                try:
                    self.session = self.session_manager.record_error(
                        created_session.session_id, f"Proxy startup failed: {exc}"
                    )
                except Exception:  # preserve the original startup error
                    log_gui.exception("Could not record the failed startup error.")
                try:
                    if self.proxy_controller.process is not None:
                        self.proxy_controller.stop_proxy()
                    self.session = self.session_manager.transition(created_session.session_id, SessionState.INTERRUPTED)
                except Exception:  # preserve the original startup error
                    log_gui.exception("Could not mark the failed startup session interrupted.")
                self._restore_persistent_proxy_config()
                self._update_launch_state()
            log_gui.exception("Could not start the capture proxy.")
            self.proxy_state.config(text=f"Could not start proxy: {exc}")
            if self.status_bar:
                self.status_bar.set_state("error")
            self._append_activity(f"Error starting proxy: {exc}", "red")

    def _stop_proxy(self, interrupted=False):
        try:
            firefox_error = None
            try:
                self._stop_managed_firefox()
            except Exception as exc:  # preserve profile/evidence for recovery
                firefox_error = exc
                log_gui.exception("Could not safely stop managed Firefox.")
            self.proxy_controller.stop_proxy()
            if firefox_error:
                raise RuntimeError(f"Firefox shutdown failed; session preserved: {firefox_error}")
            if self.session_manager is not None and self.session is not None:
                target = SessionState.INTERRUPTED if firefox_error or interrupted else SessionState.ENDED
                self.session = self.session_manager.transition(self.session.session_id, target)
                self._restore_persistent_proxy_config()
            self.start_btn.config(state="normal")
            self.stop_btn.config(state="disabled")
            self.proxy_state.config(text=(
                "Session interrupted. Export the preserved captures."
                if interrupted else "Stopped — start this before launching a browser."
            ))
            if self.status_bar:
                self.status_bar.set_state("stopped")
            self._append_activity("Proxy stopped successfully.")
            self._update_launch_state()
        except Exception as exc:  # pylint: disable=broad-exception-caught
            log_gui.exception("Could not stop the capture proxy.")
            self.proxy_state.config(text=f"Shutdown incomplete; captures and profile preserved: {exc}")
            if self.status_bar:
                self.status_bar.set_state("error")
            self._append_activity(f"Failed to stop proxy: {exc}", "red")
            self._update_launch_state()

    def _restore_persistent_proxy_config(self):
        if self.persistent_config_path is not None:
            self.proxy_controller.config_path = self.persistent_config_path.resolve()

    def shutdown(self):
        """Stop the proxy and preserve an active session as interrupted."""
        try:
            self._stop_managed_firefox()
        except Exception:
            log_gui.exception("Could not safely stop managed Firefox during shutdown.")
            return
        self.proxy_controller.stop_proxy()
        if self.session_manager is not None and self.session is not None:
            record = self.session_manager.get(self.session.session_id)
            if record.state in (SessionState.NEW, SessionState.RUNNING):
                self.session = self.session_manager.transition(record.session_id, SessionState.INTERRUPTED)
            self._restore_persistent_proxy_config()

    def _update_launch_state(self):
        if self.__dict__.get("recovery_error"):
            for button in (self.start_btn, self.stop_btn, self.launch_btn, self.export_btn):
                button.config(state="disabled")
            return
        proxy_running = self.proxy_controller.process is not None and self.proxy_controller.process.poll() is None
        managed_launched = is_appliance_mode() and self.__dict__.get("firefox_session") is not None
        allowed = proxy_running and not managed_launched and (is_appliance_mode() or self.safe_browser_acknowledged.get())
        self.launch_btn.config(state="normal" if allowed else "disabled")
        needs_export = self.session is not None and self.session.state in (
            SessionState.ENDED, SessionState.INTERRUPTED
        )
        active_session = self.session is not None and self.session.state in (SessionState.NEW, SessionState.RUNNING)
        self.start_btn.config(state="disabled" if proxy_running or needs_export or active_session else "normal")
        self.stop_btn.config(state="normal" if proxy_running or active_session else "disabled")
        if hasattr(self, "export_btn"):
            self.export_btn.config(state="normal" if needs_export and not proxy_running else "disabled")

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
        if is_appliance_mode():
            self._launch_managed_firefox()
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

    def _launch_managed_firefox(self):
        if self.session_manager is None or self.session is None:
            messagebox.showerror("Launch Failed", "Start a capture session before launching Firefox.")
            return
        if self.firefox_session is not None:
            return
        try:
            firefox = os.environ.get("TZMCP_FIREFOX_PATH") or shutil.which("firefox")
            if not firefox:
                raise RuntimeError("Appliance-managed Firefox executable was not found")
            self.firefox_session = FirefoxSession(
                Path(firefox),
                appliance_browser_dir(self.session.session_id),
                ca_dir() / "mitmproxy-ca-cert.pem",
                self.proxy_controller.proxy_port,
            )
            identity = self.firefox_session.start(self.launch_url.get())
            self.session = self.session_manager.record_process(self.session.session_id, "firefox", identity)
            self._append_activity("Launched managed Firefox with a fresh session profile.")
            self._update_launch_state()
        except Exception as exc:  # pylint: disable=broad-exception-caught
            log_gui.exception("Could not launch managed Firefox.")
            try:
                self.session = self.session_manager.record_error(
                    self.session.session_id, f"Firefox startup failed: {exc}"
                )
            except Exception:
                log_gui.exception("Could not record the Firefox startup error.")
            self._stop_proxy(interrupted=True)
            self._append_activity(f"Firefox startup failed: {exc}", "red")
            messagebox.showerror("Launch Failed", str(exc))

    def _stop_managed_firefox(self):
        if self.firefox_session is None:
            return
        self.firefox_session.stop()
        self.firefox_session.cleanup()
        self.firefox_session = None

    def _export_session(self):
        if not is_appliance_mode() or self.export_service is None or self.session is None:
            messagebox.showerror("Export unavailable", "Session export is available only in appliance mode.")
            return
        if self.proxy_controller.process and self.proxy_controller.process.poll() is None:
            messagebox.showerror("Export unavailable", "End the running session before exporting.")
            return
        try:
            firefox_path = self.firefox_session.executable if self.firefox_session else None
            result = self.export_service.create_local_archive(self.session, collect_versions(firefox_path))
            self.export_service.publish(result)
            self.session = self.session_manager.complete_export(
                self.session.session_id, result.archive_path.name, result.size, result.sha256
            )
            self._append_activity(f"Exported session {self.session.session_id}.")
            self._update_launch_state()
        except Exception as exc:  # pylint: disable=broad-exception-caught
            log_gui.exception("Could not export session; the local archive remains available for retry.")
            messagebox.showerror("Export failed", str(exc))
