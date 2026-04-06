"""Parse kitty config files to extract keyboard and mouse bindings."""

from __future__ import annotations

import glob
import os
from typing import NamedTuple


class MouseBinding(NamedTuple):
    button: str   # e.g. "shift+left"
    event: str    # e.g. "click", "doublepress"
    modes: str    # e.g. "ungrabbed", "grabbed,ungrabbed"
    action: str   # e.g. "mouse_handle_click selection link prompt"


def parse_bindings(
    config_dir: str,
) -> tuple[list[tuple[str, str]], list[MouseBinding]]:
    """Read all .conf files and extract ``map`` and ``mouse_map`` lines.

    Returns (keyboard_bindings, mouse_bindings).
    """
    keyboard: list[tuple[str, str]] = []
    mouse: list[MouseBinding] = []

    for path in sorted(glob.glob(os.path.join(config_dir, "*.conf"))):
        with open(path) as f:
            for line in f:
                line = line.strip()

                if line.startswith("map "):
                    parts = line.split(None, 2)
                    if len(parts) >= 3 and parts[2] != "no_op":
                        keyboard.append((parts[1], parts[2]))

                elif line.startswith("mouse_map "):
                    parts = line.split(None, 4)
                    if len(parts) >= 5 and parts[4] != "no_op":
                        mouse.append(MouseBinding(
                            button=parts[1],
                            event=parts[2],
                            modes=parts[3],
                            action=parts[4],
                        ))
                    elif len(parts) == 4 and parts[3] != "no_op":
                        # mouse_map with no action args (e.g. discard_event)
                        mouse.append(MouseBinding(
                            button=parts[1],
                            event=parts[2],
                            modes=parts[3],
                            action="",
                        ))

    return keyboard, mouse
