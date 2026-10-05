"""Validator helpers."""
import pytest

from src.models.connection import Connection
from src.models.zone import Zone, ZoneType
from src.parser.validator import (
    CommonValidator,
    ConnectionValidator,
    MapStructureValidator,
    ZoneValidator,
)


def zone(name: str) -> Zone:
    return Zone(name, 0, 0, ZoneType.NORMAL, "none")


@pytest.mark.parametrize(("value", "expected"),
                         [("1", 1), ("10", 10), ("999", 999)])
def test_positive_integer_valid(value: str, expected: int) -> None:
    assert CommonValidator.positive_integer(value, "x") == expected


@pytest.mark.parametrize("value", ["0", "-1", "abc", "", "1.5"])
def test_positive_integer_invalid(value: str) -> None:
    with pytest.raises(ValueError):
        CommonValidator.positive_integer(value, "x")


def test_zone_names() -> None:
    assert ZoneValidator.name("hub1") == "hub1"
    for bad in ("", "a b", "a-b"):
        with pytest.raises(ValueError):
            ZoneValidator.name(bad)


def test_zone_types() -> None:
    assert ZoneValidator.zone_type("priority") == ZoneType.PRIORITY
    with pytest.raises(ValueError, match="Invalid zone type"):
        ZoneValidator.zone_type("lava")


def test_unique_zone_name() -> None:
    with pytest.raises(ValueError, match="Duplicate zone name"):
        ZoneValidator.unique_name({"A": zone("A")}, zone("A"))


def test_connection_rules() -> None:
    zones = {"A": zone("A"), "B": zone("B")}
    ConnectionValidator.zones_exist("A", "B", zones)
    with pytest.raises(ValueError, match="Zone 'C' does not exist"):
        ConnectionValidator.zones_exist("A", "C", zones)
    with pytest.raises(ValueError, match="itself"):
        ConnectionValidator.not_self_loop("A", "A")
    existing = Connection(zones["A"], zones["B"])
    with pytest.raises(ValueError, match="Duplicate connection"):
        ConnectionValidator.unique(
            [existing], Connection(zones["B"], zones["A"]))


def test_required_fields() -> None:
    z = zone("z")
    MapStructureValidator.required_fields(1, z, z)
    for args, message in (((None, z, z), "nb_drones"),
                          ((1, None, z), "start_hub"),
                          ((1, z, None), "end_hub")):
        with pytest.raises(ValueError, match=message):
            MapStructureValidator.required_fields(*args)
