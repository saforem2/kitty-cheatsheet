"""Command-line interface for kitty-cheatsheet."""

from __future__ import annotations

import argparse
import os
import sys

from kitty_cheatsheet.config import load_config
from kitty_cheatsheet.pager import pager, print_plain
from kitty_cheatsheet.parser import parse_bindings


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(
        prog="kitty-cheatsheet",
        description="Interactive keybinding cheatsheet for kitty",
    )
    ap.add_argument(
        "--config-dir",
        default=None,
        help="Path to kitty config directory (default: ~/.config/kitty)",
    )
    ap.add_argument(
        "--config",
        default=None,
        help="Path to kitty-cheatsheet config.toml",
    )
    ap.add_argument(
        "--no-color",
        action="store_true",
        help="Disable colors (also auto-detected when piped)",
    )
    ap.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {_get_version()}",
    )
    args = ap.parse_args(argv)

    cfg = load_config(args.config)

    config_dir = os.path.expanduser(args.config_dir or cfg.config_dir)
    keyboard_bindings, mouse_bindings = parse_bindings(config_dir)

    try:
        term_width = os.get_terminal_size().columns
    except OSError:
        term_width = 80

    render_kwargs = dict(
        keyboard_categories=cfg.keyboard_categories,
        mouse_categories=cfg.mouse_categories,
        mod_colors=cfg.mod_colors,
        prettifiers=cfg.prettifiers,
    )

    if args.no_color or not sys.stdout.isatty():
        print_plain(keyboard_bindings, mouse_bindings, term_width, **render_kwargs)
    else:
        pager(keyboard_bindings, mouse_bindings, term_width, **render_kwargs)


def _get_version() -> str:
    from kitty_cheatsheet import __version__
    return __version__
