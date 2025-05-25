import tkinter as tk
from tkinter import ttk
from pathlib import Path
import queue
from tzMCP.save_media_utils.save_media_utils import log
from tzMCP.gui_bits.config_manager import ConfigManager
from tzMCP.gui_bits.proxy_control import ProxyController
from tzMCP.gui_bits.proxy_tab import ProxyTab
from tzMCP.gui_bits.browser_tab import BrowserTab
from tzMCP.gui_bits.config_tab import ConfigTab
from tzMCP.gui_bits.status_bar import StatusBar
from tzMCP.gui_bits.domain_tab import DomainTab
from tzMCP.gui_bits.log_server import start_gui_log_server
from tzMCP.gui_bits.browser_launcher import cleanup_browsers

class MainApp(tk.Tk):
    """Main application window, orchestrating all tabs and status bar."""
    def __init__(self):
        super().__init__()
        self.title("tzMCP Media Capture Proxy")
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        # Initialize controllers (always use project/config/media_proxy_config.yaml)
        project_root       = Path(__file__).parent.parent.parent
        config_file        = project_root / "config" / "media_proxy_config.yaml"

        print(f"Project root: {project_root}")
        print(f"Config file: {config_file}")
        print(f"Config file exists: {config_file.exists()}")
        config_file.parent.mkdir(parents=True, exist_ok=True)
        self.config_manager = ConfigManager()
        self.config        = self.config_manager.load_config()
        self.proxy_controller = ProxyController(
            proxy_executable_path=str(Path(__file__).parent / "save_media.py"),
            proxy_port=8080
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
            except Exception as e:
                from tkinter import messagebox
                messagebox.showerror("Error", f"Failed to reload config: {e}")

    def build_ui(self):
        # Notebook for tabs
        notebook = ttk.Notebook(self)
        notebook.pack(fill='both', expand=True)
        
        # Bind tab change event
        notebook.bind("<<NotebookTabChanged>>", self._on_tab_change)

        # Proxy Control tab
        status = StatusBar(self)
        status.pack(side='bottom', fill='x')

        self.proxy_tab = ProxyTab(notebook, self.proxy_controller, status, self.gui_queue)
        notebook.add(self.proxy_tab, text="Proxy Control")

        # Browser Launch tab
        browser_tab = BrowserTab(notebook, self.proxy_controller)
        notebook.add(browser_tab, text="Browser Launch")

        # Configuration tab
        self.config_manager.set_logger(log)
        config_tab = ConfigTab(notebook, self.config_manager, self.config)
        notebook.add(config_tab, text="Configuration")

        # Domain Viewer tab
        domain_tab = DomainTab(notebook)
        notebook.add(domain_tab, text="Domain Viewer")

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
    MainApp().run()
