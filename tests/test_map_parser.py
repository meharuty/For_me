"""Parser behaviour: valid maps and every error the subject lists."""
import pytest

from src.models.zone import ZoneType
from src.parser.parser import MapParser
from tests.conftest import Loader, MapWriter

BASE = "nb_drones: 2\nstart_hub: s 0 0\nend_hub: e 1 0\n"


def test_simple_valid_map(load: Loader) -> None:
    net = load(BASE + "hub: m 5 5\nconnection: s-m\nconnection: m-e\n")
    assert net.nb_drones == 2
    assert [z.name for z in net.zones] == ["s", "e", "m"]
    assert len(net.connections) == 2
    assert net.start.name == "s" and net.end.name == "e"


def test_metadata_any_order_and_defaults(load: Loader) -> None:
    net = load(BASE + "hub: m 1 2 [max_drones=3 color=red zone=priority]\n"
               "hub: n 2 2\n")
    m = next(z for z in net.zones if z.name == "m")
    n = next(z for z in net.zones if z.name == "n")
    assert (m.zone_type, m.color, m.max_drones) == (
        ZoneType.PRIORITY, "red", 3)
    assert (n.zone_type, n.color, n.max_drones) == (
        ZoneType.NORMAL, "none", 1)


def test_connection_capacity(load: Loader) -> None:
    net = load(BASE + "connection: s-e [max_link_capacity=5]\n")
    assert net.connections[0].max_link_capacity == 5


def test_max_drones_ignored_on_start_and_end(load: Loader) -> None:
    net = load("nb_drones: 1\nstart_hub: s 0 0 [max_drones=9]\n"
               "end_hub: e 1 0 [max_drones=9]\n")
    assert net.start.max_drones == 1


def test_comments_and_blank_lines(load: Loader) -> None:
    net = load("# hi\n\n" + BASE + "  # indented\nconnection: s-e\n")
    assert len(net.connections) == 1


def test_parser_is_reusable(write_map: MapWriter) -> None:
    parser = MapParser()
    first = parser.parse(write_map(BASE))
    second = parser.parse(write_map(BASE.replace("2", "7", 1)))
    assert (first.nb_drones, second.nb_drones) == (2, 7)


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ("start_hub: s 0 0\nend_hub: e 1 0\n", "Missing nb_drones"),
        ("nb_drones: 2\nend_hub: e 1 0\n", "Missing start_hub"),
        ("nb_drones: 2\nstart_hub: s 0 0\n", "Missing end_hub"),
        ("nb_drones: 0\n" + BASE[13:], "positive integer"),
        ("nb_drones: x\n" + BASE[13:], "positive integer"),
        (BASE + "nb_drones: 3\n", "Duplicate nb_drones"),
        (BASE + "start_hub: t 5 5\n", "Duplicate start_hub"),
        (BASE + "end_hub: t 5 5\n", "Duplicate end_hub"),
        (BASE + "hub: s 5 5\n", "Duplicate zone name"),
        (BASE + "hub: a-b 5 5\n", "cannot contain dashes"),
        (BASE + "hub: a 5\n", "Invalid zone definition"),
        (BASE + "hub: a x 5\n", "must be integers"),
        (BASE + "hub: a 5 5 [zone=lava]\n", "Invalid zone type"),
        (BASE + "hub: a 5 5 [max_drones=0]\n", "positive integer"),
        (BASE + "hub: a 5 5 [bad=1]\n", "Unknown metadata key"),
        (BASE + "hub: a 5 5 [color=red\n", "missing closing"),
        (BASE + "hub: a 5 5 color=red]\n", "missing opening"),
        (BASE + "hub: a [color=red] 5 5\n", "must appear at the end"),
        (BASE + "hub: a 5 5 [color=red] [zone=normal]\n", "Only one"),
        (BASE + "connection: s-x\n", "Zone 'x' does not exist"),
        (BASE + "connection: s-s\n", "itself"),
        (BASE + "connection: s-e\nconnection: e-s\n", "Duplicate connection"),
        (BASE + "connection: s-e-s\n", "Invalid connection"),
        (BASE + "connection: s-e [capacity=2]\n", "Unknown metadata key"),
        (BASE + "connection: s-e [max_link_capacity=-1]\n", "positive"),
        (BASE + "mystery: 1\n", "Unknown line type"),
    ],
)
def test_errors(load: Loader, text: str, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        load(text)


def test_connection_must_follow_its_zones(load: Loader) -> None:
    """The subject: connections link previously defined zones."""
    with pytest.raises(ValueError, match="does not exist"):
        load("nb_drones: 1\nconnection: s-e\n"
             "start_hub: s 0 0\nend_hub: e 1 0\n")


def test_error_reports_line_number(load: Loader) -> None:
    with pytest.raises(ValueError, match=r"Line 4:"):
        load("nb_drones: 2\nstart_hub: s 0 0\nend_hub: e 1 0\n"
             "hub: m x 0\n")


def test_missing_file() -> None:
    with pytest.raises(ValueError, match="Could not read"):
        MapParser().parse("/nonexistent/map.txt")
