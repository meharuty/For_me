*This project has been created as part of the 42 curriculum by mehruty.*

# Fly-in

## Description

Fly-in routes a fleet of drones from a start hub to an end hub through a
network of zones in as few simulation turns as possible. It respects:

* zone capacities (`max_drones`) and link capacities (`max_link_capacity`),
* `blocked` zones (never entered),
* `restricted` zones (a 2-turn crossing that cannot be interrupted),
* `priority` zones (preferred when two routes are otherwise equal).

The program parses a map file, plans every drone, verifies the plan with an
independent rule checker, shows it in a colored terminal replay or an
animated Tkinter window, and prints the official output (one line per turn).

## Instructions

Requires Python 3.10+. Tkinter is needed only for `--gui`
(`apt install python3-tk`).

```
make run MAP=maps/hard/03_ultimate_challenge.txt    # colored terminal replay
make run-gui MAP=maps/hard/02_capacity_hell.txt     # Tkinter window
make debug MAP=maps/easy/01_linear_path.txt         # run under pdb
make lint                                           # flake8 + mypy
make lint-strict                                    # flake8 + mypy --strict
```

Direct use:

```
python3 main.py <map> [--plain] [--no-visual] [--delay S] [--step]
                      [--gui] [--trails] [--heatmap] [--max-turns N]
```

| Option | Effect |
|---|---|
| `--plain` | print only the official uncolored output |
| `--no-visual` | skip the replay, print only the output lines |
| `--delay S` | seconds between turns in the terminal replay (default 0.6) |
| `--step` | press Enter to advance each turn |
| `--gui` | open the Tkinter window |
| `--trails`, `--heatmap` | with `--gui`: start with trails / heatmap on |
| `--max-turns N` | safety limit on simulation turns (default 100000) |

A syntax error prints `Error: Line N: ...` and exits with code 1. An
unsolvable map (no path from start to end avoiding blocked zones) prints
`Error: map is unsolvable ...` and exits with code 1. Both go to stderr.

### Project structure

```
main.py                  entry point (FlyInApp)
maps/                    easy, medium, hard, challenger and custom maps
src/models/              Zone, Connection, Network, Drone
src/parser/              MapParser, MetadataParser, validators
src/algorithms/          Graph, TimeExpandedPlanner, Scheduler
src/simulation/          Simulation, SimulationState, Replay, SolutionChecker
src/visualization/       TerminalVisualizer, GraphicalVisualizer, analytics
```

## Algorithm and implementation strategy

* **Parsing** (`src/parser`): line by line, every error carries its line
  number. `nb_drones` must be the first definition. A connection may only
  reference zones defined on an earlier line. Duplicate zones/connections
  (`a-b` equals `b-a`), invalid zone types, non-positive capacities and bad
  metadata are rejected. `max_drones` on the start and end hubs is ignored.
* **Planning** (`src/algorithms/planner.py`): *time-expanded A\**. A state is
  `(zone, time)`. Waiting is a normal action, so strategic waiting, path
  distribution and deadlock avoidance come out of the search itself.
  Drones are planned one after another; each one takes the earliest arrival
  that fits the reservations (zone occupancy per time, link usage per turn)
  left by the previous ones. The heuristic is the capacity-free shortest
  time to the end (Dijkstra, restricted = 2, blocked excluded). Among equal
  arrivals, routes through more priority zones are preferred.
* **Restricted zones**: a 2-turn crossing is a single leg. The link is
  reserved on the departure turn only and is free again on the arrival turn,
  as the subject specifies. The drone is printed as `D<ID>-<a>-<b>` on the
  first turn and `D<ID>-<b>` when it lands.
* **Simulation**: the `Scheduler` indexes every planned leg by turn;
  `Simulation` replays them turn by turn and records the history, from which
  `Replay` builds the frames and the official output lines.
* **Verification** (`src/simulation/checker.py`): re-reads only the printed
  output and checks zone and link capacities, restricted timing, blocked
  zones, stalling on a connection and final delivery. `main.py` runs it on
  every solve and reports an internal error if the plan is invalid.
* **Complexity**: for one drone, A\* explores at most Z·T `(zone, time)`
  states (Z zones, horizon T, which grows with the number of drones N), so
  planning is about O(N·Z·T) in total, roughly O(N²·Z). The reservation
  table stores one entry per occupied `(zone, time)` and `(link, turn)`:
  O(N·T) memory. Distances to the end are computed once and reused; routes
  are never recomputed.
* **No forbidden libraries**: graph logic uses only `heapq`, `collections`
  and the standard library.

## Visualization

