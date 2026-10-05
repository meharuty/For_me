"""Graph adjacency and reachability."""
from src.algorithms.graph import Graph
from src.models.connection import Connection
from src.models.network import Network
from src.models.zone import Zone, ZoneType


def make(blocked_middle: bool = False) -> tuple[Graph, Zone, Zone]:
    kind = ZoneType.BLOCKED if blocked_middle else ZoneType.NORMAL
    a = Zone("a", 0, 0, ZoneType.NORMAL, "none")
    b = Zone("b", 1, 0, kind, "none")
    c = Zone("c", 2, 0, ZoneType.NORMAL, "none")
    iso = Zone("iso", 9, 9, ZoneType.NORMAL, "none")
    net = Network(1, [a, b, c, iso],
                  [Connection(a, b), Connection(b, c)], a, c)
    return Graph(net), a, c


def test_neighbors_are_bidirectional() -> None:
    graph, a, _ = make()
    b = graph.get_zone("b")
    assert b in graph.get_neighbors(a) and a in graph.get_neighbors(b)


def test_has_path() -> None:
    graph, a, c = make()
    assert graph.has_path(a, c)
    assert not graph.has_path(a, graph.get_zone("iso"))


def test_blocked_zone_cuts_the_path() -> None:
    graph, a, c = make(blocked_middle=True)
    assert not graph.has_path(a, c)


def test_cycle_terminates() -> None:
    a = Zone("a", 0, 0, ZoneType.NORMAL, "none")
    b = Zone("b", 1, 0, ZoneType.NORMAL, "none")
    c = Zone("c", 2, 0, ZoneType.NORMAL, "none")
    net = Network(1, [a, b, c], [Connection(a, b), Connection(b, c),
                                 Connection(c, a)], a, c)
    assert Graph(net).has_path(a, c)
