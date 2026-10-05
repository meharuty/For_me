"""Analytics behind the graphical view (no display needed)."""
from src.visualization.analytics import SimulationAnalytics
from src.visualization.colors import heat_color
from tests.conftest import Loader, solve

MAP = ("nb_drones: 3\nstart_hub: s 0 0\nhub: a 1 0 [max_drones=1]\n"
       "hub: r 2 0 [zone=restricted max_drones=3]\nend_hub: e 3 0\n"
       "connection: s-a [max_link_capacity=3]\n"
       "connection: a-r [max_link_capacity=3]\n"
       "connection: r-e [max_link_capacity=3]\n")


def build(load: Loader) -> SimulationAnalytics:
    net = load(MAP)
    return SimulationAnalytics(net, solve(net))


def test_initial_state_has_everyone_at_start(load: Loader) -> None:
    an = build(load)
    assert an.zone_counts(-1) == {"s": 3}
    assert an.delivered(-1) == 0


def test_final_state_delivers_everyone(load: Loader) -> None:
    an = build(load)
    last = len(an.frames) - 1
    assert an.delivered(last) == 3
    assert an.zone_counts(last) == {"e": 3}


def test_in_flight_drones_are_not_resting(load: Loader) -> None:
    an = build(load)
    for i in range(len(an.frames)):
        resting = sum(an.zone_counts(i).values())
        flying = len(an.frames[i].in_transit)
        assert resting + flying == 3


def test_heat_is_normalised_and_cumulative(load: Loader) -> None:
    an = build(load)
    last = len(an.frames) - 1
    heat = an.zone_heat(last)
    assert max(heat.values()) == 1.0
    assert all(0 <= v <= 1 for v in heat.values())
    assert "s" not in heat and "e" not in heat
    for i in range(1, last + 1):
        for name, value in an.zone_heat(i - 1).items():
            assert heat[name] >= value or an.zone_heat(i)[name] >= value


def test_hotspots_sorted_busiest_first(load: Loader) -> None:
    an = build(load)
    spots = an.hotspots(len(an.frames) - 1, top=5)
    values = [v for _, v in spots]
    assert values == sorted(values, reverse=True) and spots


def test_link_heat_counts_crossings(load: Loader) -> None:
    an = build(load)
    heat = an.link_heat(len(an.frames) - 1)
    assert max(heat.values()) == 1.0
    assert frozenset(("s", "a")) in heat


def test_trail_follows_the_route(load: Loader) -> None:
    an = build(load)
    names = [z.name for z in an.trail(1, len(an.frames) - 1)]
    assert names == ["s", "a", "r", "e"]
    assert [z.name for z in an.trail(1, -1)] == ["s"]


def test_heat_color_gradient_ends_differ() -> None:
    assert heat_color(0) != heat_color(1)
    assert heat_color(-5) == heat_color(0) and heat_color(9) == heat_color(1)
