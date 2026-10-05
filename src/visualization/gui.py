"""Animated tkinter view: zones, links, drones, trails and heatmap."""
import math
from typing import Any, Callable

from src.models.network import Network
from src.models.zone import Zone, ZoneType
from src.simulation.replay import Replay
from src.visualization.analytics import LinkKey, SimulationAnalytics
from src.visualization.colors import (
    color_to_hex,
    drone_color,
    heat_color,
    text_color,
)

try:
    import tkinter as tk
except ImportError:  # tkinter is optional: only --gui needs it
    tk = None  # type: ignore[assignment]

Point = tuple[float, float]

ZONE_RADIUS = 24
DRONE_RADIUS = 8
TICK_MS = 33
MAX_RING = 8

BG = "#14181f"
PANEL = "#2b3342"
FG = "#e6e9ef"
MUTED = "#9aa4b5"
LINK = "#5b6575"
LINK_BUSY = "#f5a623"
COLD = "#3b4252"


class Layout:
    """Maps zone coordinates to canvas pixels and sizes the drawing.

    Zone and drone radii shrink on dense maps so circles never overlap,
    and neighbouring labels in a row are staggered on two levels.
    """

    def __init__(self, zones: list[Zone]) -> None:
        """Remember the zones to place."""
        self.zones = zones
        self._pos: dict[str, Point] = {}
        self._level: dict[str, int] = {}
        self._size: tuple[float, float] | None = None
        self.radius = float(ZONE_RADIUS)
        self.drone_radius = float(DRONE_RADIUS)

    def fit(self, width: float, height: float, margin: float = 90) -> None:
        """Scale and center all zones inside the given canvas size."""
        if self._size == (width, height):
            return
        self._size = (width, height)
        xs = [z.x for z in self.zones]
        ys = [z.y for z in self.zones]
        span_x, span_y = max(xs) - min(xs), max(ys) - min(ys)
        fit_x = (width - 2 * margin) / max(span_x, 1)
        fit_y = (height - 2 * margin) / max(span_y, 1)
        base = max(min(fit_x, fit_y, 170.0), 1.0)
        # Each axis may stretch up to 2.2x the uniform scale so a wide
        # map still uses the canvas height, without distorting it badly.
        scale_x = max(min(fit_x, 170.0, base * 2.2), 1.0)
        scale_y = max(min(fit_y, 170.0, base * 2.2), 1.0)
        off_x = (width - span_x * scale_x) / 2
        off_y = (height - span_y * scale_y) / 2
        taken: set[tuple[int, int]] = set()
        self._pos = {}
        for zone in self.zones:
            px = off_x + (zone.x - min(xs)) * scale_x
            py = off_y + (max(ys) - zone.y) * scale_y
            while (round(px), round(py)) in taken:
                px += 2 * ZONE_RADIUS + 8
            taken.add((round(px), round(py)))
            self._pos[zone.name] = (px, py)
        self._size_shapes()
        self._stagger_labels()

    def _size_shapes(self) -> None:
        """Pick radii from the closest pair of zones."""
        points = list(self._pos.values())
        closest = min(
            (math.dist(a, b) for i, a in enumerate(points)
             for b in points[i + 1:]),
            default=200.0,
        )
        self.radius = min(float(ZONE_RADIUS), max(9.0, closest * 0.32))
        self.drone_radius = max(5.0, min(float(DRONE_RADIUS),
                                         self.radius * 0.36))

    def _stagger_labels(self) -> None:
        """Alternate label height for crowded neighbours in one row."""
        rows: dict[int, list[Zone]] = {}
        for zone in self.zones:
            rows.setdefault(round(self._pos[zone.name][1]), []).append(zone)
        self._level = {}
        for row in rows.values():
            row.sort(key=lambda z: self._pos[z.name][0])
            gaps = [
                self._pos[b.name][0] - self._pos[a.name][0]
                for a, b in zip(row, row[1:])
            ]
            crowded = bool(gaps) and min(gaps) < 100
            for i, zone in enumerate(row):
                self._level[zone.name] = i % 2 if crowded else 0

    def pos(self, zone: Zone) -> Point:
        """Pixel position of a zone."""
        return self._pos[zone.name]

    def label_level(self, zone: Zone) -> int:
        """0 or 1: which of the two label heights a zone uses."""
        return self._level.get(zone.name, 0)


