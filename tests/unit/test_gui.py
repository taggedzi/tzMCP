import ast
import logging
from pathlib import Path
from types import SimpleNamespace

from tzMCP.common_utils import log_config



def test_gui_module_invokes_main_when_run_as_a_module():
    gui_module = Path(__file__).parents[2] / "src" / "tzMCP" / "gui.py"
    module = ast.parse(gui_module.read_text(encoding="utf-8"))

    main_guards = [
        node
        for node in module.body
        if isinstance(node, ast.If)
        and isinstance(node.test, ast.Compare)
        and isinstance(node.test.left, ast.Name)
        and node.test.left.id == "__name__"
        and len(node.test.ops) == 1
        and isinstance(node.test.ops[0], ast.Eq)
        and len(node.test.comparators) == 1
        and isinstance(node.test.comparators[0], ast.Constant)
        and node.test.comparators[0].value == "__main__"
    ]

    assert any(
        isinstance(statement, ast.Expr)
        and isinstance(statement.value, ast.Call)
        and isinstance(statement.value.func, ast.Name)
        and statement.value.func.id == "main"
        for guard in main_guards
        for statement in guard.body
    )


def test_console_keeps_warnings_visible_when_gui_log_level_is_error(monkeypatch, tmp_path, capsys):
    """GUI support diagnostics must not be hidden by the in-app log level."""
    monkeypatch.setattr(
        log_config,
        "get_config",
        lambda: SimpleNamespace(log_to_file=False, log_level="ERROR"),
    )
    monkeypatch.setattr(log_config, "logs_dir", lambda: tmp_path / "logs")

    log_config.setup_logging()
    log_config.log_gui.warning("Browser executable is missing; re-add it in the GUI.")

    captured = capsys.readouterr()
    assert "[WARNING] Browser executable is missing" in captured.err
    assert log_config.log_gui.level == logging.WARNING
