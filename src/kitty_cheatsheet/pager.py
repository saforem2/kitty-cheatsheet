"""Full-screen TUI pager with interactive search."""

from __future__ import annotations

import os
import sys
import termios
import tty

from kitty_cheatsheet.categories import (
    Category,
    DEFAULT_KEYBOARD_CATEGORIES,
    DEFAULT_MOUSE_CATEGORIES,
    categorize,
)
from kitty_cheatsheet.parser import MouseBinding
from kitty_cheatsheet.renderer import (
    BOLD,
    CATEGORY_COLORS,
    CYAN,
    DIM,
    GRAY,
    PINK,
    RESET,
    merge_blocks_horizontal,
    render_keyboard_block,
    render_mouse_block,
)


def render_all(
    keyboard_bindings: list[tuple[str, str]],
    mouse_bindings: list[MouseBinding],
    term_width: int,
    *,
    query: str = "",
    keyboard_categories: list[Category] | None = None,
    mouse_categories: list[Category] | None = None,
    mod_colors: dict[str, str] | None = None,
    prettifiers: list[tuple[str, str]] | None = None,
) -> list[str]:
    """Render keyboard + mouse sections into a list of display lines."""
    if keyboard_categories is None:
        keyboard_categories = DEFAULT_KEYBOARD_CATEGORIES
    if mouse_categories is None:
        mouse_categories = DEFAULT_MOUSE_CATEGORIES

    # Filter by search query
    kb = keyboard_bindings
    mb = mouse_bindings
    if query:
        q = query.lower()
        kb = [(k, a) for k, a in kb if q in k.lower() or q in a.lower()]
        mb = [
            m for m in mb
            if q in m.button.lower()
            or q in m.event.lower()
            or q in m.action.lower()
        ]

    out: list[str] = []
    out.append("")

    # ── Header ───────────────────────────────────────────────────────
    if query:
        match_count = len(kb) + len(mb)
        out.append(
            f"  {BOLD}{PINK}\u2328  Kitty Cheatsheet{RESET}  "
            f"{DIM}{GRAY}matching{RESET} {BOLD}{CYAN}{query}{RESET}  "
            f"{DIM}{GRAY}({match_count} results){RESET}"
        )
    else:
        out.append(f"  {BOLD}{PINK}\u2328  Kitty Cheatsheet{RESET}")
    rule = "\u2500" * (term_width - 4)
    out.append(f"  {DIM}{GRAY}{rule}{RESET}")
    out.append(
        f"  {DIM}{GRAY}"
        f"kitty_mod = alt+shift  \u2502  j/k scroll  \u2502  / search  \u2502  q close"
        f"{RESET}"
    )
    out.append("")

    # ── Keyboard section ─────────────────────────────────────────────
    categorized_kb = categorize(kb, keyboard_categories)
    blocks: list[tuple[list[str], int]] = []
    ci = 0
    for cat in keyboard_categories:
        entries = categorized_kb.get(cat.name, [])
        if not entries:
            continue
        color = CATEGORY_COLORS[ci % len(CATEGORY_COLORS)]
        ci += 1
        block_lines, block_width = render_keyboard_block(
            cat.name, entries, color, mod_colors, prettifiers,
        )
        blocks.append((block_lines, block_width))

    if blocks:
        out.extend(merge_blocks_horizontal(blocks, term_width))

    # ── Mouse section ────────────────────────────────────────────────
    categorized_mb = categorize(mb, mouse_categories)
    mouse_blocks: list[tuple[list[str], int]] = []
    mci = 0
    for cat in mouse_categories:
        entries = categorized_mb.get(cat.name, [])
        if not entries:
            continue
        color = CATEGORY_COLORS[(ci + mci) % len(CATEGORY_COLORS)]
        mci += 1
        block_lines, block_width = render_mouse_block(
            cat.name, entries, color, mod_colors, prettifiers,
        )
        mouse_blocks.append((block_lines, block_width))

    if mouse_blocks:
        out.append(f"  {BOLD}{PINK}\U0001F5B1  Mouse Bindings{RESET}")
        mouse_rule = "\u2500" * (term_width - 4)
        out.append(f"  {DIM}{GRAY}{mouse_rule}{RESET}")
        out.append("")
        out.extend(merge_blocks_horizontal(mouse_blocks, term_width))

    if not blocks and not mouse_blocks:
        out.append(f"  {DIM}{GRAY}No matches.{RESET}")
        out.append("")

    return out


def _strip_ansi(s: str) -> str:
    """Remove ANSI escape codes for plain-text output."""
    import re
    return re.sub(r'\033\[[0-9;]*m', '', s)


