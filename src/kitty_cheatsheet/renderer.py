"""Render categorized bindings as colorized side-by-side terminal blocks."""

from __future__ import annotations

import re

from kitty_cheatsheet.parser import MouseBinding

# ── ANSI color helpers ───────────────────────────────────────────────

RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
WHITE = "\033[37m"
PINK = "\033[38;5;205m"
CYAN = "\033[36m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
BLUE = "\033[34m"
MAGENTA = "\033[35m"
LAVENDER = "\033[38;5;183m"
GRAY = "\033[38;5;245m"
ORANGE = "\033[38;5;209m"

CATEGORY_COLORS = [PINK, CYAN, GREEN, YELLOW, BLUE, MAGENTA, LAVENDER]

DEFAULT_MOD_COLORS: dict[str, str] = {
    'kitty_mod': PINK,
    'cmd':       CYAN,
    'ctrl':      GREEN,
    'alt':       ORANGE,
    'shift':     LAVENDER,
    'super':     YELLOW,
    'opt':       CYAN,
}

# ── Box-drawing characters ───────────────────────────────────────────

H = "─"; V = "│"
TL = "╭"; TR = "╮"; BL = "╰"; BR = "╯"
TD = "┬"; TU = "┴"; TRight = "├"; TLeft = "┤"; X = "┼"

ANSI_RE = re.compile(r'\033\[[0-9;]*m')
COL_GAP = 3

# ── Default action prettifiers ───────────────────────────────────────

DEFAULT_PRETTIFIERS: list[tuple[str, str]] = [
    ('kitten ~/.config/kitty/', '\u2699 '),
    ('launch --allow-remote-control kitty +kitten ~/.config/kitty/', '\u2699 '),
    ('launch --allow-remote-control kitty +', '\u2699 '),
    ('launch --stdin-source=@screen_scrollback --stdin-add-formatting', 'scrollback \u2192'),
    ('launch --stdin-source=@last_cmd_output --stdin-add-formatting', 'last output \u2192'),
    ('launch --type=overlay', 'overlay:'),
    ('launch --type=window', 'window:'),
    ('launch --location=hsplit', 'hsplit:'),
    ('launch --location=vsplit', 'vsplit:'),
    ('--hints-foreground-color=#FF1A8F --hints-background-color=#FFE0FF', ''),
    ('--hints-offset=0', ''),
]


# ── Helpers ──────────────────────────────────────────────────────────

def visible_len(s: str) -> int:
    return len(ANSI_RE.sub('', s))


def pad_to_visible(s: str, width: int) -> str:
    return s + ' ' * max(width - visible_len(s), 0)


def colorize_key(
    key_str: str,
    mod_colors: dict[str, str] | None = None,
) -> tuple[str, int]:
    """Colorize modifier prefixes.  Returns (colored_string, plain_length)."""
    if mod_colors is None:
        mod_colors = DEFAULT_MOD_COLORS
    parts = key_str.split('+')
    if len(parts) <= 1:
        return f"{BOLD}{WHITE}{key_str}{RESET}", len(key_str)

    colored = ""
    for i, part in enumerate(parts):
        is_last = (i == len(parts) - 1)
        suffix = '' if is_last else '+'
        mod_color = mod_colors.get(part.lower())
        if mod_color and not is_last:
            colored += f"{mod_color}{part}{DIM}{suffix}{RESET}"
        else:
            colored += f"{BOLD}{WHITE}{part}{suffix}{RESET}"
    return colored, len(key_str)


def prettify_action(
    s: str,
    prettifiers: list[tuple[str, str]] | None = None,
) -> str:
    if prettifiers is None:
        prettifiers = DEFAULT_PRETTIFIERS
    for old, new in prettifiers:
        s = s.replace(old, new)
    return re.sub(r'  +', ' ', s).strip()


# ── Block renderers ─────────────────────────────────────────────────

