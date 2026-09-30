"""A minimal PNG writer. No Pillow in core.

PIL would be the obvious choice and it is not a dependency. A stub needs a tiny
solid-colour image so the report has a file to open, and a LINK figure needs two
cropped images side by side. Both are small and both are just pixels.

zlib and struct are stdlib. If a teammate needs real image decoding for pattern
correlation, numpy handles it (see linking.py) and that stays out of core too.
"""

from __future__ import annotations

import struct
import zlib
from pathlib import Path

RGB = tuple[int, int, int]

#: Team palette, from the plan. Blue and navy are the brand colours; red is only
#: ever danger, green only ever safe. Lives here because the linker, the stubs
#: and the images all draw, and one palette beats three copies.
BLUE = (0, 112, 192)
NAVY = (31, 56, 100)
RED = (192, 0, 0)
GREEN = (30, 123, 52)
GREY = (128, 128, 128)


def _chunk(tag: bytes, data: bytes) -> bytes:
    return (
        struct.pack(">I", len(data))
        + tag
        + data
        + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    )


def write_png(path: Path, width: int, height: int, pixels: list[list[RGB]]) -> Path:
    """Write an 8-bit RGB PNG. `pixels` is row-major, row 0 at the top.

    No alpha, no interlacing, no palette. A stub image and a side-by-side link
    figure do not need them, and every one of those is code to test.
    """
    if len(pixels) != height or any(len(row) != width for row in pixels):
        raise ValueError(f"expected {width}x{height} RGB pixels, got {len(pixels)} rows")
    raw = bytearray()
    for row in pixels:
        raw.append(0)  # filter type 0 (None)
        for r, g, b in row:
            raw += bytes((r & 255, g & 255, b & 255))
    png = (
        b"\x89PNG\r\n\x1a\n"
        + _chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        + _chunk(b"IDAT", zlib.compress(bytes(raw), 9))
        + _chunk(b"IEND", b"")
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(png)
    return path


def solid(path: Path, width: int, height: int, color: RGB) -> Path:
    return write_png(path, width, height, [[color] * width for _ in range(height)])


def checkerboard(
    path: Path, width: int, height: int, light: RGB, dark: RGB, *, cell: int = 8
) -> Path:
    """A two-tone board. Enough texture for a correlation to mean something.

    A flat image has no pattern, so normalised cross-correlation on two flat
    images is 0/0 and the linker correctly reports `pattern` as uninformative.
    A patch template in a fixture therefore has to carry texture, or the NCC code
    path is never exercised by the demo.
    """
    if cell < 1:
        raise ValueError("cell must be >= 1")
    rows = [
        [light if ((x // cell) + (y // cell)) % 2 == 0 else dark for x in range(width)]
        for y in range(height)
    ]
    return write_png(path, width, height, rows)


def side_by_side(
    path: Path,
    left: list[list[RGB]],
    right: list[list[RGB]],
    *,
    gap: int = 4,
    background: RGB = (245, 245, 245),
) -> Path:
    """Two same-size images with a gap, for a LINK figure."""
    if not left or not right:
        raise ValueError("both images are required")
    lh, lw = len(left), len(left[0])
    rh, rw = len(right), len(right[0])
    if (lh, lw) != (rh, rw):
        raise ValueError(f"images must match, got {lw}x{lh} and {rw}x{rh}")
    rows: list[list[RGB]] = []
    for y in range(lh):
        row: list[RGB] = list(left[y]) + [background] * gap + list(right[y])
        rows.append(row)
    return write_png(path, lw * 2 + gap, lh, rows)
