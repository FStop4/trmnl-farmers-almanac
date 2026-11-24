#!/usr/bin/env python3
"""Make 1-bit, dithered e-ink crops from source photos.

Usage: python3 photos/prep_photos.py SRC1.jpg SRC2.jpg SRC3.jpg
Writes photos/farm-N-wide.png (full layout masthead, two per screen) and photos/farm-N-tall.png
(half-horizontal column). Output is exact display size: do not scale in CSS.
Re-encoding drops all EXIF/GPS metadata.
"""
import sys
from pathlib import Path
from PIL import Image, ImageEnhance, ImageFilter, ImageOps

OUT = Path(__file__).resolve().parent
SIZES = {"wide": (128, 60), "tall": (128, 144)}
# Crop focus (x, y) as fractions of the source, one per photo, in argument order.
FOCUS = [(0.55, 0.62), (0.50, 0.45), (0.50, 0.45)]


def crop_to(im, size, focus):
    w, h = size
    scale = max(w / im.width, h / im.height)
    im = im.resize((round(im.width * scale), round(im.height * scale)), Image.LANCZOS)
    x = min(max(round(focus[0] * im.width - w / 2), 0), im.width - w)
    y = min(max(round(focus[1] * im.height - h / 2), 0), im.height - h)
    return im.crop((x, y, x + w, y + h))


def main(paths):
    if len(paths) != len(FOCUS):
        sys.exit(f"Expected {len(FOCUS)} photos, got {len(paths)}")
    for n, (p, focus) in enumerate(zip(paths, FOCUS), 1):
        src = ImageOps.exif_transpose(Image.open(p)).convert("L")
        for name, size in SIZES.items():
            g = crop_to(src, size, focus)
            g = ImageOps.autocontrast(g, cutoff=1)
            g = ImageEnhance.Contrast(g).enhance(1.15)
            g = g.filter(ImageFilter.UnsharpMask(radius=1, percent=60, threshold=2))
            g.convert("1").save(OUT / f"farm-{n}-{name}.png", optimize=True)  # Floyd-Steinberg


if __name__ == "__main__":
    main(sys.argv[1:])
