"""Benchmark: run every subject map and compare with its optimum."""
import sys
import time
from pathlib import Path

from src.algorithms.scheduler import Scheduler
from src.parser.parser import MapParser
from src.simulation.checker import SolutionChecker
from src.simulation.replay import Replay
from src.simulation.simulation import Simulation
from src.simulation.state import SimulationState

OPTIMUM: dict[str, int] = {
    "easy/01_linear_path": 4,
    "easy/02_simple_fork": 4,
    "easy/03_basic_capacity": 4,
    "medium/01_dead_end_trap": 8,
    "medium/02_circular_loop": 10,
    "medium/03_priority_puzzle": 6,
    "hard/01_maze_nightmare": 13,
    "hard/02_capacity_hell": 16,
    "hard/03_ultimate_challenge": 26,
    "challenger/01_the_impossible_dream": 43,
}


class Benchmark:
    """Solves each reference map, checks it and prints a table."""

    def __init__(self, root: Path) -> None:
        """Remember the repository root holding the ``maps`` folder."""
        self.root = root

    def run_map(self, name: str) -> tuple[int, int, float]:
        """Return (turns, rule violations, seconds) for one map."""
        network = MapParser().parse(str(self.root / "maps" / f"{name}.txt"))
        started = time.perf_counter()
        scheduler = Scheduler(network)
        drones = scheduler.create_drones()
        state = SimulationState(drones, network.start, network.end)
        simulation = Simulation(scheduler, state)
        simulation.run()
        seconds = time.perf_counter() - started
        lines = Replay(simulation).lines()
        errors = SolutionChecker(network).check(lines)
        return len(lines), len(errors), seconds

    def run(self) -> int:
        """Print the table; return 1 if any map is invalid or missed."""
        print(f"{'map':<38}{'turns':>6}{'optimum':>9}{'rules':>8}{'time':>9}")
        status = 0
        for name, optimum in OPTIMUM.items():
            turns, errors, seconds = self.run_map(name)
            verdict = "OK" if errors == 0 else f"{errors} ERR"
            mark = "" if turns == optimum else f"  (+{turns - optimum})"
            print(f"{name:<38}{turns:>6}{optimum:>9}{verdict:>8}"
                  f"{seconds:>8.2f}s{mark}")
            if errors or turns != optimum:
                status = 1
        return status


def main() -> int:
    """Run the benchmark from the repository root."""
    return Benchmark(Path(__file__).resolve().parent).run()


if __name__ == "__main__":
    sys.exit(main())
