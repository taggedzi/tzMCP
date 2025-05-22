import tkinter as tk
from tkinter import ttk, messagebox
from tkinter.scrolledtext import ScrolledText
import threading

from tzMCP.app_constants import LOG_BUFFER_SIZE, ANSI_PATTERN, ANSI_COLORS
from tzMCP.proxy_control import ProxyController
from tzMCP.status_bar import StatusBar

class ProxyTab(ttk.Frame):
    """Tab for controlling and monitoring the download proxy."""
    def __init__(self, parent, proxy_controller: ProxyController, status_bar: StatusBar):
        super().__init__(parent)
        self.proxy_controller = proxy_controller
        self.status_bar = status_bar
        self._build_ui()

    def _build_ui(self):
        # Control buttons
        ctrl = ttk.Frame(self)
        ctrl.pack(fill='x', pady=5)
        self.start_btn = ttk.Button(ctrl, text="Start Proxy", command=self._start)
        self.start_btn.pack(side='left', padx=5)
        self.stop_btn = ttk.Button(ctrl, text="Stop Proxy", command=self._stop, state='disabled')
        self.stop_btn.pack(side='left')

        # Log view
        self.log = ScrolledText(self, state='disabled', height=15, wrap='none')
        for code, color in ANSI_COLORS.items():
            self.log.tag_configure(color, foreground=color)
        self.log.pack(fill='both', expand=True, padx=5, pady=5)

    def _start(self):
        """Start proxy and confirm it is listening."""
        try:
            # Kick off the subprocess
            self.proxy_controller.start_proxy()

            # Poll the port for up to 2 seconds
            import time
            for _ in range(20):
                if self.proxy_controller._is_port_in_use():
                    break
                time.sleep(0.1)
            else:
                raise RuntimeError("Proxy failed to start within timeout")

            # Update buttons and status
            self.start_btn.config(state='disabled')
            self.stop_btn.config(state='normal')
            self.status_bar.set_state('running')

            # Log to console
            self.log.config(state='normal')
            self.log.insert('end', 'Proxy started successfully.\n')
            self.log.config(state='disabled')

            # Begin streaming logs
            threading.Thread(target=self._read_logs, daemon=True).start()

        except Exception as e:
            # Error state
            self.status_bar.set_state('error')
            self.log.config(state='normal')
            self.log.insert('end', f'Error starting proxy: {e}\n')
            self.log.config(state='disabled')
            messagebox.showerror("Error", f"Failed to start proxy: {e}")

    def _stop(self):
        import time
        try:
            self.proxy_controller.stop_proxy()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to stop proxy: {e}")
            self.status_bar.set_state("error")
            return

        for _ in range(30):
            if not self.proxy_controller._is_port_in_use():
                break
            time.sleep(0.1)

        self.start_btn.config(state="normal")
        self.stop_btn.config(state="disabled")
        self.status_bar.set_state("stopped")

        self.log.config(state="normal")
        self.log.insert("end", f"[{time.strftime('%H:%M:%S')}] Proxy stopped successfully.\n")
        self.log.config(state="disabled")




    def _read_logs(self):
        proc = self.proxy_controller.process
        if not proc or not proc.stdout:
            return
        for line in proc.stdout:
            segments = ANSI_PATTERN.split(line)
            tags = []
            self.log.config(state='normal')
            i = 0
            while i < len(segments):
                text = segments[i]
                if text:
                    self.log.insert(tk.END, text, tags)
                if i + 1 < len(segments):
                    code = segments[i+1]
                    if code == '0':
                        tags = []
                    else:
                        color = ANSI_COLORS.get(code)
                        tags = [color] if color else tags
                i += 2
            # Trim buffer
            lines = int(self.log.index('end-1c').split('.')[0])
            if lines > LOG_BUFFER_SIZE:
                self.log.delete('1.0', f'{lines-LOG_BUFFER_SIZE}.0')
            self.log.see(tk.END)
            self.log.config(state='disabled')