def print_plain(
    keyboard_bindings: list[tuple[str, str]],
    mouse_bindings: list[MouseBinding],
    term_width: int,
    **kwargs,
) -> None:
    """Dump plain-text output to stdout (for piped / --no-color usage)."""
    lines = render_all(keyboard_bindings, mouse_bindings, term_width, **kwargs)
    for line in lines:
        print(_strip_ansi(line))


# ── Input helpers ────────────────────────────────────────────────────

def read_key(fd: int) -> str:
    ch = os.read(fd, 1)
    if ch == b'\x1b':
        seq = os.read(fd, 2)
        if seq == b'[A':
            return 'up'
        elif seq == b'[B':
            return 'down'
        elif seq == b'[5':
            os.read(fd, 1)
            return 'pgup'
        elif seq == b'[6':
            os.read(fd, 1)
            return 'pgdn'
        return 'esc'
    return ch.decode('utf-8', errors='replace')


def _read_search_input(fd: int) -> tuple[str | None, str | None]:
    ch = os.read(fd, 1)
    if ch == b'\x1b':
        os.read(fd, 2)  # consume escape sequence
        return None, 'esc'
    if ch in (b'\r', b'\n'):
        return None, 'enter'
    if ch in (b'\x7f', b'\x08'):
        return None, 'backspace'
    if ch == b'\x03':
        return None, 'ctrl-c'
    return ch.decode('utf-8', errors='replace'), None


# ── Interactive pager ────────────────────────────────────────────────

def pager(
    keyboard_bindings: list[tuple[str, str]],
    mouse_bindings: list[MouseBinding],
    term_width: int,
    **render_kwargs,
) -> None:
    """Full-screen interactive pager with ``/`` search."""
    fd = sys.stdin.fileno()
    old_attrs = termios.tcgetattr(fd)

    sys.stdout.write('\033[?1049h\033[?25l')
    sys.stdout.flush()

    query = ""
    lines = render_all(
        keyboard_bindings, mouse_bindings, term_width, query=query,
        **render_kwargs,
    )

    try:
        tty.setraw(fd)
        offset = 0
        term_h = os.get_terminal_size().lines
        max_offset = max(len(lines) - term_h + 1, 0)

        while True:
            sys.stdout.write('\033[2J\033[H')
            visible = lines[offset:offset + term_h]
            sys.stdout.write('\r\n'.join(visible))
            sys.stdout.flush()

            key = read_key(fd)
            if key in ('q', 'Q', '\x03'):
                break
            elif key == 'esc':
                if query:
                    query = ""
                    lines = render_all(
                        keyboard_bindings, mouse_bindings, term_width,
                        query=query, **render_kwargs,
                    )
                    offset = 0
                    max_offset = max(len(lines) - term_h + 1, 0)
                else:
                    break
            elif key == '/':
                sys.stdout.write('\033[?25h')
                search_buf = query
                while True:
                    sys.stdout.write(f'\033[{term_h};1H\033[2K')
                    sys.stdout.write(
                        f' {BOLD}{CYAN}/{RESET}{search_buf}\033[K'
                    )
                    sys.stdout.flush()

                    ch, special = _read_search_input(fd)
                    if special == 'enter':
                        break
                    elif special in ('esc', 'ctrl-c'):
                        search_buf = query
                        break
                    elif special == 'backspace':
                        search_buf = search_buf[:-1]
                    elif ch:
                        search_buf += ch

                    preview = render_all(
                        keyboard_bindings, mouse_bindings, term_width,
                        query=search_buf, **render_kwargs,
                    )
                    sys.stdout.write('\033[2J\033[H')
                    visible = preview[:term_h - 1]
                    sys.stdout.write('\r\n'.join(visible))
                    sys.stdout.flush()

                sys.stdout.write('\033[?25l')
                query = search_buf
                lines = render_all(
                    keyboard_bindings, mouse_bindings, term_width,
                    query=query, **render_kwargs,
                )
                offset = 0
                max_offset = max(len(lines) - term_h + 1, 0)
            elif key in ('j', 'down'):
                offset = min(offset + 1, max_offset)
            elif key in ('k', 'up'):
                offset = max(offset - 1, 0)
            elif key in ('d', 'pgdn', ' '):
                offset = min(offset + term_h // 2, max_offset)
            elif key in ('u', 'pgup'):
                offset = max(offset - term_h // 2, 0)
            elif key == 'g':
                offset = 0
            elif key == 'G':
                offset = max_offset
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_attrs)
        sys.stdout.write('\033[?25h\033[?1049l')
        sys.stdout.flush()
