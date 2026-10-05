"""Map file parser."""
from src.models.connection import Connection
from src.models.network import Network
from src.models.zone import Zone
from src.parser.metadata import MetadataParser
from src.parser.validator import (
    CommonValidator,
    ConnectionValidator,
    MapStructureValidator,
    ZoneValidator,
)

ZONE_METADATA_KEYS = {"zone", "color", "max_drones"}
CONNECTION_METADATA_KEYS = {"max_link_capacity"}
_HUB_PREFIXES = ("start_hub:", "end_hub:", "hub:")


class MapParser:
    """Parse a map file into a Network object.

    Lines are handled in order, so a connection may only reference
    zones that were defined on an earlier line (as the subject states).
    Every error is reported with its line number.
    """

    def __init__(self) -> None:
        """Create a parser with an empty state."""
        self._reset()

    def _reset(self) -> None:
        """Reset parser state so an instance can be reused."""
        self._nb_drones: int | None = None
        self._zones: dict[str, Zone] = {}
        self._start: Zone | None = None
        self._end: Zone | None = None
        self._connections: list[Connection] = []

    # ---------- public API ----------

    def parse(self, file_path: str) -> Network:
        """Parse a map file and return a Network object.

        Raises:
            ValueError: on any unreadable file or invalid content.
        """
        self._reset()
        try:
            with open(file_path, "r", encoding="utf-8") as file:
                for number, raw_line in enumerate(file, start=1):
                    line = raw_line.strip()
                    if not line or line.startswith("#"):
                        continue
                    try:
                        self._parse_line(line)
                    except ValueError as error:
                        raise ValueError(
                            f"Line {number}: {error}"
                        ) from None
        except (OSError, UnicodeDecodeError) as error:
            raise ValueError(
                f"Could not read map file '{file_path}': {error}"
            ) from None

        MapStructureValidator.required_fields(
            self._nb_drones, self._start, self._end
        )
        assert self._nb_drones is not None
        assert self._start is not None
        assert self._end is not None
        return Network(
            nb_drones=self._nb_drones,
            zones=list(self._zones.values()),
            connections=self._connections,
            start=self._start,
            end=self._end,
        )

    # ---------- line dispatch ----------

    def _parse_line(self, line: str) -> None:
        """Dispatch a line to its corresponding parser."""
        if line.startswith("nb_drones:"):
            self._parse_nb_drones(line)
        elif line.startswith(_HUB_PREFIXES):
            kind = line.partition(":")[0].strip()
            self._parse_hub(line, kind)
        elif line.startswith("connection:"):
            connection = self._parse_connection(line)
            ConnectionValidator.unique(self._connections, connection)
            self._connections.append(connection)
        else:
            raise ValueError(f"Unknown line type: '{line}'")

    def _parse_nb_drones(self, line: str) -> None:
        """Parse the nb_drones definition."""
        if self._nb_drones is not None:
            raise ValueError("Duplicate nb_drones definition")
        value = line.partition(":")[2].strip()
        self._nb_drones = CommonValidator.positive_integer(
            value, "nb_drones"
        )

    # ---------- zones ----------

    def _parse_hub(self, line: str, kind: str) -> None:
        """Parse a start_hub, end_hub or regular hub line."""
        if kind == "start_hub" and self._start is not None:
            raise ValueError("Duplicate start_hub definition")
        if kind == "end_hub" and self._end is not None:
            raise ValueError("Duplicate end_hub definition")
        zone = self._build_zone(
            line, is_start_or_end=kind in {"start_hub", "end_hub"}
        )
        ZoneValidator.unique_name(self._zones, zone)
        self._zones[zone.name] = zone
        if kind == "start_hub":
            self._start = zone
        elif kind == "end_hub":
            self._end = zone

    def _build_zone(self, line: str, *, is_start_or_end: bool) -> Zone:
        """Build a Zone from a hub definition."""
        content = line.partition(":")[2].strip()
        metadata, content = self._extract_metadata(content)
        MetadataParser.ensure_known_keys(
            metadata, ZONE_METADATA_KEYS, "a hub"
        )
        parts = content.split()
        if len(parts) != 3:
            raise ValueError(
                "Invalid zone definition. Expected: <name> <x> <y>"
            )
        name = ZoneValidator.name(parts[0])
        try:
            x, y = int(parts[1]), int(parts[2])
        except ValueError:
            raise ValueError(
                "Zone coordinates must be integers"
            ) from None
        zone_type = ZoneValidator.zone_type(metadata.get("zone", "normal"))
        max_drones = CommonValidator.positive_integer(
            metadata.get("max_drones", "1"), "max_drones"
        )
        if is_start_or_end:
            max_drones = 1  # capacity is ignored on start/end hubs
        return Zone(
            name=name,
            x=x,
            y=y,
            zone_type=zone_type,
            color=metadata.get("color", "none"),
            max_drones=max_drones,
        )

    # ---------- connections ----------

    def _parse_connection(self, line: str) -> Connection:
        """Parse a connection definition."""
        content = line.partition(":")[2].strip()
        metadata, content = self._extract_metadata(content)
        MetadataParser.ensure_known_keys(
            metadata, CONNECTION_METADATA_KEYS, "a connection"
        )
        if content.count("-") != 1:
            raise ValueError(
                "Invalid connection definition. "
                "Expected: <zone_a>-<zone_b>"
            )
        name_a, name_b = (part.strip() for part in content.split("-"))
        if not name_a or not name_b:
            raise ValueError("Connection must contain two zone names")
        ConnectionValidator.not_self_loop(name_a, name_b)
        ConnectionValidator.zones_exist(name_a, name_b, self._zones)
        capacity = CommonValidator.positive_integer(
            metadata.get("max_link_capacity", "1"), "max_link_capacity"
        )
        return Connection(
            zone_a=self._zones[name_a],
            zone_b=self._zones[name_b],
            max_link_capacity=capacity,
        )

    # ---------- metadata ----------

    @staticmethod
    def _extract_metadata(
        content: str,
    ) -> tuple[dict[str, str], str]:
        """Split a definition from its optional trailing ``[...]`` block.

        Valid:   ``A 1 2`` and ``A 1 2 [color=red]``.
        Invalid: metadata before the coordinates, unbalanced or repeated
        brackets, or text after the closing bracket.
        """
        has_opening = "[" in content
        has_closing = "]" in content
        if not has_opening and not has_closing:
            return {}, content
        if not has_opening:
            raise ValueError("Invalid metadata: missing opening '['")
        if not has_closing:
            raise ValueError("Invalid metadata: missing closing ']'")
        if content.count("[") != 1 or content.count("]") != 1:
            raise ValueError("Only one metadata block is allowed")
        start = content.find("[")
        definition = content[:start].strip()
        metadata_text = content[start:].strip()
        if not metadata_text.endswith("]"):
            raise ValueError(
                "Metadata must appear at the end of the definition"
            )
        return MetadataParser.parse(metadata_text), definition
