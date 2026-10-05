"""Shared helpers for the test-suite."""
from pathlib import Path
from typing import Callable

import pytest

from src.algorithms.scheduler import Scheduler
from src.models.network import Network
from src.parser.parser import MapParser
from src.simulation.replay import Replay
from src.simulation.simulation import Simulation
from src.simulation.state import SimulationState

ROOT = Path(__file__).resolve().parent.parent


def solve(network: Network) -> Replay:
    """Plan and simulate a network, returning its replay."""
    scheduler = Scheduler(network)
    drones = scheduler.create_drones()
    state = SimulationState(drones, network.start, network.end)
    simulation = Simulation(scheduler, state)
    simulation.run()
    return Replay(simulation)


Loader = Callable[[str], Network]
MapWriter = Callable[[str], str]


@pytest.fixture
def write_map(tmp_path: Path) -> MapWriter:
    """Return a function writing map text to a temp file, returns path."""
    def _write(text: str) -> str:
        path = tmp_path / "map.txt"
        path.write_text(text, encoding="utf-8")
        return str(path)
    return _write


@pytest.fixture
def load(write_map: MapWriter) -> Loader:
    """Return a function parsing map text into a Network."""
    def _load(text: str) -> Network:
        return MapParser().parse(write_map(text))
    return _load
