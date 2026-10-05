"""Planner, scheduler and simulation rules on tiny hand-made maps."""
from src.algorithms.planner import TimeExpandedPlanner
from tests.conftest import Loader, solve


def lines(load: Loader, text: str) -> list[str]:
    return solve(load(text)).lines()


def test_one_drone_straight_line(load: Loader) -> None:
    out = lines(load, "nb_drones: 1\nstart_hub: s 0 0\nhub: a 1 0\n"
                "end_hub: e 2 0\nconnection: s-a\nconnection: a-e\n")
    assert out == ["D1-a", "D1-e"]


def test_restricted_zone_takes_two_turns(load: Loader) -> None:
    out = lines(load, "nb_drones: 1\nstart_hub: s 0 0\n"
                "hub: r 1 0 [zone=restricted]\nend_hub: e 2 0\n"
                "connection: s-r\nconnection: r-e\n")
    assert out == ["D1-s-r", "D1-r", "D1-e"]


def test_restricted_link_is_freed_on_arrival(load: Loader) -> None:
    """The subject's example: D2 may start crossing as D1 lands."""
    out = lines(load, "nb_drones: 2\nstart_hub: s 0 0\n"
                "hub: r 1 0 [zone=restricted max_drones=2]\n"
                "end_hub: e 2 0 \nconnection: s-r [max_link_capacity=1]\n"
                "connection: r-e [max_link_capacity=2]\n")
    assert out[0] == "D1-s-r"
    assert out[1].split()[:2] == ["D1-r", "D2-s-r"]


def test_zone_capacity_makes_drones_queue(load: Loader) -> None:
    out = lines(load, "nb_drones: 3\nstart_hub: s 0 0\n"
                "hub: a 1 0 [max_drones=1]\nend_hub: e 2 0\n"
                "connection: s-a [max_link_capacity=3]\n"
                "connection: a-e [max_link_capacity=3]\n")
    assert len(out) == 4  # single-file column: one entry per turn
    assert out[0] == "D1-a"


def test_priority_route_is_preferred(load: Loader) -> None:
    out = lines(load, "nb_drones: 1\nstart_hub: s 0 0\n"
                "hub: n 1 1\nhub: p 1 -1 [zone=priority]\n"
                "end_hub: e 2 0\nconnection: s-n\nconnection: s-p\n"
                "connection: n-e\nconnection: p-e\n")
    assert out[0] == "D1-p"


def test_drones_split_over_parallel_paths(load: Loader) -> None:
    out = lines(load, "nb_drones: 2\nstart_hub: s 0 0\nhub: a 1 1\n"
                "hub: b 1 -1\nend_hub: e 2 0\nconnection: s-a\n"
                "connection: s-b\nconnection: a-e\nconnection: b-e\n")
    assert len(out) == 2  # both fly at once on different branches


def test_blocked_zone_is_never_entered(load: Loader) -> None:
    out = lines(load, "nb_drones: 1\nstart_hub: s 0 0\n"
                "hub: x 1 1 [zone=blocked]\nhub: a 1 -1\nend_hub: e 2 0\n"
                "connection: s-x\nconnection: x-e\nconnection: s-a\n"
                "connection: a-e\n")
    assert out == ["D1-a", "D1-e"]


def test_no_route_returns_none(load: Loader) -> None:
    net = load("nb_drones: 1\nstart_hub: s 0 0\nhub: x 1 0 [zone=blocked]\n"
               "end_hub: e 2 0\nconnection: s-x\nconnection: x-e\n")
    assert TimeExpandedPlanner(net).plan_next() is None


def test_many_drones_complete(load: Loader) -> None:
    out = lines(load, "nb_drones: 200\nstart_hub: s 0 0\n"
                "hub: a 1 0 [max_drones=5]\nend_hub: e 2 0\n"
                "connection: s-a [max_link_capacity=5]\n"
                "connection: a-e [max_link_capacity=5]\n")
    assert len(out) == 41  # 5 drones per turn, plus the latency