class GraphicalVisualizer:
    """Animated tkinter replay with timeline, trails and congestion heat."""

    def __init__(
        self,
        network: Network,
        replay: Replay,
        trails: bool = False,
        heatmap: bool = False,
    ) -> None:
        """Build the window (raises RuntimeError without a display)."""
        self.network = network
        self.frames = replay.frames
        self.analytics = SimulationAnalytics(network, replay)
        self.drone_ids = self.analytics.drone_ids
        self.layout = Layout(network.zones)
        self.index = -1
        self.progress = 1.0
        self.playing = False
        self._syncing = False
        if tk is None:
            raise RuntimeError(
                "tkinter is not installed (try: apt install python3-tk)"
            )
        try:
            self.root = tk.Tk()
        except tk.TclError as error:
            raise RuntimeError(f"Cannot open a window: {error}") from None
        self.root.title("Fly-in")
        self.root.configure(bg=BG)
        self.show_trails = tk.BooleanVar(master=self.root, value=trails)
        self.show_heat = tk.BooleanVar(master=self.root, value=heatmap)
        self.trail_drone = tk.StringVar(master=self.root, value="All")
        self._build_ui()

    # ---------- UI construction ----------

    @staticmethod
    def _label(parent: "tk.Misc", **options: Any) -> "tk.Label":
        """Create a themed label."""
        return tk.Label(parent, bg=BG, fg=FG, **options)

    def _build_ui(self) -> None:
        """Create the canvas, side panel, timeline and controls."""
        self.canvas = tk.Canvas(
            self.root, width=960, height=600, bg=BG, highlightthickness=0,
        )
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self._build_side_panel()
        self.scrub = tk.Scale(
            self.root, from_=0, to=len(self.frames), orient="horizontal",
            showvalue=False, command=self._on_scrub, bg=BG, fg=FG,
            troughcolor=PANEL, highlightthickness=0, sliderlength=22,
        )
        self.scrub.grid(row=1, column=0, columnspan=2, sticky="ew",
                        padx=14)
        self._build_controls()
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        self.canvas.bind("<Configure>", lambda _e: self._redraw())
        keys: dict[str, Callable[[], None]] = {
            "<space>": self.toggle_play, "<Right>": self.next_turn,
            "<Left>": self.prev_turn, "<Home>": self.reset,
            "<End>": self.go_to_end, "t": self._flip_trails,
            "h": self._flip_heat, "<Escape>": self.root.destroy,
            "q": self.root.destroy,
        }
        for key, action in keys.items():
            self.root.bind(key, self._handler(action))

    @staticmethod
    def _handler(action: Callable[[], None]) -> Callable[[Any], None]:
        """Wrap a no-argument action as a tkinter event handler."""
        def handle(_event: Any) -> None:
            action()
        return handle

    def _build_side_panel(self) -> None:
        """Create the info panel on the right."""
        side = tk.Frame(self.root, bg=BG, padx=12, pady=12)
        side.grid(row=0, column=1, sticky="ns")
        self.turn_var = tk.StringVar(master=self.root)
        self.delivered_var = tk.StringVar(master=self.root)
        self.moves_var = tk.StringVar(master=self.root)
        self.hot_var = tk.StringVar(master=self.root)
        self._label(side, textvariable=self.turn_var, anchor="w",
                    font=("Helvetica", 16, "bold")).pack(fill="x", pady=2)
        self._label(side, textvariable=self.delivered_var, anchor="w",
                    font=("Helvetica", 11)).pack(fill="x", pady=2)
        tk.Label(side, text="Moves this turn", bg=BG, fg=LINK_BUSY,
                 font=("Helvetica", 10, "bold"), anchor="w",
                 ).pack(fill="x", pady=(10, 0))
        self._label(side, textvariable=self.moves_var, justify="left",
                    wraplength=230, anchor="nw",
                    font=("Courier", 10)).pack(fill="x")
        tk.Label(side, text="Busiest zones (drone-turns)", bg=BG,
                 fg=LINK_BUSY, font=("Helvetica", 10, "bold"), anchor="w",
                 ).pack(fill="x", pady=(10, 0))
        self._label(side, textvariable=self.hot_var, justify="left",
                    anchor="nw", font=("Courier", 10)).pack(fill="x")
        legend = (
            "Legend\n"
            "zone fill    zone color\n"
            "gold ring    priority zone\n"
            "dashed white restricted (2 turns)\n"
            "X            blocked\n"
            "orange link  used this turn (used/cap)\n"
            "red dot      zone is full\n"
            "n/cap        drones / capacity\n"
            "halo / link  heatmap (cool to hot)"
        )
        tk.Label(side, text=legend, bg=BG, fg=MUTED, justify="left",
                 anchor="w", font=("Courier", 9),
                 ).pack(fill="x", side="bottom", pady=(10, 0))
        self.heat_bar = tk.Canvas(side, width=230, height=28, bg=BG,
                                  highlightthickness=0)
        self.heat_bar.create_text(0, 22, text="cool", fill=MUTED, anchor="w",
                                  font=("Helvetica", 8))
        self.heat_bar.create_text(230, 22, text="hot (busiest)",
                                  fill=MUTED, anchor="e",
                                  font=("Helvetica", 8))
        self.heat_bar.pack(side="bottom", pady=(8, 0))
        for step in range(46):
            self.heat_bar.create_rectangle(
                step * 5, 0, step * 5 + 5, 14, outline="",
                fill=heat_color(step / 45),
            )

    def _build_controls(self) -> None:
        """Create the button bar below the timeline."""
        bar = tk.Frame(self.root, bg=BG, pady=8)
        bar.grid(row=2, column=0, columnspan=2)
        self.play_button = tk.Button(bar, text="Play", width=7,
                                     command=self.toggle_play)
        for text, command in (("Reset", self.reset), ("Prev", self.prev_turn)):
            tk.Button(bar, text=text, width=7, command=command).pack(
                side="left", padx=3)
        self.play_button.pack(side="left", padx=3)
        tk.Button(bar, text="Next", width=7, command=self.next_turn).pack(
            side="left", padx=3)
        for text, var in (("Trails", self.show_trails),
                          ("Heatmap", self.show_heat)):
            tk.Checkbutton(
                bar, text=text, variable=var, command=self._redraw,
                bg=BG, fg=FG, selectcolor=PANEL, activebackground=BG,
                activeforeground=FG, highlightthickness=0,
            ).pack(side="left", padx=(14, 0))
        choices = ["All"] + [f"D{i}" for i in self.drone_ids]
        menu = tk.OptionMenu(bar, self.trail_drone, *choices,
                             command=lambda _v: self._redraw())
        menu.config(bg=BG, fg=FG, highlightthickness=0, width=4)
        menu.pack(side="left", padx=3)
        self._label(bar, text="ms/turn").pack(side="left", padx=(16, 2))
        self.speed = tk.Scale(
            bar, from_=150, to=2000, orient="horizontal", length=160,
            bg=BG, fg=FG, highlightthickness=0,
        )
        self.speed.set(800)
        self.speed.pack(side="left")

    # ---------- controls ----------

    def _goto(self, index: int, progress: float) -> None:
        """Jump to a frame index with a given animation progress."""
        self.index = max(-1, min(index, len(self.frames) - 1))
        self.progress = progress
        self._redraw()

    def _on_scrub(self, value: str) -> None:
        """Timeline slider moved by the user."""
        if self._syncing:
            return
        self.playing = False
        self.play_button.config(text="Play")
        self._goto(int(float(value)) - 1, 1.0)

    def _flip_trails(self) -> None:
        """Toggle trails from the keyboard."""
        self.show_trails.set(not self.show_trails.get())
        self._redraw()

    def _flip_heat(self) -> None:
        """Toggle the heatmap from the keyboard."""
        self.show_heat.set(not self.show_heat.get())
        self._redraw()

    def toggle_play(self) -> None:
        """Start or pause automatic playback."""
        if not self.playing and self.index >= len(self.frames) - 1:
            self.reset()
        self.playing = not self.playing
        self.play_button.config(text="Pause" if self.playing else "Play")

    def next_turn(self) -> None:
        """Advance one turn with animation."""
        if self.index < len(self.frames) - 1:
            self._goto(self.index + 1, 0.0)

    def prev_turn(self) -> None:
        """Go back one turn without animation."""
        if self.index >= 0:
            self._goto(self.index - 1, 1.0)

    def reset(self) -> None:
        """Return to the initial state."""
        self._goto(-1, 1.0)

    def go_to_end(self) -> None:
        """Jump to the last turn."""
        self.playing = False
        self.play_button.config(text="Play")
        self._goto(len(self.frames) - 1, 1.0)

    def _tick(self) -> None:
        """Advance the animation clock."""
        if self.progress < 1.0:
            step = TICK_MS / self.speed.get()
            self.progress = min(1.0, self.progress + step)
            self._redraw()
        elif self.playing:
            if self.index < len(self.frames) - 1:
                self.next_turn()
            else:
                self.playing = False
                self.play_button.config(text="Play")
        self.root.after(TICK_MS, self._tick)

    def run(self) -> None:
        """Show the window and block until it is closed."""
        self.root.update_idletasks()
        self._redraw()
        self.root.after(TICK_MS, self._tick)
        self.root.mainloop()

    # ---------- geometry ----------

    def _anchor_point(self, anchor: tuple[Zone, Zone | None]) -> Point:
        """Pixel position of an anchor (links use their midpoint)."""
        ax, ay = self.layout.pos(anchor[0])
        if anchor[1] is None:
            return ax, ay
        bx, by = self.layout.pos(anchor[1])
        return (ax + bx) / 2, (ay + by) / 2

    # ---------- drawing ----------

    def _redraw(self) -> None:
        """Redraw the whole scene for the current index and progress."""
        canvas = self.canvas
        canvas.delete("all")
        self.layout.fit(max(canvas.winfo_width(), 200),
                        max(canvas.winfo_height(), 200))
        an, index = self.analytics, self.index
        heat_on = self.show_heat.get()
        self._draw_links(
            an.link_usage(index), an.link_heat(index) if heat_on else {},
        )
        if self.show_trails.get():
            self._draw_trails()
        zone_heat = an.zone_heat(index) if heat_on else {}
        counts = an.zone_counts(index)
        for zone in self.network.zones:
            self._draw_zone(zone, counts.get(zone.name, 0), zone_heat)
        self._draw_drones()
        self._update_panel()
        self._syncing = True
        self.scrub.set(index + 1)
        self._syncing = False

    def _draw_links(
        self,
        usage: dict[LinkKey, int],
        heat: dict[LinkKey, float],
    ) -> None:
        """Draw connections; busy ones show usage/cap, hot ones glow."""
        for conn in self.network.connections:
            ax, ay = self.layout.pos(conn.zone_a)
            bx, by = self.layout.pos(conn.zone_b)
            key = frozenset((conn.zone_a.name, conn.zone_b.name))
            used = usage.get(key, 0)
            ratio = heat.get(key, 0.0)
            color = LINK_BUSY if used else LINK
            width = min(2 + conn.max_link_capacity, 7)
            if ratio > 0 and not used:
                color, width = heat_color(ratio), width + 2
            self.canvas.create_line(ax, ay, bx, by, fill=color, width=width)
            label = (
                f"{used}/{conn.max_link_capacity}" if used
                else (f"x{conn.max_link_capacity}"
                      if conn.max_link_capacity > 1 else "")
            )
            if label:
                self.canvas.create_text(
                    (ax + bx) / 2, (ay + by) / 2 - 11, text=label,
                    fill=color, font=("Helvetica", 9, "bold"),
                )

    def _draw_trails(self) -> None:
        """Draw the path every selected drone has flown so far."""
        choice = self.trail_drone.get()
        ids = self.drone_ids if choice == "All" else [int(choice[1:])]
        for drone_id in ids:
            zones = self.analytics.trail(drone_id, self.index)
            if len(zones) < 2:
                continue
            shift = ((drone_id * 7) % 5 - 2) * 2.4
            coords: list[float] = []
            for zone in zones:
                px, py = self.layout.pos(zone)
                coords += [px + shift, py + shift]
            self.canvas.create_line(
                *coords, fill=drone_color(drone_id),
                width=3 if choice != "All" else 2, dash=(6, 3),
                arrow="last", arrowshape=(9, 11, 4),
            )

    def _draw_zone(
        self, zone: Zone, count: int, heat: dict[str, float],
    ) -> None:
        """Draw one zone: its own color, type styling, occupancy, halo."""
        x, y = self.layout.pos(zone)
        r = self.layout.radius
        halo_gap = max(4.0, r * 0.28)
        fill = color_to_hex(zone.color)
        dash: tuple[int, ...] = ()
        outline, width = "#d9dee7", 2
        if zone.zone_type == ZoneType.PRIORITY:
            outline, width = "#f5c542", 5
        elif zone.zone_type == ZoneType.RESTRICTED:
            outline, width, dash = "#ffffff", 4, (6, 4)
        elif zone.zone_type == ZoneType.BLOCKED:
            fill = "#3a3f4b"
        is_start = zone == self.network.start
        is_end = zone == self.network.end
        if is_start or is_end:
            self.canvas.create_oval(
                x - r - 5, y - r - 5, x + r + 5, y + r + 5,
                outline="#ffffff", width=2,
            )
        elif self.show_heat.get() and zone.zone_type != ZoneType.BLOCKED:
            ratio = heat.get(zone.name, 0.0)
            halo = heat_color(ratio) if ratio > 0 else COLD
            self.canvas.create_oval(
                x - r - halo_gap, y - r - halo_gap,
                x + r + halo_gap, y + r + halo_gap,
                outline=halo, width=max(3, int(r * 0.25)),
            )
        self.canvas.create_oval(
            x - r, y - r, x + r, y + r, fill=fill, outline=outline,
            width=width, dash=dash,
        )
        if zone.zone_type == ZoneType.BLOCKED:
            d = r * 0.6
            for sign in (1, -1):
                self.canvas.create_line(
                    x - d, y - sign * d, x + d, y + sign * d,
                    fill="#ff5c5c", width=3,
                )
        else:
            if is_end:
                inner = str(self.analytics.delivered(self.index))
            elif is_start:
                inner = str(count)
            else:
                inner = f"{count}/{zone.max_drones}"
            self.canvas.create_text(
                x, y, text=inner, fill=text_color(fill),
                font=("Helvetica", 10, "bold"),
            )
            if not (is_start or is_end) and count >= zone.max_drones:
                self.canvas.create_oval(
                    x + r - 5, y - r - 3, x + r + 3, y - r + 5,
                    fill="#ff3b30", outline="",
                )
        tag = " (START)" if is_start else " (END)" if is_end else ""
        level = self.layout.label_level(zone)
        self._draw_name(zone, x, y + r + 9 + 11 * level, zone.name + tag)

    def _draw_name(self, zone: Zone, x: float, y: float, text: str) -> None:
        """Draw a zone name on a small backing box so it stays legible."""
        size = 9 if self.layout.radius >= 16 else 8
        item = self.canvas.create_text(
            x, y, text=text, fill=FG, font=("Helvetica", size),
        )
        box = self.canvas.bbox(item)
        if box:
            rect = self.canvas.create_rectangle(
                box[0] - 2, box[1], box[2] + 2, box[3], fill=BG, outline="",
            )
            self.canvas.tag_lower(rect, item)

    def _draw_drone(self, drone_id: int, x: float, y: float) -> None:
        """Draw one drone dot with its id."""
        color = drone_color(drone_id)
        r = self.layout.drone_radius
        self.canvas.create_oval(
            x - r, y - r, x + r, y + r, fill=color, outline="#111111",
        )
        self.canvas.create_text(
            x, y, text=str(drone_id), fill=text_color(color),
            font=("Helvetica", 7, "bold"),
        )

    def _draw_drones(self) -> None:
        """Draw moving drones individually and resting ones around zones."""
        t = self.progress
        eased = t * t * (3 - 2 * t)
        end = self.network.end
        resting: dict[str, list[int]] = {}
        for drone_id in self.drone_ids:
            before = self.analytics.anchor(self.index - 1, drone_id)
            after = self.analytics.anchor(self.index, drone_id)
            x0, y0 = self._anchor_point(before)
            x1, y1 = self._anchor_point(after)
            at_end = after[1] is None and after[0] == end
            if at_end and (t >= 1.0 or before[0] == end):
                continue
            if t >= 1.0 or (x0, y0) == (x1, y1):
                if after[1] is None:
                    resting.setdefault(after[0].name, []).append(drone_id)
                else:
                    self._draw_drone(drone_id, x1, y1)
                continue
            self._draw_drone(
                drone_id, x0 + (x1 - x0) * eased, y0 + (y1 - y0) * eased,
            )
        zones = {z.name: z for z in self.network.zones}
        for name, ids in resting.items():
            self._draw_resting(zones[name], ids)

    def _draw_resting(self, zone: Zone, ids: list[int]) -> None:
        """Place resting drones on a ring, or show a count badge."""
        x, y = self.layout.pos(zone)
        zr = self.layout.radius
        if len(ids) > MAX_RING:
            self.canvas.create_rectangle(
                x + zr - 2, y + zr - 14, x + zr + 38, y + zr + 2,
                fill=PANEL, outline=FG,
            )
            self.canvas.create_text(
                x + zr + 18, y + zr - 6,
                text=f"{len(ids)} drones", fill=FG, font=("Helvetica", 8),
            )
            return
        ring = zr + self.layout.drone_radius + 4
        for slot, drone_id in enumerate(ids):
            angle = -math.pi / 2 + 2 * math.pi * slot / max(len(ids), 1)
            self._draw_drone(
                drone_id,
                x + ring * math.cos(angle),
                y + ring * math.sin(angle),
            )

    def _update_panel(self) -> None:
        """Refresh the text panel."""
        total = len(self.drone_ids)
        self.turn_var.set(f"Turn {self.index + 1} / {len(self.frames)}")
        self.delivered_var.set(
            f"Delivered {self.analytics.delivered(self.index)} / {total}"
        )
        spots = self.analytics.hotspots(self.index)
        self.hot_var.set(
            "\n".join(f"{n:<18}{v:>4}" for n, v in spots) or "(none yet)"
        )
        if self.index < 0:
            self.moves_var.set("(start)")
            return
        frame = self.frames[self.index]
        tokens = [Replay.token(m, frame) for m in frame.movements]
        self.moves_var.set("\n".join(tokens) if tokens else "(all waiting)")
