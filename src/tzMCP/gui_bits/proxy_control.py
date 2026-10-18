import os
import subprocess
import socket
import sys
import time
from pathlib import Path
from typing import Optional
import threading
import psutil
from tzMCP.sessions.processes import ProcessIdentity, stop_owned_process_tree
from tzMCP.proxy_runtime import ProxyLaunchSpec, build_proxy_command, launch_environment


class ProxyController:
    """Launch and manage a mitmdump process running the save_media.py addon."""

    def __init__(self, proxy_executable_path: str, proxy_port: int = 8080, gui_queue=None,
                 config_path: str | Path | None = None, confdir: str | Path | None = None,
                 log_dir: str | Path | None = None, startup_timeout: float = 10.0):
        print(f"Proxy controller initialized")
        print(f"proxy_executable_path: {proxy_executable_path}")
        self.proxy_executable_path = proxy_executable_path  # path to save_media.py
        self.proxy_port = proxy_port
        self.process: Optional[subprocess.Popen] = None
        self.gui_queue = gui_queue  # <-- ADD THIS LINE
        self.config_path = Path(config_path).resolve() if config_path else None
        self.confdir = Path(confdir).resolve() if confdir else None
        self.log_dir = Path(log_dir).resolve() if log_dir else None
        self.startup_timeout = startup_timeout
        self.proxy_ready = False
        self.identity = None
        self.on_process_started = None

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _is_port_in_use(self) -> bool:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            return sock.connect_ex(("127.0.0.1", self.proxy_port)) == 0

    def _wait_for_readiness(self) -> None:
        """Wait until mitmdump accepts loopback connections or fails."""
        deadline = time.monotonic() + self.startup_timeout
        while time.monotonic() < deadline:
            if self.process is None:
                raise RuntimeError("Proxy process disappeared during startup")
            return_code = self.process.poll()
            if return_code is not None:
                raise RuntimeError(f"Proxy exited during startup with code {return_code}")
            if self._is_port_in_use():
                self.proxy_ready = True
                return
            time.sleep(0.05)
        raise TimeoutError(
            f"Proxy did not become ready on 127.0.0.1:{self.proxy_port} "
            f"within {self.startup_timeout:.1f} seconds"
        )

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
        self.proxy_ready = False

        script_path = Path(self.proxy_executable_path).resolve()
        print(f"Script path: {script_path}")
        if not script_path.exists():
            raise RuntimeError(f"Proxy script not found at {script_path}")

        if self.config_path is None:
            raise RuntimeError("An explicit proxy config path is required")
        spec = ProxyLaunchSpec(
            self.config_path,
            self.proxy_port,
            confdir=self.confdir,
            log_dir=self.log_dir,
            auto_reload=not bool(os.environ.get("TZMCP_APPLIANCE") == "1"),
        )
        cmd = build_proxy_command(spec, script_path, self._mitmdump_exe())
        cmd.extend(["--set", "http2=true"])
        env = launch_environment(spec)
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
            start_new_session=True,
        )
        try:
            self.identity = ProcessIdentity.from_process(psutil.Process(self.process.pid))
            if self.on_process_started is not None:
                self.on_process_started(self.identity)
            threading.Thread(target=self._drain_stdout, daemon=True).start()
            self._wait_for_readiness()
        except Exception:
            self.stop_proxy()
            raise

    def _drain_stdout(self):
        if not self.process or not self.process.stdout:
            return
        
        for line in self.process.stdout:
            # mirror everything to the parent shell (optional)
            print(line, end="")

    def stop_proxy(self) -> None:
        """Gracefully terminate the mitmdump subprocess."""
        if self.identity is not None:
            # The parent may have exited during an earlier, incomplete stop.
            # Its recorded OS session can still contain capture processes.
            stop_owned_process_tree(self.identity)
            if self.process is not None:
                self.process.wait(timeout=5)
        elif self.process and self.process.poll() is None:
            # A launch-time identity failure still leaves us with the
            # original Popen handle, which must be reaped before returning.
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=5)
        self.process = None
        self.identity = None
        self.proxy_ready = False

    def _mirror_stdout(self):
        if self.process and self.process.stdout:
            for line in self.process.stdout:
                print(line, end="")      # goes to PowerShell as well
