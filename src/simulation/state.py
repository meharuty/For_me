"""Simulation state."""
from src.models.drone import Drone
from src.models.zone import Zone


class SimulationState:
    """Drones plus the current turn counter."""

    def __init__(
        self,
        drones: list[Drone],
        start: Zone | None = None,
        end: Zone | None = None,
    ) -> None:
        """Store the drones and optional start/end zones."""
        self.drones = drones
        self.start = start
        self.end = end
        self.turn = 0

    def drones_at(self, zone_name: str) -> list[Drone]:
        """Return the drones currently resting in a zone."""
        return [
            drone
            for drone in self.drones
            if drone.curr_location.name == zone_name
        ]