**Terminal (default)**: a legend of zones (colored with the map's `color=`,
with coordinates, capacity and type) and links, then for each turn the
moves, per-zone occupancy (`n/cap`), links in flight, a progress bar with
the delivered count, and a final summary with the busiest zones. Colors are
disabled automatically when stdout is not a TTY or `NO_COLOR` is set.

**Tkinter window (`--gui`)**:

* Timeline scrubber to jump to any turn, plus Play/Pause, Prev/Next, Reset
  and a speed slider. Keys: Space, Left/Right, Home/End, `t` (trails),
  `h` (heatmap), `q`/Esc.
* Trails: dashed arrowed path each drone has flown, in the drone's color;
  pick one drone in the menu to follow it.
* Heatmap: halo around zones and color of links from cool (blue) to hot
  (red), by cumulative drone-turns in a zone / crossings of a link. The side
  panel lists the busiest zones, which makes bottlenecks visible.
* Styling: gold ring = priority, dashed white = restricted, X = blocked,
  `n/cap` occupancy with a red dot when a zone is full, orange link = used
  this turn (`used/cap`). Sizes adapt to map density.

## Example

Input (`maps/easy/02_simple_fork.txt`):

```
nb_drones: 4
start_hub: start 0 0 [color=green]
hub: junction 1 0 [color=yellow max_drones=2]
hub: path_a 2 1 [color=blue]
hub: path_b 2 -1 [color=blue]
end_hub: goal 3 0 [color=red]
connection: start-junction [max_link_capacity=2]
connection: junction-path_a
connection: junction-path_b
connection: path_a-goal
connection: path_b-goal
```

Output (`python3 main.py maps/easy/02_simple_fork.txt --plain`, 4 turns):

```
D1-junction D2-junction
D1-path_a D2-path_b D3-junction D4-junction
D1-goal D2-goal D3-path_a D4-path_b
D3-goal D4-goal
```

With a restricted zone `x` reached from `r`, `D1-r-x` means D1 is in flight
on the connection `r-x` and lands in the next turn.

## Limitations and incomplete parts

Known gaps, listed honestly:

* **Not guaranteed optimal.** Drones are planned sequentially, so the result
  depends on drone order and can be above the true minimum on some maps. No
  optimality proof or lower bound (for example a flow-based one) is
  implemented. The reference-map turn counts have not been re-verified since
  the benchmark script was removed from the repository.
* **No automated tests are included.** `pyproject.toml` points to a `tests/`
  folder that is not part of the repository, and `pytest` is not listed in
  `requirements.txt`.
* **Not fully object-oriented yet.** `src/visualization/colors.py` still has
  module-level functions (`color_to_hex`, `text_color`, `drone_color`,
  `heat_color`) and constant dictionaries, and `main.py` keeps
  `build_arg_parser()` and `main()` as free functions. They should be moved
  into classes (for example a `ColorPalette` class and static methods of
  `FlyInApp`).
* **Replay is printed before the official output**, even when stdout is not
  a terminal. Use `--plain` (or `--no-visual`) when piping the output.
* **Dead or weakly used code**: `SimulationState.drones_at`,
  `Connection.name`, and `Drone.remaining_turns` / `active_connection` are
  set or defined but barely used; the "simulation" mostly replays a
  precomputed plan. `Scheduler.create_drones` actually plans routes, so its
  name is misleading. `Replay` infers "in flight" from positions rather than
  an explicit movement kind.
* **Parser details**: connection names are trimmed (`a - b` is accepted);
  connection uniqueness is checked in O(C²); `assert` is used for type
  narrowing in `MapParser.parse`.
* **Style**: some modules (`graph.py`, `planner.py`, `scheduler.py`,
  `parser.py`, `validator.py`, `checker.py`, `simulation.py`, `state.py`,
  `terminal.py`) have no module docstring.
* **GUI performance**: the whole canvas is redrawn at about 30 fps and trails
  are recomputed on every redraw. This is fine for the provided maps but will
  not scale to hundreds of drones. With more than 8 resting drones in a zone
  only a count badge is shown. The terminal replay prints every move every
  turn without truncation.
* **Housekeeping**: a `.gitignore` is required by the subject and should be
  committed (`__pycache__/`, `.mypy_cache/`, `.pytest_cache/`, `.venv/`).
  `make lint` and `make lint-strict` should be re-run after the changes
  above.

## Resources

* Silver, *Cooperative Pathfinding* (cooperative A\* / prioritized
  planning) and time-expanded graphs; multi-agent path finding surveys.
* Python documentation: `heapq`, `dataclasses`, `argparse`, `tkinter`;
  PEP 8, PEP 257; flake8 and mypy documentation.

**AI usage**: AI assistance was used to review the project against the
subject, to draft the rule checker, the analytics and Tkinter window
features, and to draft this README. Every part was read, tested and can be
explained by the author.
