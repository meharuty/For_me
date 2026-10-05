"""Command-line behaviour: output format and clean error handling."""
import pytest

from main import FlyInApp, build_arg_parser
from tests.conftest import ROOT


def run(*argv: str) -> int:
    return FlyInApp(build_arg_parser().parse_args(list(argv))).run()


def test_plain_output(capsys: pytest.CaptureFixture[str]) -> None:
    code = run(str(ROOT / "maps/easy/01_linear_path.txt"), "--plain")
    out = capsys.readouterr().out.splitlines()
    assert code == 0
    assert out == [
        "D1-waypoint1",
        "D1-waypoint2 D2-waypoint1",
        "D1-goal D2-waypoint2",
        "D2-goal",
    ]


def test_unsolvable_map_is_reported(
        capsys: pytest.CaptureFixture[str]) -> None:
    code = run(str(ROOT / "maps/custom/unsolvable.txt"), "--plain")
    assert code == 1
    assert "unsolvable" in capsys.readouterr().err


def test_syntax_error_has_line_number(
        capsys: pytest.CaptureFixture[str]) -> None:
    code = run(str(ROOT / "maps/custom/bad_syntax.txt"), "--plain")
    assert code == 1
    assert "Line 3:" in capsys.readouterr().err


def test_missing_file(capsys: pytest.CaptureFixture[str]) -> None:
    assert run("does_not_exist.txt", "--plain") == 1
    assert "Error:" in capsys.readouterr().err


def test_colored_replay_runs(capsys: pytest.CaptureFixture[str]) -> None:
    code = run(str(ROOT / "maps/medium/03_priority_puzzle.txt"),
               "--delay", "0")
    out = capsys.readouterr().out
    assert code == 0
    assert "=== SUMMARY ===" in out and "=== OUTPUT ===" in out
