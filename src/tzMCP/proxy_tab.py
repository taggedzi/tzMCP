import tkinter as tk
from tkinter import ttk, messagebox
from tkinter.scrolledtext import ScrolledText
import threading, re, time, queue

from tzMCP.proxy_control import ProxyController
from tzMCP.app_constants import LOG_BUFFER_SIZE, ANSI_PATTERN, ANSI_COLORS

# Only forward lines emitted by our add‑on (green 💾 , red ⏭ , banner)
FILTER_RE = re.compile(r"(💾|⏭|MediaSaver)")


class ProxyTab(ttk.Frame):
    """Tab that starts/stops the proxy and shows concise add‑on logs."""

    def __init__(self, parent, proxy_controller: ProxyController, status_bar=None):
        super().__init__(parent)
        self.proxy_controller = proxy_controller
        self.status_bar = status_bar  # optional
        self.gui_queue: queue.Queue[str] = queue.Queue()
        self._build_ui()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------
    def _build_ui(self):
        ctrl = ttk.Frame(self)
        ctrl.pack(fill="x", pady=5)
        self.start_btn = ttk.Button(ctrl, text="Start", command=self._start)
        self.start_btn.pack(side="left", padx=5)
        self.stop_btn = ttk.Button(ctrl, text="Stop", command=self._stop, state="disabled")
        self.stop_btn.pack(side="left")

        self.log = ScrolledText(self, state="disabled", height=15, wrap="none")
        for code, colour in ANSI_COLORS.items():
            self.log.tag_configure(colour, foreground=colour)
        self.log.pack(fill="both", expand=True, padx=5, pady=5)

    # ------------------------------------------------------------------
    # Start / Stop
    # ------------------------------------------------------------------
    def _start(self):
        try:
            # give controller access to the queue so it can push lines
            self.proxy_controller.gui_queue = self.gui_queue
            self.proxy_controller.start_proxy()

            self.start_btn.config(state="disabled")
            self.stop_btn.config(state="normal")
            if self.status_bar:
                self.status_bar.set_state("running")

            # clear previous log
            self.log.config(state="normal")
            self.log.delete("1.0", tk.END)
            self.log.config(state="disabled")

            # begin polling queue for new lines
            self.after(50, self._poll_gui_queue)
        except Exception as e:
            messagebox.showerror("Error", str(e))
            if self.status_bar:
                self.status_bar.set_state("error")

    def _stop(self):
        self.proxy_controller.stop_proxy()
        self.start_btn.config(state="normal")
        self.stop_btn.config(state="disabled")
        if self.status_bar:
            self.status_bar.set_state("stopped")
        # flush remaining lines so user sees final messages
        self._poll_gui_queue()

    # ------------------------------------------------------------------
    # Queue polling → GUI console
    # ------------------------------------------------------------------
    def _poll_gui_queue(self):
        while not self.gui_queue.empty():
            line = self.gui_queue.get_nowait()
            self._append_line(line)
        if self.proxy_controller.process and self.proxy_controller.process.poll() is None:
            self.after(50, self._poll_gui_queue)  # keep polling until proxy exits
        else:
            if self.status_bar:
                self.status_bar.set_state("stopped")

    # ------------------------------------------------------------------
    # Helper: insert colourised line, trim buffer
    # ------------------------------------------------------------------
    def _append_line(self, line: str):
        segments = ANSI_PATTERN.split(line)
        tags: list[str] = []
        self.log.config(state="normal")
        i = 0
        while i < len(segments):
            text = segments[i]
            if text:
                self.log.insert(tk.END, text, tags)
            if i + 1 < len(segments):
                code = segments[i + 1]
                tags = [ANSI_COLORS[code]] if code in ANSI_COLORS and code != "0" else []
            i += 2

        # trim scrollback
        total_lines = int(self.log.index("end-1c").split(".")[0])
        if total_lines > LOG_BUFFER_SIZE:
            self.log.delete("1.0", f"{total_lines - LOG_BUFFER_SIZE}.0")

        self.log.see(tk.END)
        self.log.config(state="disabled")
