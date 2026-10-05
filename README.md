*This project has been created as part of the 42 curriculum by <login>.*

# Fly-in

## Description

Fly-in routes a fleet of drones from a start hub to an end hub through a
network of zones, in as few simulation turns as possible, while respecting
zone capacities (`max_drones`), link capacities (`max_link_capacity`), blocked
zones, 2-turn restricted zones and preferred priority zones.

The program parses a map file, plans every drone, verifies the plan with an
independent rule checker, prints the official output (one line per turn) and
shows it either in a colored terminal replay or in an animated Tkinter window.

Result on the reference maps: **every map, including the challenger
(43 turns), reaches the exact optimum** (`make benchmark`).

## Instructions

Requires Python 3.10+ (Tkinter only for `--gui`: `apt install python3-tk`).

```
make install          # flake8, mypy, pytest
make run MAP=maps/hard/03_ultimate_challenge.txt   # colored terminal replay
make run-gui MAP=maps/hard/02_capacity_hell.txt    # Tkinter window
make test             # unit tests (GUI tests skip without a display)
make benchmark        # every reference map vs its optimum
make lint             # flake8 + mypy (make lint-strict: mypy --strict)
make debug            # run under pdb
make clean
```

Command line: `python3 main.py <map> [--plain] [--no-visual] [--delay S]
[--step] [--gui] [--trails] [--heatmap] [--max-turns N]`.
`--plain` prints only the official output. An unsolvable map or a syntax
error prints `Error: ...` (with the line number for syntax errors) and exits
with code 1; it never crashes.

## Algorithm

* **Parsing** (`src/parser`): line-by-line, every error carries its line
  number. Connections may only reference previously defined zones.
* **Planning** (`src/algorithms/planner.py`): *time-expanded A\**. A state is
  `(zone, time)`. Waiting is a normal action, so strategic waiting, path
  distribution and deadlock avoidance come out of the search itself. Drones
  are planned one after another; each takes the earliest arrival that fits
  the reservations (zone occupancy per time, link usage per turn) of the
  previous ones. The heuristic is the capacity-free shortest time to the end
  (Dijkstra with restricted = 2, blocked excluded). Ties prefer routes through
  more priority zones.
* **Restricted zones**: a 2-turn crossing is one leg; the link is reserved on
  the departure turn only and is free again on the arrival turn, as the
  subject's example requires.
* **Verification** (`src/simulation/checker.py`): re-reads only the printed
  output and checks zone/link capacities, restricted timing, blocked zones,
  stalling on a connection and delivery. `main.py` runs it on every solve.
* **Complexity**: roughly O(N · Z · T) per drone for N drones, Z zones and
  horizon T (T grows with N), so about O(N²·Z) overall: 100 drones in 0.2 s,
  1000 drones in about 12 s on the hard maps. Heuristic distances are
  computed once and reused; routes are never recomputed.

## Visualization

Terminal (default): legend of zones and links, a coordinate grid with drone
counts, per-zone occupancy, links in flight (yellow), a progress bar, and a
summary with the busiest zones. Zone colors come from the map's `color=`.

Tkinter window (`--gui`), drawn with the zone colors:

* **Timeline scrubber**: drag to any turn; also Play/Pause, Prev/Next, Reset,
  speed slider. Keys: Space, Left/Right, Home/End, `t`, `h`, `q`.
* **Trails**: dashed, arrowed path each drone has flown so far, in the
  drone's color; pick one drone in the menu to follow it.
* **Heatmap**: halo around each zone and color of each link, from cool (blue)
  to hot (red), by cumulative drone-turns spent in a zone / crossings of a
  link. The side panel lists the busiest zones, which shows bottlenecks.
* Zone styling: gold ring = priority, dashed white = restricted, X = blocked,
  `n/cap` occupancy with a red dot when full, orange link = used this turn.
  Sizes adapt to map density so large maps stay readable.

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

Output (4 turns, the optimum):

```
D1-junction D2-junction
D1-path_a D2-path_b D3-junction D4-junction
D1-goal D2-goal D3-path_a D4-path_b
D3-goal D4-goal
```

With a restricted zone, `D1-r-x` means D1 is in flight on the connection
`r-x` and lands in the next turn.

## Resources

* Silver, *Cooperative Pathfinding* (WHCA\*) and time-expanded graphs,
  multi-agent path finding surveys.
* Python docs: `heapq`, `dataclasses`, `tkinter`; PEP 257, flake8, mypy docs.

**AI usage**: AI assistance was used for reviewing the project against the
subject, writing and typing the test-suite, the rule checker, the analytics
and Tkinter window features, and drafting this README. Every part was read,
tested and can be explained by the author.