def render_keyboard_block(
    cat: str,
    entries: list[tuple[str, str]],
    color: str,
    mod_colors: dict[str, str] | None = None,
    prettifiers: list[tuple[str, str]] | None = None,
) -> tuple[list[str], int]:
    """Render a keyboard category as a boxed table.  Returns (lines, visible_width)."""
    display = [(k, prettify_action(a, prettifiers)) for k, a in entries]
    display.sort(key=lambda x: x[0])

    kw = max(max(len(k) for k, _ in display), 10)
    aw = max(max(len(a) for _, a in display), 16)
    table_w = kw + aw + 7

    lines: list[str] = []
    lines.append(f" {BOLD}{color}\u258e {cat}{RESET}")
    lines.append(f" {DIM}{TL}{H*(kw+2)}{TD}{H*(aw+2)}{TR}{RESET}")
    for i, (key, action) in enumerate(display):
        k_colored, k_plain_len = colorize_key(key, mod_colors)
        k_padded = k_colored + ' ' * (kw - k_plain_len)
        a = f"{GRAY}{action:<{aw}}{RESET}"
        lines.append(f" {DIM}{V}{RESET} {k_padded} {DIM}{V}{RESET} {a} {DIM}{V}{RESET}")
        if i < len(display) - 1:
            lines.append(f" {DIM}{TRight}{H*(kw+2)}{X}{H*(aw+2)}{TLeft}{RESET}")
    lines.append(f" {DIM}{BL}{H*(kw+2)}{TU}{H*(aw+2)}{BR}{RESET}")
    return lines, table_w


def _format_mouse_key(mb: MouseBinding) -> str:
    """Format a mouse binding's key column: ``button [event] (modes)``."""
    return f"{mb.button} [{mb.event}]"


def _format_mouse_modes(mb: MouseBinding) -> str:
    return f"({mb.modes})"


def render_mouse_block(
    cat: str,
    entries: list[MouseBinding],
    color: str,
    mod_colors: dict[str, str] | None = None,
    prettifiers: list[tuple[str, str]] | None = None,
) -> tuple[list[str], int]:
    """Render a mouse category as a boxed table.  Returns (lines, visible_width)."""
    display = [
        (_format_mouse_key(mb), _format_mouse_modes(mb), prettify_action(mb.action, prettifiers))
        for mb in entries
    ]
    display.sort(key=lambda x: x[0])

    kw = max(max(len(k) for k, _, _ in display), 10)
    mw = max(max(len(m) for _, m, _ in display), 6)
    aw = max(max(len(a) for _, _, a in display), 12)
    table_w = kw + mw + aw + 10

    lines: list[str] = []
    lines.append(f" {BOLD}{color}\u258e {cat}{RESET}")
    lines.append(f" {DIM}{TL}{H*(kw+2)}{TD}{H*(mw+2)}{TD}{H*(aw+2)}{TR}{RESET}")
    for i, (key, modes, action) in enumerate(display):
        k_parts = key.split(' ', 1)
        button_part = k_parts[0]
        event_part = k_parts[1] if len(k_parts) > 1 else ''
        k_colored, k_plain_len = colorize_key(button_part, mod_colors)
        full_key = k_colored + (' ' + f"{DIM}{event_part}{RESET}" if event_part else '')
        full_key_plain_len = k_plain_len + (1 + len(event_part) if event_part else 0)
        k_padded = full_key + ' ' * (kw - full_key_plain_len)

        m = f"{DIM}{modes:<{mw}}{RESET}"
        a = f"{GRAY}{action:<{aw}}{RESET}"
        lines.append(f" {DIM}{V}{RESET} {k_padded} {DIM}{V}{RESET} {m} {DIM}{V}{RESET} {a} {DIM}{V}{RESET}")
        if i < len(display) - 1:
            lines.append(f" {DIM}{TRight}{H*(kw+2)}{X}{H*(mw+2)}{X}{H*(aw+2)}{TLeft}{RESET}")
    lines.append(f" {DIM}{BL}{H*(kw+2)}{TU}{H*(mw+2)}{TU}{H*(aw+2)}{BR}{RESET}")
    return lines, table_w


# ── Layout ───────────────────────────────────────────────────────────

def merge_blocks_horizontal(
    block_list: list[tuple[list[str], int]],
    term_width: int,
) -> list[str]:
    """Arrange blocks side-by-side in rows that fit within *term_width*."""
    rows: list[list[tuple[list[str], int]]] = []
    current_row: list[tuple[list[str], int]] = []
    current_width = 0

    for lines, width in block_list:
        needed = width + (COL_GAP if current_row else 0)
        if current_row and current_width + needed > term_width:
            rows.append(current_row)
            current_row = [(lines, width)]
            current_width = width
        else:
            current_row.append((lines, width))
            current_width += needed

    if current_row:
        rows.append(current_row)

    output: list[str] = []
    for row in rows:
        max_height = max(len(lines) for lines, _ in row)
        padded = [
            (lines + [''] * (max_height - len(lines)), width)
            for lines, width in row
        ]
        for line_idx in range(max_height):
            combined = ""
            for col_idx, (lines, width) in enumerate(padded):
                if col_idx > 0:
                    combined += ' ' * COL_GAP
                combined += pad_to_visible(lines[line_idx], width + 1)
            output.append(combined.rstrip())
        output.append("")

    return output
