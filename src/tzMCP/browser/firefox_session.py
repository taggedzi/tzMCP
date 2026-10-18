"""Per-session Firefox profile, proxy, certificate, and process lifecycle."""
from __future__ import annotations

import shutil
import subprocess
from collections.abc import Callable
from pathlib import Path

import psutil

from tzMCP.paths import ensure_private_dir
from tzMCP.sessions.processes import ProcessIdentity, verify_process_identity, _session_members

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
        # Snap launchers rely on the symlink name (for example,
        # /snap/bin/firefox -> /usr/bin/snap) to select the application.
        self.executable = executable.absolute()
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
        ensure_private_dir(self.session_browser_dir)
        self.profile_dir.mkdir(mode=0o700, parents=False, exist_ok=False)
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
            if self.process is not None and self.process.poll() is None:
                self.process.terminate()
                try:
                    self.process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.process.kill()
                    self.process.wait(timeout=5)
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
            if self.process is not None and self.process.poll() is None:
                raise FirefoxSessionError("Firefox identity unavailable; profile preserved")
            return
        if self.identity.owner is None:
            raise FirefoxSessionError("Firefox owner unavailable; profile preserved")
        roots: dict[int, psutil.Process] = {}
        if verify_process_identity(self.identity):
            process = psutil.Process(self.identity.pid)
            roots[process.pid] = process

        # Firefox Snap can exec into a different binary after Popen returns.
        # In that case the original PID no longer matches its launch identity,
        # even though the new process still owns this unique private profile.
        # Match the exact profile and owner, then take a fresh PID/start-time
        # identity before stopping that process tree.
        profile = str(self.profile_dir.resolve())
        for candidate in psutil.process_iter(["cmdline", "username"]):
            try:
                info = candidate.info
                command = info.get("cmdline") or []
                owner = info.get("username")
                if profile not in command or (self.identity.owner is not None and owner != self.identity.owner):
                    continue
                process = psutil.Process(candidate.pid)
                identity = ProcessIdentity.from_process(process)
                if profile not in (process.cmdline() or []) or not verify_process_identity(identity):
                    continue
                roots[process.pid] = process
            except (psutil.Error, OSError, ValueError):
                continue

        if not roots:
            if self.process is not None and self.process.poll() is not None:
                for process in _session_members(self.identity):
                    roots[process.pid] = process
            if self.process is None or self.process.poll() is None:
                try:
                    psutil.Process(self.identity.pid)
                except psutil.NoSuchProcess:
                    for process in _session_members(self.identity):
                        roots[process.pid] = process
                else:
                    raise FirefoxSessionError("Firefox ownership could not be verified; profile preserved")
            # Firefox may already have been closed normally. Do not signal an
            # unrelated process if the recorded launcher PID has since changed.
            if not roots:
                self.process = None
                self.identity = None
                return

        descendants: dict[int, psutil.Process] = {}
        for process in roots.values():
            try:
                for child in process.children(recursive=True):
                    descendants[child.pid] = child
            except psutil.NoSuchProcess:
                raise FirefoxSessionError("Firefox tree changed during shutdown; retry recovery")
        targets_by_pid = {**descendants, **roots}
        targets = list(targets_by_pid.values())
        identities = {process.pid: ProcessIdentity.from_process(process) for process in targets}
        for process in targets:
            identity = identities[process.pid]
            if identity.owner != self.identity.owner or not verify_process_identity(identity):
                raise FirefoxSessionError("Firefox tree ownership changed; profile preserved")
            process.terminate()
        _, alive = psutil.wait_procs(targets, timeout=5)
        for child in alive:
            if not verify_process_identity(identities[child.pid]):
                raise FirefoxSessionError("Firefox tree identity changed; profile preserved")
            child.kill()
        _, alive = psutil.wait_procs(alive, timeout=5)
        if alive:
            raise FirefoxSessionError("Firefox did not exit; profile preserved")
        if _session_members(self.identity):
            raise FirefoxSessionError("Firefox spawned more processes; retry recovery with profile preserved")
        self.process = None
        self.identity = None

    def cleanup(self) -> None:
        if self.identity is not None or (self.process is not None and self.process.poll() is None):
            self.stop()
        if self.profile_dir.exists():
            shutil.rmtree(self.profile_dir)
        try:
            self.session_browser_dir.rmdir()
        except OSError:
            pass
