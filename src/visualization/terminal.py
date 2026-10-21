"""Colored terminal replay of a finished simulation."""
import time

from src.models.network import Network
from src.models.zone import ZoneType
from src.simulation.replay import Replay
from src.visualization.analytics import SimulationAnalytics
from src.visualization.colors import Painter

BAR_WIDTH = 30
FLIGHT_CODE = "33"


class TerminalVisualizer:
    """Prints the simulation turn by turn using the zones' colors."""

    def __init__(
        self,
        network: Network,
        replay: Replay,
        delay: float = 0.6,
        step: bool = False,
        painter: Painter | None = None,
    ) -> None:
        """Store the data to show and the pacing options."""
        self.network = network
        self.frames = replay.frames
        self.analytics = SimulationAnalytics(network, replay)
        self.delay = delay
        self.step = step
        self.painter = painter or Painter()

    def _legend(self) -> list[str]:
        """Describe zones and links once, before the replay."""
        start, end = self.network.start, self.network.end
        lines = ["Zones:"]
        for zone in self.network.zones:
            tags: list[str] = []
            if zone == start:
                tags.append("START")
            elif zone == end:
                tags.append("END")
            else:
                tags.append(f"cap {zone.max_drones}")
            if zone.zone_type != ZoneType.NORMAL:
                tags.append(zone.zone_type.value)
            name = self.painter.zone(f"{zone.name:<22}", zone)
            lines.append(
                f"  {name}({zone.x},{zone.y}) {', '.join(tags)}"
            )
        lines.append("Links:")
        for conn in self.network.connections:
            lines.append(
                f"  {conn.zone_a.name} - {conn.zone_b.name} "
                f"(cap {conn.max_link_capacity})"
            )
        return lines

    def _turn(self, index: int) -> list[str]:
        """Render one turn: moves, occupancy and links in flight."""
        frame = self.frames[index]
        start, end = self.network.start, self.network.end
        total = len(self.analytics.drone_ids)
        done = self.analytics.delivered(index)
        filled = BAR_WIDTH * (index + 1) // len(self.frames)
        bar = "#" * filled + "." * (BAR_WIDTH - filled)
        lines = [
            f"Turn {index + 1}/{len(self.frames)} [{bar}] "
            f"delivered {done}/{total}"
        ]
        moves = [
            self.painter.zone(Replay.token(m, frame), m.destination)
            for m in frame.movements
        ]
        lines.append("  moves:  " + (" ".join(moves) or "(all waiting)"))
        counts = self.analytics.zone_counts(index)
        held: list[str] = []
        for zone in self.network.zones:
            count = counts.get(zone.name, 0)
            if not count or zone == end:
                continue
            cap = "" if zone == start else f"/{zone.max_drones}"
            held.append(self.painter.zone(f"{zone.name} {count}{cap}", zone))
        lines.append("  zones:  " + (" | ".join(held) or "-"))
        flights = [
            self.painter.paint(
                f"{m.current.name}=>{m.destination.name}", FLIGHT_CODE
            )
            for m in frame.in_transit.values()
        ]
        if flights:
            lines.append("  flying: " + " ".join(flights))
        return lines

    def _pause(self) -> None:
        """Wait for Enter (--step) or for the configured delay."""
        if self.step:
            try:
                input("  [Enter] next turn ")
            except EOFError:
                self.step = False
        elif self.delay > 0:
            time.sleep(self.delay)

    def run(self) -> None:
        """Print the legend, every turn, then a short summary."""
        if not self.frames:
            return
        print("\n".join(self._legend()))
        print()
        for index in range(len(self.frames)):
            print("\n".join(self._turn(index)))
            self._pause()
        busiest = ", ".join(
            f"{name} ({turns})"
            for name, turns in self.analytics.hotspots(len(self.frames) - 1)
        )
        print(f"\nDone in {len(self.frames)} turns. "
              f"Busiest zones (drone-turns): {busiest or '-'}\n")
