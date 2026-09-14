#!/usr/bin/env python3
"""Shave leftover Korean lettering off the edges of the extracted photo bands.

detail_assets.py cut these bands out of the Korean detail JPGs and gated them
with OCR. OCR was the wrong gate: it invents single syllables out of photo
texture, and it misses a heading that has been sliced through the middle —
which is exactly what survived, a part-height line of display type sitting on
the last rows of a band.

So look for the shape instead. Lettering is a sparse scatter of much darker
pixels spread across the row; a photograph is either evenly covered or evenly
empty. Walk in from the edge while the rows keep looking like lettering, and
give up if the walk runs so far that it must be eating the picture.
"""
import os
import sys

import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'img', 'detail-en')
LIMIT = 0.22          # never take more than this share of the band off one edge
FLOOR = 170           # nor leave less than this many rows


def ink_rows(a, cut=55):
    """Per row: the share of pixels far from that row's own ground.

    Distance, not darkness — the Korean headings are set white-on-grey as often
    as black-on-white, and an earlier darkness-only version walked straight past
    the light ones.
    """
    grey = a.mean(axis=2)
    bg = np.median(grey, axis=1, keepdims=True)
    return (np.abs(grey - bg) > cut).mean(axis=1)


def _walk(ink, n, lo=0.02, hi=0.40):
    """How many rows from index 0 keep looking like a line of type."""
    i = 0
    while i < n and (lo < ink[i] < hi or ink[i] <= 0.002):
        i += 1
    # a run of pure blank rows is just margin — don't count it as lettering
    while i > 0 and ink[i - 1] <= 0.002:
        i -= 1
    return i


def trim(path, pad=6):
    im = Image.open(path).convert('RGB')
    a = np.asarray(im).astype(float)
    h = a.shape[0]
    ink = ink_rows(a)
    room = int(h * LIMIT)

    bot = _walk(ink[::-1], room)
    top = _walk(ink, room)
    if bot >= room:
        bot = 0
    if top >= room:
        top = 0
    if not bot and not top:
        return None
    y0 = top + pad if top else 0
    y1 = h - bot - pad if bot else h
    if y1 - y0 < FLOOR:
        return None
    im.crop((0, y0, im.width, y1)).save(path, quality=88, optimize=True)
    return h, y1 - y0


if __name__ == '__main__':
    import glob
    targets = sys.argv[1:] or sorted(glob.glob(os.path.join(OUT, '*.jpg')))
    n = 0
    for p in targets:
        r = trim(p)
        if r:
            n += 1
            print(f'  {os.path.relpath(p, ROOT):58s} {r[0]:5d} -> {r[1]}')
    print(f'{n}/{len(targets)} 장 잘라냄')
