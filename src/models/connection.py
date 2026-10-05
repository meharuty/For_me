"""Connection model."""
from dataclasses import dataclass

from .zone import Zone


@dataclass
class Connection:
    """A bidirectional link between two zones."""

    zone_a: Zone
    zone_b: Zone
    max_link_capacity: int = 1

    @property
    def name(self) -> str:
        """Return the ``a-b`` name of the connection."""
        return f"{self.zone_a.name}-{self.zone_b.name}"
