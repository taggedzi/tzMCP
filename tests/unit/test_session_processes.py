from types import SimpleNamespace

from tzMCP.sessions.processes import ProcessIdentity, verify_process_identity


def test_process_identity_requires_executable_owner_and_start_time(tmp_path):
    executable = tmp_path / "mitmdump"
    executable.write_text("", encoding="utf-8")
    identity = ProcessIdentity(42, str(executable), 123.0, "tzmcp")

    process = SimpleNamespace(
        pid=42,
        exe=lambda: str(executable),
        create_time=lambda: 123.0,
        username=lambda: "tzmcp",
    )
    assert verify_process_identity(identity, lambda _: process)

    wrong_pid_reuse = SimpleNamespace(
        pid=42,
        exe=lambda: str(executable),
        create_time=lambda: 999.0,
        username=lambda: "tzmcp",
    )
    assert not verify_process_identity(identity, lambda _: wrong_pid_reuse)
