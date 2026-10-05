"""Network model."""
from dataclasses import dataclass

from .connection import Connection
from .zone import Zone


@dataclass
class Network:
    """A parsed map: drones, zones, connections, start and end."""

    nb_drones: int
    zones: list[Zone]
    connections: list[Connection]
    start: Zone
    end: Zone
