"""Movement record."""
from dataclasses import dataclass

from src.models.zone import Zone


@dataclass
class Movement:
    """One drone movement printed on a turn line."""

    drone_id: int
    current: Zone
    destination: Zone
