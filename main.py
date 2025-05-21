import tkinter as tk
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText
import subprocess
import threading
import os
import signal

class ProxyControlTab(ttk.Frame):
    def __init__(self, parent, status_callback):
        super().__init__(parent)
        self.proc = None
        self.status_callback = status_callback

        # Start/Stop toggle button
        self.toggle_btn = ttk.Button(self, text="Start Proxy", command=self.toggle_proxy)
        self.toggle_btn.pack(pady=10)

        # Console output box
        self.output = ScrolledText(self, height=20, width=100, bg="black", fg="lime", insertbackground="white")
        self.output.configure(state="disabled")
        self.output.pack(padx=10, pady=10)

    def toggle_proxy(self):
        if self.proc is None:
            self.start_proxy()
        else:
            self.stop_proxy()

    def start_proxy(self):
        script = os.path.abspath("save_media.py")
        self.proc = subprocess.Popen(
            ["mitmdump", "-s", script],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        self.toggle_btn.config(text="Stop Proxy")
        self.status_callback("Proxy Running", "green")
        threading.Thread(target=self.read_output, daemon=True).start()

    def stop_proxy(self):
        if self.proc:
            self.proc.terminate()
            self.proc = None
            self.toggle_btn.config(text="Start Proxy")
            self.status_callback("Proxy Stopped", "red")
            self.write_output("[!] Proxy stopped.\n")

    def read_output(self):
        for line in self.proc.stdout:
            self.write_output(line)
        self.proc = None
        self.toggle_btn.config(text="Start Proxy")
        self.status_callback("Proxy Exited", "yellow")

    def write_output(self, text):
        self.output.configure(state="normal")
        self.output.insert(tk.END, text)
        self.output.see(tk.END)
        self.output.configure(state="disabled")


class MainApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Media Capture Proxy")

        self.tabs = ttk.Notebook(self)
        self.tabs.pack(expand=1, fill="both")

        self.status_bar = tk.Label(self, text="Status: Idle", bg="grey", fg="white")
        self.status_bar.pack(fill=tk.X, side=tk.BOTTOM)

        self.proxy_tab = ProxyControlTab(self.tabs, self.update_status)
        self.tabs.add(self.proxy_tab, text="Proxy Control")

    def update_status(self, message, color):
        self.status_bar.config(text=f"Status: {message}", bg=color)


if __name__ == "__main__":
    app = MainApp()
    app.mainloop()
