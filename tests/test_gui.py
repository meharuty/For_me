"""Window behaviour (skipped when no display is available)."""
from typing import Iterator

import pytest

from src.parser.parser import MapParser
from src.visualization.gui import GraphicalVisualizer, Layout
from tests.conftest import ROOT, solve


@pytest.fixture
def gui() -> Iterator[GraphicalVisualizer]:
    network = MapParser().parse(
        str(ROOT / "maps/medium/02_circular_loop.txt"))
    try:
        window = GraphicalVisualizer(network, solve(network))
    except RuntimeError as error:
        pytest.skip(str(error))
    window.root.update()
    yield window
    window.root.destroy()


def test_scrubber_jumps_to_a_turn(gui: GraphicalVisualizer) -> None:
    gui.scrub.set(5)
    gui.root.update()  # Tk runs the slider command at idle time
    assert gui.index == 4 and gui.progress == 1.0
    assert gui.turn_var.get() == f"Turn 5 / {len(gui.frames)}"


def test_buttons_move_and_clamp(gui: GraphicalVisualizer) -> None:
    gui.next_turn()
    assert gui.index == 0 and gui.scrub.get() == 1
    gui.prev_turn()
    gui.prev_turn()
    assert gui.index == -1
    gui.go_to_end()
    assert gui.index == len(gui.frames) - 1
    assert gui.scrub.get() == len(gui.frames)
    gui.reset()
    assert gui.index == -1 and gui.scrub.get() == 0


def test_play_pause_and_auto_advance(gui: GraphicalVisualizer) -> None:
    gui.toggle_play()
    assert gui.playing
    gui.progress = 1.0
    gui.next_turn()
    assert gui.index == 0
    gui.toggle_play()
    assert not gui.playing


def test_trails_and_heatmap_toggles_redraw(gui: GraphicalVisualizer) -> None:
    gui.go_to_end()
    plain = len(gui.canvas.find_all())
    gui.show_heat.set(True)
    gui._redraw()
    with_heat = len(gui.canvas.find_all())
    gui.show_trails.set(True)
    gui.trail_drone.set("D2")
    gui._redraw()
    with_trail = len(gui.canvas.find_all())
    assert with_heat > plain and with_trail > with_heat


def test_layout_radius_shrinks_on_dense_maps() -> None:
    network = MapParser().parse(
        str(ROOT / "maps/challenger/01_the_impossible_dream.txt"))
    layout = Layout(network.zones)
    layout.fit(900, 600)
    assert 9 <= layout.radius < 24
    for a in network.zones:
        for b in network.zones:
            if a is not b:
                (x1, y1), (x2, y2) = layout.pos(a), layout.pos(b)
                assert (x1, y1) != (x2, y2)
