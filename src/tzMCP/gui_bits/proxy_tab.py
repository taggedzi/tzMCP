import threading
import json
import queue
import tkinter as tk
from tkinter import scrolledtext, ttk
from http.server import BaseHTTPRequestHandler, HTTPServer
import time
from tzMCP.common_utils.log_config import log_gui

class ProxyTab(ttk.Frame):
    def __init__(self, master, proxy_controller, status_bar, gui_queue, show_controls=True):
        super().__init__(master)
        self.proxy_controller = proxy_controller
        self.status_bar = status_bar

        self.gui_queue = gui_queue
        self.proxy_controller.gui_queue = self.gui_queue

        self._build_widgets(show_controls)
        self._start_log_drain_thread()

    def _build_widgets(self, show_controls):
        log_row = 0
        if show_controls:
            self.start_btn = ttk.Button(self, text="Start", command=self._start)
            self.start_btn.grid(row=0, column=0, padx=5, pady=5)

            self.stop_btn = ttk.Button(self, text="Stop", command=self._stop, state='disabled')
            self.stop_btn.grid(row=0, column=1, padx=5, pady=5)
            log_row = 1
        else:
            self.start_btn = None
            self.stop_btn = None

        self.log = scrolledtext.ScrolledText(self, wrap=tk.WORD, height=20, state='disabled')
        self.log.grid(row=log_row, column=0, columnspan=2, sticky='nsew', padx=10, pady=10)
        self.grid_rowconfigure(log_row, weight=1)
        self.grid_columnconfigure(1, weight=1)

        # Setup color tags
        self.log.tag_configure("red", foreground="red")
        self.log.tag_configure("green", foreground="green")
        self.log.tag_configure("orange", foreground="orange")
        self.log.tag_configure("blue", foreground="blue")
        self.log.tag_configure("grey", foreground="grey")
        self.log.tag_configure("black", foreground="black")

    def _start(self):
        try:
            self.proxy_controller.start_proxy()
            if self.start_btn:
                self.start_btn.config(state='disabled')
            if self.stop_btn:
                self.stop_btn.config(state='normal')
            self.status_bar.set_state('running')
            self._append_json_log({"color": "blue", "weight": "bold", "lines": ["Proxy started successfully."]})
        except Exception as e:
            log_gui.exception(
                "Could not start the proxy. Check that the configured port is free and "
                "that mitmproxy is installed in the active environment."
            )
            self._append_json_log({"color": "red", "weight": "bold", "lines": [f"Error starting proxy: {e}"]})
            self.status_bar.set_state('error')

    def _stop(self):
        try:
            self.proxy_controller.stop_proxy()
            if self.start_btn:
                self.start_btn.config(state='normal')
            if self.stop_btn:
                self.stop_btn.config(state='disabled')
            self.status_bar.set_state('stopped')
            self._append_json_log({"color": "blue", "weight": "bold", "lines": ["Proxy stopped successfully."]})
        except Exception as e:
            log_gui.exception(
                "Could not stop the proxy. Retry the stop action; if it persists, close "
                "tzMCP and check for a remaining mitmdump process."
            )
            self._append_json_log({"color": "red", "weight": "bold", "lines": [f"Failed to stop proxy: {e}"]})

    def _start_log_drain_thread(self):
        threading.Thread(target=self._drain_queue, daemon=True).start()

    def _drain_queue(self):
        while True:
            try:
                raw = self.gui_queue.get()
                if isinstance(raw, dict):
                    msg = raw
                else:
                    msg = json.loads(raw)
                self._append_json_log(msg)
            except Exception:
                continue

    def _append_json_log(self, msg):
        color = msg.get("color") or msg.get("tag") or ""
        lines = msg.get("lines", [])
        self.log.config(state='normal')
        for line in lines:
            self.log.insert(tk.END, line + "\n", color)
        self.log.see(tk.END)
        self.log.config(state='disabled')
