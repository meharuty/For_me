"""Display-independent analytics behind the graphical view."""
from src.models.network import Network
from src.models.zone import Zone
from src.simulation.replay import Frame, Replay

LinkKey = frozenset[str]


class SimulationAnalytics:
    """Per-turn occupancy, link usage, trails and congestion heat.

    Index ``-1`` is the initial state (before any turn); index ``i`` is
    the state right after frame ``i``. Heat values are cumulative up to
    the index and normalised by the final maximum, so colors keep a
    stable meaning while the replay advances.
    """

    def __init__(self, network: Network, replay: Replay) -> None:
        """Precompute counts, link usage and cumulative heat."""
        self.network = network
        self.frames: list[Frame] = replay.frames
        self.drone_ids = sorted(
            self.frames[0].positions) if self.frames else []
        steps = range(-1, len(self.frames))
        self._zone_counts = [self._count(i) for i in steps]
        self._link_usage = [self._usage(i) for i in steps]
        self._zone_heat = self._cumulate_zone()
        self._link_heat = self._cumulate_link()
        self._zone_max = max(self._zone_heat[-1].values(), default=0)
        self._link_max = max(self._link_heat[-1].values(), default=0)

    def anchor(self, index: int, drone_id: int) -> tuple[Zone, Zone | None]:
        """Where a drone is after ``index``: a zone, or a link in flight."""
        if index < 0:
            return self.network.start, None
        frame = self.frames[index]
        move = frame.in_transit.get(drone_id)
        if move is not None:
            return move.current, move.destination
        return frame.positions[drone_id], None

    def _count(self, index: int) -> dict[str, int]:
        """Drones resting in each zone after ``index``."""
        counts: dict[str, int] = {}
        for drone_id in self.drone_ids:
            zone, link = self.anchor(index, drone_id)
            if link is None:
                counts[zone.name] = counts.get(zone.name, 0) + 1
        return counts

    def _usage(self, index: int) -> dict[LinkKey, int]:
        """Crossings started during turn ``index`` per link."""
        usage: dict[LinkKey, int] = {}
        if index < 0:
            return usage
        previous = self.frames[index - 1].in_transit if index > 0 else {}
        for move in self.frames[index].movements:
            if move.drone_id in previous:
                continue
            key = frozenset((move.current.name, move.destination.name))
            usage[key] = usage.get(key, 0) + 1
        return usage

    def zone_counts(self, index: int) -> dict[str, int]:
        """Drones resting in each zone after ``index``."""
        return self._zone_counts[index + 1]

    def link_usage(self, index: int) -> dict[LinkKey, int]:
        """Crossings that started during turn ``index``."""
        return self._link_usage[index + 1]

    def delivered(self, index: int) -> int:
        """Number of drones at the end zone after ``index``."""
        if index < 0:
            return 0
        end = self.network.end
        return sum(
            1 for z in self.frames[index].positions.values() if z == end
        )

    def _cumulate_zone(self) -> list[dict[str, int]]:
        """Cumulative drone-turns resting in each inner zone."""
        special = {self.network.start.name, self.network.end.name}
        total: dict[str, int] = {}
        history = [dict(total)]
        for counts in self._zone_counts[1:]:
            for name, count in counts.items():
                if name not in special:
                    total[name] = total.get(name, 0) + count
            history.append(dict(total))
        return history

    def _cumulate_link(self) -> list[dict[LinkKey, int]]:
        """Cumulative crossings per link."""
        total: dict[LinkKey, int] = {}
        history: list[dict[LinkKey, int]] = [dict(total)]
        for usage in self._link_usage[1:]:
            for key, used in usage.items():
                total[key] = total.get(key, 0) + used
            history.append(dict(total))
        return history

    def zone_heat(self, index: int) -> dict[str, float]:
        """Normalised (0..1) congestion of each zone after ``index``."""
        if not self._zone_max:
            return {}
        return {
            name: value / self._zone_max
            for name, value in self._zone_heat[index + 1].items()
        }

    def link_heat(self, index: int) -> dict[LinkKey, float]:
        """Normalised (0..1) traffic of each link after ``index``."""
        if not self._link_max:
            return {}
        return {
            key: value / self._link_max
            for key, value in self._link_heat[index + 1].items()
        }

    def hotspots(self, index: int, top: int = 3) -> list[tuple[str, int]]:
        """Busiest zones as (name, drone-turns), busiest first."""
        ranked = sorted(
            self._zone_heat[index + 1].items(),
            key=lambda item: (-item[1], item[0]),
        )
        return ranked[:top]

    def trail(self, drone_id: int, index: int) -> list[Zone]:
        """Zones a drone has visited up to ``index`` (no repeats in a row)."""
        path = [self.network.start]
        for frame in self.frames[: index + 1]:
            zone = frame.positions[drone_id]
            if zone != path[-1]:
                path.append(zone)
        return path
