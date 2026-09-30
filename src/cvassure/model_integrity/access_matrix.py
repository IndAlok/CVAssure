"""Access-tier capability matrix generator.

Generates a visual matrix showing which methods are available at each
access tier (white-box, gray-box, black-box). The matrix is generated
from the wrapper's declared capabilities so it is always true for the
model in front of you.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from cvassure.core.detector import AccessTier
from cvassure.core.imaging import BLUE, GREEN, NAVY, RED, write_png

#: Methods shown in the matrix, in display order.
MATRIX_METHODS: tuple[str, ...] = (
    "Weight digest vs signed reference",
    "Parameter / activation statistics",
    "Trigger reconstruction (Neural Cleanse style)",
    "Behavioural fingerprint on reference battery",
    "Query-based trigger sweep (patch library)",
)

#: Which methods are available at each tier.
#: True = available, False = unavailable, "partial" = partially available.
MATRIX: dict[str, dict[str, Any]] = {
    "white-box": {
        "Weight digest vs signed reference": True,
        "Parameter / activation statistics": True,
        "Trigger reconstruction (Neural Cleanse style)": True,
        "Behavioural fingerprint on reference battery": True,
        "Query-based trigger sweep (patch library)": True,
    },
    "gray-box": {
        "Weight digest vs signed reference": True,
        "Parameter / activation statistics": "partial",
        "Trigger reconstruction (Neural Cleanse style)": "partial",
        "Behavioural fingerprint on reference battery": True,
        "Query-based trigger sweep (patch library)": True,
    },
    "black-box": {
        "Weight digest vs signed reference": True,
        "Parameter / activation statistics": False,
        "Trigger reconstruction (Neural Cleanse style)": False,
        "Behavioural fingerprint on reference battery": True,
        "Query-based trigger sweep (patch library)": True,
    },
}


def generate_matrix(
    out_path: Path,
    *,
    tier: AccessTier = "white-box",
) -> Path:
    """Generate the access-tier capability matrix as a PNG.

    The matrix is a grid: rows are methods, columns are tiers.
    Each cell is coloured: green for available, red for unavailable,
    blue for partial.
    """
    tiers: tuple[str, ...] = ("white-box", "gray-box", "black-box")
    n_methods = len(MATRIX_METHODS)
    n_tiers = len(tiers)

    # Layout constants
    cell_w = 180
    cell_h = 40
    label_w = 320
    header_h = 50
    padding = 10

    width = label_w + n_tiers * cell_w + padding * 2
    height = header_h + n_methods * cell_h + padding * 2

    # Build pixel grid
    background = (255, 255, 255)
    pixels: list[list[tuple[int, int, int]]] = [
        [background] * width for _ in range(height)
    ]

    # Draw header row
    for ti, tier_name in enumerate(tiers):
        x = label_w + ti * cell_w + padding
        _draw_centered_text(pixels, tier_name, x, padding, cell_w, header_h, NAVY)

    # Draw method rows
    for mi, method in enumerate(MATRIX_METHODS):
        y = header_h + mi * cell_h + padding
        # Method label
        _draw_left_text(pixels, method, padding, y, label_w - 10, cell_h, (0, 0, 0))

        for ti, tier_name in enumerate(tiers):
            x = label_w + ti * cell_w + padding
            status = MATRIX[tier_name].get(method, False)
            if status is True:
                color = GREEN
                label = "Available"
            elif status == "partial":
                color = BLUE
                label = "Partial"
            else:
                color = RED
                label = "Unavailable"
            _draw_cell(pixels, x, y, cell_w, cell_h, color, label)

    write_png(out_path, width, height, pixels)
    return out_path


def _draw_cell(
    pixels: list[list[tuple[int, int, int]]],
    x: int,
    y: int,
    w: int,
    h: int,
    color: tuple[int, int, int],
    label: str,
) -> None:
    """Draw a filled cell with centred text."""
    for dy in range(h):
        for dx in range(w):
            if 0 <= y + dy < len(pixels) and 0 <= x + dx < len(pixels[0]):
                pixels[y + dy][x + dx] = color
    _draw_centered_text(pixels, label, x, y, w, h, (255, 255, 255))


def _draw_centered_text(
    pixels: list[list[tuple[int, int, int]]],
    text: str,
    x: int,
    y: int,
    w: int,
    h: int,
    color: tuple[int, int, int],
) -> None:
    """Draw text approximately centred in a cell (pixel-based)."""
    # Simple approximation: draw characters as small blocks
    char_w = 6
    char_h = 8
    text_w = len(text) * char_w
    start_x = x + max(0, (w - text_w) // 2)
    start_y = y + max(0, (h - char_h) // 2)
    _draw_text(pixels, text, start_x, start_y, color)


def _draw_left_text(
    pixels: list[list[tuple[int, int, int]]],
    text: str,
    x: int,
    y: int,
    w: int,
    h: int,
    color: tuple[int, int, int],
) -> None:
    """Draw text left-aligned in a cell."""
    char_w = 6
    char_h = 8
    start_y = y + max(0, (h - char_h) // 2)
    _draw_text(pixels, text, x + 4, start_y, color)


def _draw_text(
    pixels: list[list[tuple[int, int, int]]],
    text: str,
    x: int,
    y: int,
    color: tuple[int, int, int],
) -> None:
    """Draw text using a simple 5x7 pixel font."""
    # Simple pixel font for uppercase letters and digits
    font: dict[str, list[str]] = {
        "A": ["01110", "10001", "10001", "11111", "10001", "10001", "10001"],
        "B": ["11110", "10001", "10001", "11110", "10001", "10001", "11110"],
        "C": ["01110", "10001", "10000", "10000", "10000", "10001", "01110"],
        "D": ["11110", "10001", "10001", "10001", "10001", "10001", "11110"],
        "E": ["11111", "10000", "10000", "11110", "10000", "10000", "11111"],
        "F": ["11111", "10000", "10000", "11110", "10000", "10000", "10000"],
        "G": ["01110", "10001", "10000", "10111", "10001", "10001", "01110"],
        "H": ["10001", "10001", "10001", "11111", "10001", "10001", "10001"],
        "I": ["01110", "00100", "00100", "00100", "00100", "00100", "01110"],
        "J": ["00111", "00010", "00010", "00010", "00010", "10010", "01100"],
        "K": ["10001", "10010", "10100", "11000", "10100", "10010", "10001"],
        "L": ["10000", "10000", "10000", "10000", "10000", "10000", "11111"],
        "M": ["10001", "11011", "10101", "10101", "10001", "10001", "10001"],
        "N": ["10001", "11001", "10101", "10011", "10001", "10001", "10001"],
        "O": ["01110", "10001", "10001", "10001", "10001", "10001", "01110"],
        "P": ["11110", "10001", "10001", "11110", "10000", "10000", "10000"],
        "Q": ["01110", "10001", "10001", "10001", "10101", "10010", "01101"],
        "R": ["11110", "10001", "10001", "11110", "10100", "10010", "10001"],
        "S": ["01111", "10000", "10000", "01110", "00001", "00001", "11110"],
        "T": ["11111", "00100", "00100", "00100", "00100", "00100", "00100"],
        "U": ["10001", "10001", "10001", "10001", "10001", "10001", "01110"],
        "V": ["10001", "10001", "10001", "10001", "10001", "01010", "00100"],
        "W": ["10001", "10001", "10001", "10101", "10101", "11011", "10001"],
        "X": ["10001", "10001", "01010", "00100", "01010", "10001", "10001"],
        "Y": ["10001", "10001", "01010", "00100", "00100", "00100", "00100"],
        "Z": ["11111", "00001", "00010", "00100", "01000", "10000", "11111"],
        "0": ["01110", "10001", "10011", "10101", "11001", "10001", "01110"],
        "1": ["00100", "01100", "00100", "00100", "00100", "00100", "01110"],
        "2": ["01110", "10001", "00001", "00010", "00100", "01000", "11111"],
        "3": ["11110", "00001", "00001", "01110", "00001", "00001", "11110"],
        "4": ["00010", "00110", "01010", "10010", "11111", "00010", "00010"],
        "5": ["11111", "10000", "11110", "00001", "00001", "10001", "01110"],
        "6": ["00110", "01000", "10000", "11110", "10001", "10001", "01110"],
        "7": ["11111", "00001", "00010", "00100", "01000", "01000", "01000"],
        "8": ["01110", "10001", "10001", "01110", "10001", "10001", "01110"],
        "9": ["01110", "10001", "10001", "01111", "00001", "00010", "01100"],
        " ": ["00000", "00000", "00000", "00000", "00000", "00000", "00000"],
        "/": ["00001", "00010", "00010", "00100", "01000", "01000", "10000"],
        "(": ["00010", "00100", "01000", "01000", "01000", "00100", "00010"],
        ")": ["01000", "00100", "00010", "00010", "00010", "00100", "01000"],
        "-": ["00000", "00000", "00000", "11111", "00000", "00000", "00000"],
        ".": ["00000", "00000", "00000", "00000", "00000", "01100", "01100"],
        ",": ["00000", "00000", "00000", "00000", "01100", "01100", "01000"],
        ":": ["00000", "01100", "01100", "00000", "01100", "01100", "00000"],
        "+": ["00000", "00100", "00100", "11111", "00100", "00100", "00000"],
        "_": ["00000", "00000", "00000", "00000", "00000", "00000", "11111"],
    }

    for i, char in enumerate(text.upper()):
        glyph = font.get(char, font[" "])
        for row_idx, row in enumerate(glyph):
            for col_idx, pixel in enumerate(row):
                if pixel == "1":
                    py = y + row_idx
                    px = x + i * 6 + col_idx
                    if 0 <= py < len(pixels) and 0 <= px < len(pixels[0]):
                        pixels[py][px] = color
