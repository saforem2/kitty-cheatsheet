"""Default category definitions for keyboard and mouse bindings."""

from __future__ import annotations

import re
from collections import OrderedDict
from dataclasses import dataclass


@dataclass
class Category:
    name: str
    pattern: str


# ── Keyboard categories (first match wins) ──────────────────────────

DEFAULT_KEYBOARD_CATEGORIES: list[Category] = [
    Category('Navigation',        r'(neighboring_window|focus_visible|move_window|swap_with)'),
    Category('Splits & Layout',   r'(launch.*(split|location)|resize_window|layout_action|zoom_toggle|toggle_maximized)'),
    Category('Scrolling',         r'(scroll_|show_scrollback|show_last|last_cmd_output|screen_scrollback)'),
    Category('Tabs',              r'(tab|goto_tab|next_tab|previous_tab|next_layout)'),
    Category('Windows & OS',      r'(new_os_window|close_os_window|close_window)'),
    Category('Clipboard',         r'(copy_|paste_|pass_selection)'),
    Category('Hints',             r'(khints|kitten hints|open_url)'),
    Category('Font & Appearance', r'(font_size|background_opacity)'),
    Category('Search & Browse',   r'(search|pipe.*overlay|vim-ansi)'),
    Category('Kittens & Tools',   r'(kitten |kitty_shell|kitty_scrollback|kitty_config|edit_config|unicode_input|grab\.py|keymap\.py)'),
    Category('Config',            r'(load_config|debug_config)'),
    Category('Misc',              r'.'),
]

# ── Mouse categories (first match wins) ─────────────────────────────

DEFAULT_MOUSE_CATEGORIES: list[Category] = [
    Category('Selection',       r'(mouse_selection|select_command_output)'),
    Category('Click Handling',  r'(mouse_handle_click)'),
    Category('Paste',           r'(paste)'),
    Category('Scrollback',      r'(mouse_show_command_output|kitty_scrollback)'),
    Category('Other',           r'.'),
]


def categorize(
    bindings: list,
    cats: list[Category],
) -> OrderedDict[str, list]:
    """Assign bindings to categories.  First regex match wins."""
    result: OrderedDict[str, list] = OrderedDict()
    for binding in bindings:
        # binding is (key, action) for keyboard, MouseBinding for mouse
        action = binding[1] if isinstance(binding, tuple) else binding.action
        for cat in cats:
            if re.search(cat.pattern, action):
                result.setdefault(cat.name, []).append(binding)
                break
    return result
