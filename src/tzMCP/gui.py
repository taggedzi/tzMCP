import tkinter as tk
from tkinter import ttk
import queue
from pathlib import Path
from tzMCP.gui_bits.config_manager import ConfigManager
from tzMCP.gui_bits.proxy_control import ProxyController
from tzMCP.gui_bits.proxy_tab import ProxyTab
from tzMCP.gui_bits.browser_tab import BrowserTab
from tzMCP.gui_bits.config_tab import ConfigTab
from tzMCP.gui_bits.status_bar import StatusBar
from tzMCP.gui_bits.log_server import start_gui_log_server
from tzMCP.gui_bits.browser_launcher import cleanup_browsers
from tzMCP.common_utils.log_config import setup_logging, log_gui
from tzMCP.common_utils.cleanup_profiles import clean_old_profiles
from tzMCP.common_utils.cleanup_logs import clean_old_logs
from tzMCP.paths import config_dir, logs_dir, profiles_dir
setup_logging()

class MainApp(tk.Tk):
    """Main application window, orchestrating all tabs and status bar."""
    def __init__(self):
        super().__init__()
        self.title("tzMCP Media Capture Proxy")
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        config_file = config_dir() / "media_proxy_config.yaml"
        profile_root = profiles_dir()
        log_dir = logs_dir()

        # Clean out old profiles and logs. 
        clean_old_profiles(profile_root, max_age_days=3)
        clean_old_logs(log_dir, max_age_days=7)

        log_gui.info(f"Application data directory: {config_file.parent.parent}")
        log_gui.debug(f"Config file: {config_file}")
        log_gui.debug(f"Config file exists: {config_file.exists()}")
        config_file.parent.mkdir(parents=True, exist_ok=True)
        self.config_manager = ConfigManager()
        self.config        = self.config_manager.load_config()
        self.proxy_controller = ProxyController(
            proxy_executable_path=str(Path(__file__).parent / "save_media.py"),
            proxy_port=self.config.proxy_port,
        )
        
        # Setup the GUI http logging server
        self.gui_queue = queue.Queue()
        start_gui_log_server(self.gui_queue)
        
        self.build_ui()
        # ensure we intercept window-close
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _on_tab_change(self, event):
        selected = event.widget.select()
        selected_tab = event.widget.nametowidget(selected)
        if isinstance(selected_tab, ConfigTab):
            try:
                new_config = self.config_manager.load_config()
                selected_tab.reload_config(new_config)
                self.config = new_config
                if self.proxy_controller.process is None:
                    self.proxy_controller.proxy_port = new_config.proxy_port
            except Exception as e:
                log_gui.exception(
                    "Could not reload the configuration. Check the configuration values "
                    "and correct any invalid entries before trying again."
                )
                from tkinter import messagebox
                messagebox.showerror("Error", f"Failed to reload config: {e}")

    def report_callback_exception(self, exc, val, tb):
        """Report unexpected Tk callback failures to the console with a traceback."""
        log_gui.critical(
            "Unexpected GUI error. Restart tzMCP and retry the action; if it persists, "
            "include this traceback in a bug report.",
            exc_info=(exc, val, tb),
        )

    def build_ui(self):
        self.geometry("900x700")
        self.minsize(760, 560)
        style = ttk.Style(self)
        style.configure("Title.TLabel", font=("Segoe UI", 18, "bold"))
        style.configure("Subtitle.TLabel", foreground="#5d6673")
        style.configure("Accent.TButton", font=("Segoe UI", 10, "bold"))

        notebook = ttk.Notebook(self)
        notebook.pack(fill='both', expand=True)
        
        # Bind tab change event
        notebook.bind("<<NotebookTabChanged>>", self._on_tab_change)

        status = StatusBar(self)
        status.pack(side='bottom', fill='x')

        self.proxy_tab = ProxyTab(notebook, self.proxy_controller, status, self.gui_queue, show_controls=False)
        browser_tab = BrowserTab(notebook, self.proxy_controller, status, self.proxy_tab._append_json_log)
        notebook.add(browser_tab, text="Capture Session")

        self.config_manager.set_logger(log_gui)
        config_tab = ConfigTab(notebook, self.config_manager, self.config)
        notebook.add(config_tab, text="Capture Rules")
        notebook.add(self.proxy_tab, text="Activity")

    def _on_close(self):
        # stop the proxy if it’s still running and log it
        try:
            if self.proxy_controller.process and self.proxy_controller.process.poll() is None:
                self.proxy_controller.stop_proxy()
                self.proxy_tab.log.config(state='normal')
                self.proxy_tab.log.insert('end', 'Proxy stopped on exit.\n')
                self.proxy_tab.log.config(state='disabled')
        except Exception:
            pass
        cleanup_browsers()
        self.destroy()

    def run(self):
        self.mainloop()

def main():
    try:
        MainApp().run()
    except Exception:
        log_gui.critical(
            "tzMCP could not start. Review the traceback below, then check the "
            "configuration and installation before retrying.",
            exc_info=True,
        )
        raise


if __name__ == "__main__":
    main()
