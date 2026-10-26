from src.models.network import Network
from src.models.zone import ZoneType


IN_FLIGHT = "<in flight>"


class SolutionChecker:
    """Replays the printed output lines and checks every subject rule.

    It only trusts the ``D<ID>-<zone>`` / ``D<ID>-<a>-<b>`` text, so it
    cannot share a bug with the planner that produced the plan.
    """

    def __init__(self, network: Network) -> None:
        """Index zones and links of the network."""
        self.network = network
        self.zones = {zone.name: zone for zone in network.zones}
        self.links = {
            frozenset((c.zone_a.name, c.zone_b.name)): c
            for c in network.connections
        }

    def check(self, lines: list[str]) -> list[str]:
        """Return a list of rule violations (empty means valid)."""
        errors: list[str] = []
        start = self.network.start.name
        end = self.network.end.name
        where: dict[int, str] = {
            i: start for i in range(1, self.network.nb_drones + 1)
        }
        flying: dict[int, tuple[str, str]] = {}
        for turn, line in enumerate(lines, start=1):
            starts: dict[frozenset[str], int] = {}
            seen: set[int] = set()
            for token in line.split():
                self._apply(
                    turn, token, where, flying, starts, seen, errors
                )
            for drone_id in flying:
                if drone_id not in seen:
                    errors.append(
                        f"turn {turn}: D{drone_id} stalled on a connection"
                    )
            self._check_capacity(turn, where, starts, errors)
        for drone_id, zone in where.items():
            if zone != end:
                errors.append(f"D{drone_id} never reaches the end zone")
        return errors

    def _apply(
        self,
        turn: int,
        token: str,
        where: dict[int, str],
        flying: dict[int, tuple[str, str]],
        starts: dict[frozenset[str], int],
        seen: set[int],
        errors: list[str],
    ) -> None:
        """Apply one ``D<ID>-<target>`` token to the replayed state."""
        head, _, target = token.partition("-")
        if not head.startswith("D") or not head[1:].isdigit() or not target:
            errors.append(f"turn {turn}: malformed token '{token}'")
            return
        drone_id = int(head[1:])
        if drone_id not in where or drone_id in seen:
            errors.append(f"turn {turn}: bad or repeated drone '{head}'")
            return
        seen.add(drone_id)
        if drone_id in flying:
            origin, dest = flying.pop(drone_id)
            if target != dest:
                errors.append(
                    f"turn {turn}: D{drone_id} must land in {dest}"
                )
            where[drone_id] = dest
            return
        current = where[drone_id]
        if current == IN_FLIGHT:
            errors.append(f"turn {turn}: D{drone_id} moved mid-flight")
            return
        if "-" in target:
            first, _, second = target.partition("-")
            if first != current or second not in self.zones:
                errors.append(f"turn {turn}: bad connection '{token}'")
                return
            dest_name = second
            if self.zones[dest_name].zone_type != ZoneType.RESTRICTED:
                errors.append(f"turn {turn}: '{token}' is not restricted")
            flying[drone_id] = (current, dest_name)
            where[drone_id] = IN_FLIGHT
        else:
            dest_name = target
            if dest_name not in self.zones:
                errors.append(f"turn {turn}: unknown zone '{dest_name}'")
                return
            if self.zones[dest_name].zone_type == ZoneType.RESTRICTED:
                errors.append(
                    f"turn {turn}: '{token}' skips the 2-turn crossing"
                )
            where[drone_id] = dest_name
        key = frozenset((current, dest_name))
        if key not in self.links:
            errors.append(f"turn {turn}: no connection {current}-{dest_name}")
            return
        if self.zones[dest_name].zone_type == ZoneType.BLOCKED:
            errors.append(f"turn {turn}: D{drone_id} enters blocked zone")
        starts[key] = starts.get(key, 0) + 1

    def _check_capacity(
        self,
        turn: int,
        where: dict[int, str],
        starts: dict[frozenset[str], int],
        errors: list[str],
    ) -> None:
        """Check link and zone capacities at the end of a turn."""
        for key, used in starts.items():
            cap = self.links[key].max_link_capacity
            if used > cap:
                errors.append(
                    f"turn {turn}: link {'-'.join(sorted(key))} "
                    f"used {used}/{cap}"
                )
        counts: dict[str, int] = {}
        for zone_name in where.values():
            counts[zone_name] = counts.get(zone_name, 0) + 1
        special = {self.network.start.name, self.network.end.name}
        for name, count in counts.items():
            if name in special or name == IN_FLIGHT:
                continue
            if count > self.zones[name].max_drones:
                errors.append(
                    f"turn {turn}: zone {name} holds "
                    f"{count}/{self.zones[name].max_drones}"
                )
