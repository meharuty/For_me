"""Replay frames and official output, shared by every view."""
from dataclasses import dataclass

from src.simulation.movement import Movement
from src.simulation.simulation import Simulation
from src.models.zone import Zone


@dataclass
class Frame:
    """State of the simulation right after one turn."""

    turn: int
    movements: list[Movement]
    positions: dict[int, Zone]
    in_transit: dict[int, Movement]


class Replay:
    """Frames built from a finished simulation."""

    def __init__(self, simulation: Simulation) -> None:
        """Replay the history; a move not ending at its goal is in flight."""
        self.frames: list[Frame] = []
        for index, moves in enumerate(simulation.history):
            after = simulation.position_history[index]
            transit = {
                m.drone_id: m for m in moves
                if after[m.drone_id] != m.destination
            }
            ordered = sorted(moves, key=lambda m: m.drone_id)
            self.frames.append(Frame(index + 1, ordered, after, transit))

    @staticmethod
    def token(move: Movement, frame: Frame) -> str:
        """Format one move as ``D<ID>-<zone>`` or ``D<ID>-<connection>``."""
        if move.drone_id in frame.in_transit:
            target = f"{move.current.name}-{move.destination.name}"
        else:
            target = move.destination.name
        return f"D{move.drone_id}-{target}"

    def lines(self) -> list[str]:
        """Return the official uncolored output, one line per turn."""
        return [
            " ".join(self.token(m, frame) for m in frame.movements)
            for frame in self.frames
        ]
