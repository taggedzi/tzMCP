"""Per-session Firefox profile, proxy, certificate, and process lifecycle."""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Callable

import psutil

from tzMCP.sessions.processes import ProcessIdentity, verify_process_identity


CA_NICKNAME = "tzMCP mitmproxy CA"


class FirefoxSessionError(RuntimeError):
    """Raised when managed Firefox setup or shutdown cannot complete safely."""


class FirefoxSession:
    def __init__(
        self,
        executable: Path,
        session_browser_dir: Path,
        ca_certificate: Path,
        proxy_port: int,
        certutil: Path | str = "certutil",
        runner: Callable[..., subprocess.CompletedProcess] = subprocess.run,
    ):
        self.executable = executable.resolve()
        self.session_browser_dir = session_browser_dir.resolve()
        self.ca_certificate = ca_certificate.resolve()
        self.proxy_port = proxy_port
        self.certutil = str(certutil)
        self.runner = runner
        self.profile_dir = self.session_browser_dir / "profile"
        self.process: subprocess.Popen | None = None
        self.identity: ProcessIdentity | None = None

    def create_profile(self) -> Path:
        if not self.executable.is_file():
            raise FirefoxSessionError(f"Firefox executable not found: {self.executable}")
        if not self.ca_certificate.is_file():
            raise FirefoxSessionError(f"CA certificate not found: {self.ca_certificate}")
        self.session_browser_dir.mkdir(parents=True, exist_ok=True)
        self.profile_dir.mkdir(parents=False, exist_ok=False)
        if not 1 <= self.proxy_port <= 65535:
            raise FirefoxSessionError("Firefox proxy port is invalid")
        (self.profile_dir / "user.js").write_text(
            "\n".join(
                [
                    'user_pref("network.proxy.type", 1);',
                    'user_pref("network.proxy.http", "127.0.0.1");',
                    f'user_pref("network.proxy.http_port", {self.proxy_port});',
                    'user_pref("network.proxy.ssl", "127.0.0.1");',
                    f'user_pref("network.proxy.ssl_port", {self.proxy_port});',
                    'user_pref("network.proxy.no_proxies_on", "");',
                ]
            )
            + "\n",
            encoding="utf-8",
            newline="\n",
        )
        return self.profile_dir

    def _run_certutil(self, *args: str) -> None:
        command = [self.certutil, *args]
        result = self.runner(command, check=False, capture_output=True, text=True)
        if result.returncode != 0:
            raise FirefoxSessionError(
                f"certutil failed ({result.returncode}): {(result.stderr or '').strip()}"
            )

    def import_ca(self) -> None:
        if not self.profile_dir.is_dir():
            raise FirefoxSessionError("Firefox profile has not been created")
        database = f"sql:{self.profile_dir}"
        self._run_certutil("-N", "-d", database, "--empty-password")
        self._run_certutil(
            "-A", "-d", database, "-n", CA_NICKNAME, "-t", "C,,", "-a", "-i", str(self.ca_certificate)
        )
        self._run_certutil("-L", "-d", database, "-n", CA_NICKNAME)

    def launch(self, url: str = "about:blank") -> ProcessIdentity:
        if not self.profile_dir.is_dir():
            raise FirefoxSessionError("Firefox profile has not been created")
        if self.process is not None and self.process.poll() is None:
            raise FirefoxSessionError("Firefox session is already running")
        try:
            self.process = subprocess.Popen(
                [str(self.executable), "-no-remote", "-profile", str(self.profile_dir), url],
                start_new_session=True,
            )
            self.identity = ProcessIdentity.from_process(psutil.Process(self.process.pid))
            return self.identity
        except (OSError, psutil.Error) as exc:
            self.process = None
            raise FirefoxSessionError(f"Could not launch Firefox: {exc}") from exc

    def start(self, url: str = "about:blank") -> ProcessIdentity:
        self.create_profile()
        try:
            self.import_ca()
            return self.launch(url)
        except Exception:
            self.cleanup()
            raise

    def stop(self) -> None:
        if self.identity is None:
            return
        if not verify_process_identity(self.identity):
            raise FirefoxSessionError("Refusing to stop an unverified Firefox process")
        process = psutil.Process(self.identity.pid)
        descendants = process.children(recursive=True)
        for child in descendants:
            child.terminate()
        process.terminate()
        _, alive = psutil.wait_procs([*descendants, process], timeout=5)
        for child in alive:
            child.kill()
        self.process = None
        self.identity = None

    def cleanup(self) -> None:
        if self.process is not None and self.process.poll() is None:
            self.stop()
        if self.profile_dir.exists():
            shutil.rmtree(self.profile_dir)
