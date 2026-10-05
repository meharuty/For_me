"""Every subject map must be valid and reach the optimum turn count."""
import pytest

from src.parser.parser import MapParser
from src.simulation.checker import SolutionChecker
from tests.conftest import ROOT, solve

OPTIMUM = {
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


@pytest.mark.parametrize(("name", "optimum"), OPTIMUM.items())
def test_map_reaches_optimum_and_is_valid(name: str, optimum: int) -> None:
    network = MapParser().parse(str(ROOT / "maps" / f"{name}.txt"))
    lines = solve(network).lines()
    assert SolutionChecker(network).check(lines) == []
    assert len(lines) == optimum
