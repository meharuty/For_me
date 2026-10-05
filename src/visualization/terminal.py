"""Colored terminal replay of a Fly-in simulation."""
import time
from collections import Counter

from src.models.network import Network
from src.models.zone import Zone, ZoneType
from src.simulation.replay import Frame, Replay
from src.visualization.analytics import SimulationAnalytics
from src.visualization.colors import Painter

TYPE_MARKERS: dict[ZoneType, str] = {
    ZoneType.NORMAL: " ",
    ZoneType.PRIORITY: "*",
    ZoneType.RESTRICTED: "!",
    ZoneType.BLOCKED: "#",
}


class TerminalVisualizer:
    """Renders the map, each turn and a final summary in the terminal."""

    def __init__(
        self,
        network: Network,
        replay: Replay,
        painter: Painter | None = None,
    ) -> None:
        """Keep the replay and build the analytics used by the summary."""
        self.network = network
        self.replay = replay
        self.frames = replay.frames
        self.analytics = SimulationAnalytics(network, replay)
        self.painter = painter or Painter()
        self.total = network.nb_drones

    # ---------- small helpers ----------

    def _capacity(self, zone: Zone) -> str:
        """Capacity label of a zone."""
        if zone == self.network.start or zone == self.network.end:
            return "inf"
        return str(zone.max_drones)

    def _tag(self, zone: Zone) -> str:
        """Role label of a zone."""
        if zone == self.network.start:
            return "START"
        if zone == self.network.end:
            return "END"
        return zone.zone_type.value

    def _format_move(self, token: str, frame: Frame, drone_id: int,
                     dest: Zone) -> str:
        """Color a move token: yellow in flight, zone color on arrival."""
        if drone_id in frame.in_transit:
            return self.painter.paint(token, "33")
        return self.painter.zone(token, dest)

    # ---------- legend ----------

    def show_legend(self) -> None:
        """Print every zone and connection with its properties."""
        p = self.painter
        print(p.paint("=== MAP ===", "1"))
        print(
            "Markers: > start  $ end  * priority  "
            "! restricted(2 turns)  # blocked"
        )
        for zone in self.network.zones:
            name = p.zone(f"{zone.name:<16}", zone)
            print(
                f"  {name} ({zone.x:>3},{zone.y:>3})  "
                f"{self._tag(zone):<10} cap={self._capacity(zone)}"
            )
        print(p.paint("Connections:", "1"))
        for conn in self.network.connections:
            a = p.zone(conn.zone_a.name, conn.zone_a)
            b = p.zone(conn.zone_b.name, conn.zone_b)
            print(f"  {a} <-> {b}  cap={conn.max_link_capacity}")
        print()

    # ---------- grid ----------

    def _label(self, zone: Zone, count: int) -> str:
        """Grid label: marker, name and resting drone count."""
        marker = TYPE_MARKERS[zone.zone_type]
        if zone == self.network.start:
            marker = ">"
        elif zone == self.network.end:
            marker = "$"
        suffix = f"[{count}]" if count else ""
        return f"{marker}{zone.name}{suffix}"

    def render_grid(self, frame: Frame | None = None) -> str:
        """Draw zones on a compressed coordinate grid with drone counts."""
        zones = self.network.zones
        xs = sorted({z.x for z in zones})
        ys = sorted({z.y for z in zones}, reverse=True)
        counts: Counter[str] = Counter()
        if frame is not None:
            for drone_id, zone in frame.positions.items():
                if drone_id not in frame.in_transit:
                    counts[zone.name] += 1
        else:
            counts[self.network.start.name] = self.total
        width = max(len(z.name) for z in zones) + 7
        cells: dict[tuple[int, int], Zone] = {}
        for z in zones:
            col, row = xs.index(z.x), ys.index(z.y)
            while (col, row) in cells:
                col += 1
            cells[(col, row)] = z
        n_cols = max(col for col, _ in cells) + 1
        rows = []
        for row in range(len(ys)):
            parts = []
            for col in range(n_cols):
                cell = cells.get((col, row))
                if cell is None:
                    parts.append(" " * width)
                    continue
                count = counts[cell.name]
                text = self._label(cell, count).center(width)
                code = self.painter.code_for(cell.color)
                if count:
                    code = f"1;{code}" if code else "1"
                parts.append(self.painter.paint(text, code))
            rows.append(" ".join(parts).rstrip())
        return "\n\n".join(rows)

    # ---------- turn rendering ----------

    def render_turn(self, frame: Frame) -> None:
        """Print moves, grid, zone occupancy, links in flight, progress."""
        p = self.painter
        end = self.network.end
        delivered = sum(1 for z in frame.positions.values() if z == end)
        print(p.paint(f"--- Turn {frame.turn} ---", "1"))
        print("  " + " ".join(
            self._format_move(
                self.replay.token(m, frame), frame, m.drone_id,
                m.destination,
            )
            for m in frame.movements
        ))
        print()
        print(self.render_grid(frame))
        print()
        by_zone: dict[str, list[int]] = {}
        for drone_id, zone in frame.positions.items():
            if drone_id in frame.in_transit or zone == end:
                continue
            by_zone.setdefault(zone.name, []).append(drone_id)
        for zone in self.network.zones:
            ids = sorted(by_zone.get(zone.name, []))
            if not ids:
                continue
            label = p.zone(f"{zone.name:<16}", zone)
            drones = " ".join(f"D{i}" for i in ids)
            print(f"  {label} {len(ids)}/{self._capacity(zone):<3} {drones}")
        for drone_id, move in sorted(frame.in_transit.items()):
            name = f"{move.current.name}-{move.destination.name}"
            print(
                "  " + p.paint(f"{name:<16}", "33")
                + f" in flight: D{drone_id}"
            )
        bar_len = 30
        filled = bar_len * delivered // self.total
        bar = "#" * filled + "." * (bar_len - filled)
        progress = p.paint(f"[{bar}] {delivered}/{self.total}", "32")
        print(f"  Delivered {progress}\n")

    # ---------- public entry points ----------

    def play(self, delay: float = 0.6, step: bool = False) -> None:
        """Replay every turn; wait for Enter if step, else sleep delay."""
        print(self.painter.paint("=== START ===", "1"))
        print(self.render_grid(None), "\n")
        for frame in self.frames:
            self.render_turn(frame)
            if step:
                input("  [Enter] next turn ")
            elif delay > 0:
                time.sleep(delay)

    def show_summary(self) -> None:
        """Print the turn count, arrivals and the main bottlenecks."""
        p = self.painter
        end = self.network.end
        arrival: dict[int, int] = {}
        for frame in self.frames:
            for drone_id, zone in frame.positions.items():
                if zone == end and drone_id not in arrival:
                    arrival[drone_id] = frame.turn
        print(p.paint("=== SUMMARY ===", "1"))
        print(f"  Drones : {self.total}")
        print(f"  Turns  : {len(self.frames)}")
        if arrival:
            avg = sum(arrival.values()) / len(arrival)
            print(f"  Average arrival turn: {avg:.1f}")
            for drone_id, turn in sorted(arrival.items()):
                print(f"    D{drone_id:<3} arrived at turn {turn}")
        spots = self.analytics.hotspots(len(self.frames) - 1)
        if spots:
            print("  Busiest zones (drone-turns spent inside):")
            for name, value in spots:
                print(f"    {name:<18} {value}")
