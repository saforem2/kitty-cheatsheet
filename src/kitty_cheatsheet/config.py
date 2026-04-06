"""Load optional TOML configuration and merge with defaults."""

from __future__ import annotations

import os
from dataclasses import dataclass, field

from kitty_cheatsheet.categories import (
    DEFAULT_KEYBOARD_CATEGORIES,
    DEFAULT_MOUSE_CATEGORIES,
    Category,
)
from kitty_cheatsheet.renderer import DEFAULT_MOD_COLORS, DEFAULT_PRETTIFIERS

# ── Hex → ANSI 24-bit color conversion ──────────────────────────────

def _hex_to_ansi(hex_str: str) -> str:
    """Convert ``#RRGGBB`` to a 24-bit ANSI foreground escape."""
    hex_str = hex_str.lstrip('#')
    r, g, b = int(hex_str[0:2], 16), int(hex_str[2:4], 16), int(hex_str[4:6], 16)
    return f"\033[38;2;{r};{g};{b}m"


# ── Config dataclass ─────────────────────────────────────────────────

@dataclass
class Config:
    config_dir: str = "~/.config/kitty"
    mod_colors: dict[str, str] = field(default_factory=lambda: dict(DEFAULT_MOD_COLORS))
    keyboard_categories: list[Category] = field(
        default_factory=lambda: list(DEFAULT_KEYBOARD_CATEGORIES),
    )
    mouse_categories: list[Category] = field(
        default_factory=lambda: list(DEFAULT_MOUSE_CATEGORIES),
    )
    prettifiers: list[tuple[str, str]] = field(
        default_factory=lambda: list(DEFAULT_PRETTIFIERS),
    )


def _default_config_path() -> str:
    xdg = os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config"))
    return os.path.join(xdg, "kitty-cheatsheet", "config.toml")


def load_config(path: str | None = None) -> Config:
    """Load config from TOML file.  Returns defaults if file doesn't exist."""
    cfg = Config()

    if path is None:
        path = _default_config_path()

    path = os.path.expanduser(path)
    if not os.path.isfile(path):
        return cfg

    try:
        import tomllib
    except ModuleNotFoundError:
        import tomli as tomllib  # type: ignore[no-redef]

    with open(path, "rb") as f:
        data = tomllib.load(f)

    if "config_dir" in data:
        cfg.config_dir = data["config_dir"]

    # Merge modifier colors (individual overrides)
    if "colors" in data and "modifiers" in data["colors"]:
        for mod, color_val in data["colors"]["modifiers"].items():
            if color_val.startswith('#'):
                color_val = _hex_to_ansi(color_val)
            cfg.mod_colors[mod] = color_val

    # Replace keyboard categories if specified
    if "categories" in data and "keyboard" in data["categories"]:
        cfg.keyboard_categories = [
            Category(name=c["name"], pattern=c["pattern"])
            for c in data["categories"]["keyboard"]
        ]

    # Replace mouse categories if specified
    if "categories" in data and "mouse" in data["categories"]:
        cfg.mouse_categories = [
            Category(name=c["name"], pattern=c["pattern"])
            for c in data["categories"]["mouse"]
        ]

    # Merge prettifiers
    if "prettify" in data:
        existing = dict(cfg.prettifiers)
        existing.update(data["prettify"])
        cfg.prettifiers = list(existing.items())

    return cfg
