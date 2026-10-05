"""The independent checker must catch every kind of violation."""
from src.simulation.checker import SolutionChecker
from tests.conftest import Loader

MAP = ("nb_drones: 2\nstart_hub: s 0 0\nhub: a 1 0\n"
       "hub: r 2 0 [zone=restricted]\nend_hub: e 3 0\n"
       "connection: s-a\nconnection: a-r\nconnection: r-e\n"
       "connection: s-e\n")


def check(load: Loader, out: list[str]) -> list[str]:
    return SolutionChecker(load(MAP)).check(out)


def test_valid_solution(load: Loader) -> None:
    out = ["D1-a D2-e", "D1-a-r", "D1-r", "D1-e"]
    assert check(load, out) == []


def test_zone_over_capacity(load: Loader) -> None:
    errs = check(load, ["D1-a D2-a"])
    assert any("holds 2/1" in e for e in errs)


def test_link_over_capacity(load: Loader) -> None:
    errs = check(load, ["D1-e D2-e"])
    assert any("used 2/1" in e for e in errs)


def test_restricted_needs_two_turns(load: Loader) -> None:
    errs = check(load, ["D1-a D2-e", "D1-r"])
    assert any("skips the 2-turn" in e for e in errs)


def test_drone_may_not_stall_on_connection(load: Loader) -> None:
    errs = check(load, ["D1-a D2-e", "D1-a-r", "D2-e"])
    assert any("stalled" in e for e in errs)


def test_undelivered_drone(load: Loader) -> None:
    errs = check(load, ["D1-a D2-e"])
    assert any("never reaches" in e for e in errs)


def test_missing_connection_and_garbage(load: Loader) -> None:
    assert check(load, ["D1-r D2-e"])
    assert check(load, ["nonsense"])
