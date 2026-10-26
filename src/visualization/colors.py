import colorsys
import os
import sys
import zlib

from src.models.zone import Zone


class Painter:
    """Wraps text in ANSI escape codes (or leaves it plain)."""

    RESET: str = "\033[0m"

    NAMED_COLORS: dict[str, str] = {
        "black": "90", "red": "31", "green": "32", "yellow": "33",
        "blue": "34", "magenta": "35", "purple": "35", "cyan": "36",
        "white": "37", "gray": "90", "grey": "90",
        "orange": "38;5;208", "brown": "38;5;130", "pink": "38;5;213",
        "gold": "38;5;220", "maroon": "38;5;88", "violet": "38;5;99",
        "lime": "38;5;118", "crimson": "38;5;161", "darkred": "38;5;124",
    }

    def __init__(self, enabled: bool | None = None) -> None:
        """Enable colors if stdout is a TTY, unless NO_COLOR is set."""
        if enabled is None:
            enabled = sys.stdout.isatty() and "NO_COLOR" not in os.environ
        self.enabled = enabled

    @staticmethod
    def code_for(color: str) -> str:
        """Map any single-word color name to an ANSI code."""
        key = color.strip().lower()
        if key in ("", "none"):
            return ""
        if key in Painter.NAMED_COLORS:
            return Painter.NAMED_COLORS[key]
        return f"38;5;{16 + zlib.crc32(key.encode()) % 216}"

    def paint(self, text: str, code: str) -> str:
        """Return text wrapped in the given ANSI code."""
        if not self.enabled or not code:
            return text
        return f"\033[{code}m{text}{self.RESET}"

    def zone(self, text: str, zone: Zone) -> str:
        """Paint text using a zone's own color."""
        return self.paint(text, self.code_for(zone.color))


class ColorPalette:
    """Hex colors for the graphical view (zones, drones, heat)."""

    HEX_COLORS: dict[str, str] = {
        "red": "#e74c3c", "green": "#2ecc71", "blue": "#3498db",
        "yellow": "#f1c40f", "orange": "#e67e22", "purple": "#9b59b6",
        "violet": "#8e44ad", "magenta": "#e84393", "cyan": "#1abc9c",
        "gray": "#95a5a6", "grey": "#95a5a6", "black": "#2c3e50",
        "white": "#ecf0f1", "brown": "#a0522d", "pink": "#ff7eb9",
        "gold": "#f5c542", "maroon": "#a93226", "lime": "#a3e635",
        "crimson": "#dc143c", "darkred": "#8b1a1a", "none": "#8a94a6",
    }

    @staticmethod
    def rgb_to_hex(r: float, g: float, b: float) -> str:
        """Format 0..1 channels as a hex color."""
        return f"#{int(r * 255):02x}{int(g * 255):02x}{int(b * 255):02x}"

    @staticmethod
    def from_name(name: str) -> str:
        """Map any single-word color name to a hex color."""
        key = name.strip().lower()
        if key in ColorPalette.HEX_COLORS:
            return ColorPalette.HEX_COLORS[key]
        hue = (zlib.crc32(key.encode()) % 360) / 360
        return ColorPalette.rgb_to_hex(*colorsys.hsv_to_rgb(hue, 0.6, 0.85))

    @staticmethod
    def text_on(background: str) -> str:
        """Return black or white, whichever is readable on the background."""
        r, g, b = (int(background[i:i + 2], 16) for i in (1, 3, 5))
        luminance = 0.299 * r + 0.587 * g + 0.114 * b
        return "#111111" if luminance > 150 else "#ffffff"

    @staticmethod
    def for_drone(drone_id: int) -> str:
        """Return a stable, well-separated color for a drone."""
        hue = (drone_id * 0.618033988) % 1.0
        return ColorPalette.rgb_to_hex(*colorsys.hsv_to_rgb(hue, 0.55, 0.95))

    @staticmethod
    def heat(ratio: float) -> str:
        """Map 0..1 to a cool-to-hot gradient (blue, yellow, red)."""
        ratio = min(1.0, max(0.0, ratio))
        if ratio < 0.5:
            hue = 0.60 - ratio * 2 * 0.43  # blue -> yellow
        else:
            hue = 0.17 - (ratio - 0.5) * 2 * 0.17  # yellow -> red
        return ColorPalette.rgb_to_hex(*colorsys.hsv_to_rgb(hue, 0.85, 0.95))
