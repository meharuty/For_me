"""Zone model."""
from dataclasses import dataclass
from enum import Enum


class ZoneType(Enum):
    """Kinds of zones and their movement rules."""

    NORMAL = "normal"
    BLOCKED = "blocked"
    RESTRICTED = "restricted"
    PRIORITY = "priority"


@dataclass(eq=True, unsafe_hash=True)
class Zone:
    """A node of the network."""

    name: str
    x: int
    y: int
    zone_type: ZoneType
    color: str
    max_drones: int = 1
