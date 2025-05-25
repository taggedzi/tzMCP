import os
import subprocess
import socket
import sys
from pathlib import Path
from typing import Optional
import threading


class ProxyController:
    """Launch and manage a mitmdump process running the save_media.py addon."""

    def __init__(self, proxy_executable_path: str, proxy_port: int = 8080, gui_queue=None):
        print(f"Proxy controller initialized")
        print(f"proxy_executable_path: {proxy_executable_path}")
        self.proxy_executable_path = proxy_executable_path  # path to save_media.py
        self.proxy_port = proxy_port
        self.process: Optional[subprocess.Popen] = None
        self.gui_queue = gui_queue  # <-- ADD THIS LINE

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _is_port_in_use(self) -> bool:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            return sock.connect_ex(("127.0.0.1", self.proxy_port)) == 0

    def _mitmdump_exe(self) -> Path:
        exe = Path(sys.executable).parent / ("mitmdump.exe" if sys.platform == "win32" else "mitmdump")
        if not exe.exists():
            raise RuntimeError(f"mitmdump executable not found at {exe}")
        return exe

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def start_proxy(self) -> None:
        """Start mitmdump on the requested port with the given addon script."""
        if self._is_port_in_use():
            raise RuntimeError(f"Port {self.proxy_port} is already in use.")

        script_path = Path(self.proxy_executable_path).resolve()
        print(f"Script path: {script_path}")
        if not script_path.exists():
            raise RuntimeError(f"Proxy script not found at {script_path}")

        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"

        cmd = [
            str(self._mitmdump_exe()), 
            "-q",  # quiet mitmdump output
            # "--set", "console_eventlog=false", # suppress INFO flood
            "--set", "console_eventlog_verbosity=info",  # Control mitmdump log output level to term
            "--listen-host", "127.0.0.1",                # Only allow local connection
            "--listen-port", str(self.proxy_port),
            "-s", str(script_path),
        ]
        print("[DEBUG] Launching proxy:", " ".join(cmd))
        self.process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            bufsize=1,
            cwd=str(script_path.parent),
            env=env, 
        )
        threading.Thread(target=self._drain_stdout, daemon=True).start()

    def _drain_stdout(self):
        if not self.process or not self.process.stdout:
            return
        
        for line in self.process.stdout:
            # mirror everything to the parent shell (optional)
            print(line, end="")

    def stop_proxy(self) -> None:
        """Gracefully terminate the mitmdump subprocess."""
        if self.process and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()
        self.process = None

    def _mirror_stdout(self):
        if self.process and self.process.stdout:
            for line in self.process.stdout:
                print(line, end="")      # goes to PowerShell as well
