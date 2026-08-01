"""Generate assets/ghmanage.ico - the app, shortcut, and Setup.exe icon.

Pure standard library (no Pillow), so it runs anywhere Python does.  The icon is
committed to the repo; re-run this only when the artwork changes:

    python assets\\make_icon.py

Artwork: a dark rounded square (GitHub graphite) holding three white "list rows",
each tagged with a status dot — the app is a list of issues, PRs, and commits.
Everything is drawn at 4x and box-filtered down, which gives clean antialiasing
without a graphics library.
"""

from __future__ import annotations

import struct
import zlib
from pathlib import Path

# ── palette ──────────────────────────────────────────────────────────────────
BG = (36, 41, 47)  # GitHub graphite
ROW = (255, 255, 255)
DOTS = [
    (63, 185, 80),  # open  — green
    (163, 113, 247),  # merged — purple
    (47, 129, 247),  # info  — blue
]

SS = 4  # supersampling factor
# ICO entries: BMP for the small sizes (widest compatibility), PNG for the big ones.
BMP_SIZES = [16, 20, 24, 32, 48, 64]
PNG_SIZES = [128, 256]


def _rounded_rect_alpha(px: float, py: float, x0: float, y0: float,
                        x1: float, y1: float, r: float) -> bool:
    """True when the point is inside the rounded rectangle."""
    if px < x0 or px > x1 or py < y0 or py > y1:
        return False
    cx = min(max(px, x0 + r), x1 - r)
    cy = min(max(py, y0 + r), y1 - r)
    return (px - cx) ** 2 + (py - cy) ** 2 <= r * r


def render(size: int) -> bytes:
    """Render the icon at `size` px, returning RGBA bytes (top-down)."""
    n = size * SS
    u = n / 256.0  # design units: artwork is authored on a 256x256 grid

    # Geometry, in design units scaled to the supersampled canvas.
    bg_r = 48 * u
    rows = []
    row_h, row_gap = 34 * u, 26 * u
    row_x0, row_x1 = 56 * u, 208 * u
    top = 62 * u
    for i in range(3):
        y0 = top + i * (row_h + row_gap)
        rows.append((y0, y0 + row_h))
    dot_r = 11 * u
    dot_cx = 40 * u

    # Supersampled render, then box-downsample to `size`.
    hi = bytearray(n * n * 4)
    for y in range(n):
        py = y + 0.5
        for x in range(n):
            px = x + 0.5
            o = (y * n + x) * 4
            if not _rounded_rect_alpha(px, py, 0, 0, n, n, bg_r):
                continue  # transparent outside the rounded square
            r, g, b = BG
            for i, (y0, y1) in enumerate(rows):
                cy = (y0 + y1) / 2
                if _rounded_rect_alpha(px, py, row_x0, y0, row_x1, y1, row_h / 2):
                    r, g, b = ROW
                    break
                if (px - dot_cx) ** 2 + (py - cy) ** 2 <= dot_r * dot_r:
                    r, g, b = DOTS[i]
                    break
            hi[o:o + 4] = bytes((r, g, b, 255))

    out = bytearray(size * size * 4)
    area = SS * SS
    for y in range(size):
        for x in range(size):
            acc = [0, 0, 0, 0]
            for dy in range(SS):
                for dx in range(SS):
                    o = ((y * SS + dy) * n + (x * SS + dx)) * 4
                    a = hi[o + 3]
                    acc[0] += hi[o] * a
                    acc[1] += hi[o + 1] * a
                    acc[2] += hi[o + 2] * a
                    acc[3] += a
            a = acc[3] // area
            if acc[3]:
                px = bytes((acc[0] // acc[3], acc[1] // acc[3], acc[2] // acc[3], a))
            else:
                px = b"\x00\x00\x00\x00"
            o = (y * size + x) * 4
            out[o:o + 4] = px
    return bytes(out)


def to_png(rgba: bytes, size: int) -> bytes:
    raw = b"".join(b"\x00" + rgba[y * size * 4:(y + 1) * size * 4] for y in range(size))

    def chunk(tag: bytes, data: bytes) -> bytes:
        return (struct.pack(">I", len(data)) + tag + data
                + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))

    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw, 9))
            + chunk(b"IEND", b""))


def to_bmp(rgba: bytes, size: int) -> bytes:
    """32bpp bottom-up DIB plus the (unused but expected) 1bpp AND mask."""
    header = struct.pack("<IiiHHIIiiII", 40, size, size * 2, 1, 32, 0, 0, 0, 0, 0, 0)
    pixels = bytearray()
    for y in range(size - 1, -1, -1):
        for x in range(size):
            o = (y * size + x) * 4
            r, g, b, a = rgba[o:o + 4]
            pixels += bytes((b, g, r, a))
    mask_stride = ((size + 31) // 32) * 4
    return bytes(header) + bytes(pixels) + b"\x00" * (mask_stride * size)


def main() -> None:
    images: list[tuple[int, bytes]] = []
    for size in BMP_SIZES:
        images.append((size, to_bmp(render(size), size)))
    for size in PNG_SIZES:
        images.append((size, to_png(render(size), size)))

    offset = 6 + 16 * len(images)
    directory, blobs = bytearray(struct.pack("<HHH", 0, 1, len(images))), bytearray()
    for size, data in images:
        directory += struct.pack(
            "<BBBBHHII", size & 0xFF, size & 0xFF, 0, 0, 1, 32, len(data), offset)
        blobs += data
        offset += len(data)

    out = Path(__file__).with_name("ghmanage.ico")
    out.write_bytes(bytes(directory) + bytes(blobs))
    print(f"Wrote {out} ({out.stat().st_size:,} bytes, "
          f"{len(images)} sizes: {', '.join(str(s) for s, _ in images)})")


if __name__ == "__main__":
    main()
