"""Generate assets/ghmanage.icns - the macOS app, Dock, and DMG icon.

The Mac counterpart to make_icon.py, and it reuses that module's renderer, so
both platforms' icons are the same artwork from the same source. Only the
container format differs: Windows wants .ico, macOS wants .icns.

Like the .ico, the result is committed to the repo. Re-run this only when the
artwork in make_icon.py changes:

    python3 assets/make_icns.py

macOS only - it shells out to `iconutil`, which ships with the OS. Writing
.icns by hand is possible (it is a simple tag/length/payload container), but
iconutil is the reference implementation and gets the @2x pairing right, which
is the part Finder is fussy about. An .icns assembled by hand with the wrong
type codes renders as a generic blank document icon and gives no clue why.

Takes roughly a minute: the renderer is pure Python and supersamples 4x, so
the 512px icon alone is a 2048x2048 pixel loop. That is fine for a script that
runs when the artwork changes and never in CI.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from make_icon import render, to_png  # noqa: E402

# The iconset layout iconutil expects. Each entry is (base size, is_retina):
# a "128x128@2x" slot holds a 256px image, and Finder picks whichever matches
# the display. Omitting the @2x variants would leave the icon blurry on every
# Mac sold in the last decade, since all of them are Retina.
ICONSET = [
    (16, False), (16, True),
    (32, False), (32, True),
    (128, False), (128, True),
    (256, False), (256, True),
    (512, False), (512, True),
]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default=str(Path(__file__).with_name("ghmanage.icns")),
        help="output path (default: assets/ghmanage.icns)",
    )
    args = parser.parse_args()

    if sys.platform != "darwin":
        sys.exit("Error: make_icns.py needs macOS (it uses iconutil).")
    if not shutil.which("iconutil"):
        sys.exit("Error: iconutil not found. Install the Xcode command line tools.")

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp:
        iconset = Path(tmp) / "ghmanage.iconset"
        iconset.mkdir()

        # Render each distinct pixel size once, then write it to every slot
        # that wants it: 32x32@2x and 64x64 are the same 64px image, and
        # rendering it twice would just burn another few seconds.
        cache: dict[int, bytes] = {}
        for base, retina in ICONSET:
            px = base * 2 if retina else base
            if px not in cache:
                print(f"  rendering {px}x{px}...", flush=True)
                cache[px] = to_png(render(px), px)
            name = f"icon_{base}x{base}{'@2x' if retina else ''}.png"
            (iconset / name).write_bytes(cache[px])

        subprocess.run(
            ["iconutil", "--convert", "icns", "--output", str(out), str(iconset)],
            check=True,
        )

    print(f"Wrote {out} ({out.stat().st_size:,} bytes, "
          f"{len(cache)} sizes: {', '.join(str(s) for s in sorted(cache))})")


if __name__ == "__main__":
    main()
