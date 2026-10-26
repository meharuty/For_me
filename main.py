import argparse
import sys

from src.algorithms.graph import Graph
from src.algorithms.scheduler import Scheduler
from src.models.network import Network
from src.parser.parser import MapParser
from src.simulation.checker import SolutionChecker
from src.simulation.replay import Replay
from src.simulation.simulation import Simulation
from src.simulation.state import SimulationState
from src.visualization.gui import GraphicalVisualizer
from src.visualization.terminal import TerminalVisualizer


class FlyInApp:
    """Orchestrates parsing, planning, verification and display."""

    def __init__(self, args: argparse.Namespace) -> None:
        """Store the command-line options."""
        self.args = args

    def _simulate(self, network: Network) -> Simulation:
        """Plan every drone, run the simulation and return it."""
        scheduler = Scheduler(network)
        drones = scheduler.create_drones()
        state = SimulationState(drones, network.start, network.end)
        simulation = Simulation(scheduler, state)
        simulation.run(max_turns=self.args.max_turns)
        return simulation

    def _verify(self, network: Network, replay: Replay) -> None:
        """Re-check the printed output against every subject rule."""
        errors = SolutionChecker(network).check(replay.lines())
        if errors:
            raise RuntimeError(
                "internal error, invalid plan: " + "; ".join(errors[:3])
            )

    def _display(self, network: Network, replay: Replay) -> None:
        """Show the visual replay, then print the official output."""
        lines = replay.lines()
        if self.args.gui:
            print("\n".join(lines))
            GraphicalVisualizer(
                network, replay,
                trails=self.args.trails, heatmap=self.args.heatmap,
            ).run()
            return
        if not (self.args.plain or self.args.no_visual):
            TerminalVisualizer(
                network, replay,
                delay=self.args.delay, step=self.args.step,
            ).run()
        print("\n".join(lines))

    def run(self) -> int:
        """Run the whole pipeline; return a process exit code."""
        try:
            network = MapParser().parse(self.args.map_file)
            if not Graph(network).has_path(network.start, network.end):
                print(
                    "Error: map is unsolvable (no path from start to end).",
                    file=sys.stderr,
                )
                return 1
            replay = Replay(self._simulate(network))
            self._verify(network, replay)
            self._display(network, replay)
        except (ValueError, RuntimeError) as error:
            print(f"Error: {error}", file=sys.stderr)
            return 1
        except KeyboardInterrupt:
            print("\nInterrupted.", file=sys.stderr)
            return 130
        except Exception as error:
            print(f"Error: unexpected failure: {error}", file=sys.stderr)
            return 1
        return 0


def build_arg_parser() -> argparse.ArgumentParser:
    """Define the command-line interface."""
    parser = argparse.ArgumentParser(
        description="Fly-in: drone routing simulation",
    )
    parser.add_argument("map_file", help="path to the map file")
    parser.add_argument(
        "--delay", type=float, default=0.6,
        help="seconds between turns in the terminal replay (default: 0.6)",
    )
    parser.add_argument(
        "--step", action="store_true",
        help="press Enter to advance each turn",
    )
    parser.add_argument(
        "--no-visual", action="store_true",
        help="skip the colored replay, print only the output lines",
    )
    parser.add_argument(
        "--gui", action="store_true",
        help="open the animated graphical window (tkinter)",
    )
    parser.add_argument(
        "--trails", action="store_true",
        help="with --gui: start with drone trails visible",
    )
    parser.add_argument(
        "--heatmap", action="store_true",
        help="with --gui: start with the congestion heatmap on",
    )
    parser.add_argument(
        "--plain", action="store_true",
        help="print only the official uncolored output",
    )
    parser.add_argument(
        "--max-turns", type=int, default=100000,
        help="safety limit on simulation turns (default: 100000)",
    )
    return parser


def main() -> int:
    """Parse arguments and launch the application."""
    args = build_arg_parser().parse_args()
    return FlyInApp(args).run()


if __name__ == "__main__":
    sys.exit(main())
