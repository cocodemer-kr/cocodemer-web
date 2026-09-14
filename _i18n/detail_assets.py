#!/usr/bin/env python3
"""Cut the reusable photography out of the Korean detail JPGs.

Each product detail image is one tall JPG (900 x ~11,000) with the copy baked in
as Korean text. For the English pages we rebuild the pane in HTML, so all we
need from the JPG is the photography: the texture band and the ACTIVE CODE
shots. This script finds those bands and writes them to img/detail-en/.
"""
import glob
import json
import os
import re
import subprocess
import sys
import tempfile

import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'img', 'detail')
OUT = os.path.join(ROOT, 'img', 'detail-en')


def content_blocks(std, height, min_gap=10):
    """Split the page at runs of perfectly flat rows (the design's whitespace)."""
    flat = std < 3.0
    runs, start = [], None
    for y in range(height):
        if flat[y] and start is None:
            start = y
        elif not flat[y] and start is not None:
            if y - start >= min_gap:
                runs.append((start, y))
            start = None
    if start is not None and height - start >= min_gap:
        runs.append((start, height))
    blocks, prev = [], 0
    for b, e in runs:
        if b - prev > 20:
            blocks.append((prev, b))
        prev = e
    if height - prev > 20:
        blocks.append((prev, height))
    return blocks


def longest_photo_run(ink, b, e, thr=0.45):
    """Longest run of rows that are covered edge to edge — i.e. a photo."""
    best = (0, 0, 0)
    cur = None
    for y in range(b, e):
        if ink[y] >= thr:
            if cur is None:
                cur = y
        elif cur is not None:
            if y - cur > best[0]:
                best = (y - cur, cur, y)
            cur = None
    if cur is not None and e - cur > best[0]:
        best = (e - cur, cur, e)
    return best


def text_rows(a, b, e, contrast=62):
    """Rows that look like a line of type: a few pixels far from the row's own
    background colour. Measured against the row median, so it catches white
    lettering on a dark photo as well as black on white."""
    seg = a[b:e].mean(axis=2)
    bg = np.median(seg, axis=1, keepdims=True)
    cover = (np.abs(seg - bg) > contrast).mean(axis=1)
    return (cover > 0.004) & (cover < 0.32)


def _runs(mask, lo, hi, min_len=14):
    out, cur = [], None
    for i in range(lo, hi):
        if mask[i] and cur is None:
            cur = i
        elif not mask[i] and cur is not None:
            if i - cur >= min_len:
                out.append((cur, i))
            cur = None
    if cur is not None and hi - cur >= min_len:
        out.append((cur, hi))
    return out


def trim_caption(a, b, e, look=210):
    """Captions are set on a flat strip at the top or bottom of the photo band.

    Walk in from each edge for as long as the rows keep looking like caption:
    either blank or a sparse line of type, and never carrying real colour. The
    first row of actual picture stops the walk.
    """
    seg = a[b:e].astype(float)
    grey = seg.mean(axis=2)
    even = grey.std(axis=1) < 7
    typed = text_rows(a, b, e)
    plain = (seg.max(axis=2) - seg.min(axis=2)).mean(axis=1) < 25
    caption = (even | typed) & plain
    n = len(caption)

    bottom = n
    while bottom > 0 and caption[bottom - 1]:
        bottom -= 1
    top = 0
    while top < bottom and caption[top]:
        top += 1
    # keep a little breathing room, and never trim away the whole band
    if bottom < n:
        bottom = min(n, bottom + 4)
    if top > 0:
        top = max(0, top - 4)
    if bottom - top < 200:
        return b, e
    return b + top, b + bottom


KO_RE = re.compile(r'[가-힣]')


def korean_count(im):
    """How much Korean type is left in this crop, per OCR.

    Read with kor+eng, not kor alone: given only Korean to work with, Tesseract
    will happily render Latin display type as Hangul — the 16-type chart came
    back as 21 Korean characters that way, and as none with both languages on.
    """
    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as fh:
        tmp = fh.name
    try:
        im.save(tmp)
        out = subprocess.run(['tesseract', tmp, 'stdout', '-l', 'kor+eng', '--psm', '11'],
                             capture_output=True, text=True, timeout=90).stdout
    except Exception:
        return 0
    finally:
        os.unlink(tmp)
    return len(KO_RE.findall(out))


# The 16-type chart is set entirely in Latin display type, but on two of the
# sixteen serums Tesseract still hallucinates a handful of Hangul out of it.
# Both crops were checked by eye and are clean, so they are allowed through
# rather than loosening the gate for every band.
VERIFIED_CLEAN = {
    ('skin-code-serum-03-drnw', 8639, 8906),
    ('skin-code-serum-04-drpw', 9494, 9761),
}

# Bands whose Korean cannot be cropped away without losing the picture: a
# product shot whose packaging copy is the subject, or a heading set into the
# middle of the photograph. The English pane already leads with the clean
# cutout, so these are simply left out rather than shipped with Korean on them.
DROP = {
    ('claire-blanc-cleansing-water', 0),    # "2 IN 1 클렌져" across the photo
    ('hydra-velour-essential-mask', 0),     # jar shot, Korean label
    ('meilleur-eye-contour-cream', 0),      # jar shot, Korean label
    ('meilleur-nourishing-cream', 0),       # jar + carton, Korean copy
    ('meilleur-uv-sun-protecter', 2),       # "자외선 & Sweat Proof" over the leaves
    ('purifiant-clay-mask', 0),             # jar shot, Korean label
    ('relief-hydra-body-lotion', 0),        # heading set into the texture shot
}


def trim_until_clean(im, b, e, step=40, limit=360, floor=230, tol=4):
    """Shave the edges back until OCR stops finding Korean.

    The caption sits on the photo itself in some layouts, so geometry alone
    can't find it reliably — this checks the actual result instead. Returns
    None when the band can't be cleared without losing the picture.
    """
    if korean_count(im.crop((0, b, 900, e))) < tol:
        return b, e
    for cut in range(step, limit + 1, step):
        for nb, ne in ((b, e - cut), (b + cut, e)):
            if ne - nb < floor:
                continue
            if korean_count(im.crop((0, nb, 900, ne))) < tol:
                return nb, ne
    return None


def is_copy_panel(a, b, e):
    """Tell a block of set copy from photography.

    A copy panel is lines of type on one flat colour: plenty of perfectly even
    rows (the gaps between lines), plenty of sparse-mark rows (the lines), and
    no colour. A smooth gradient photo also has even rows but no type; a flat
    illustration has some of both but keeps its colour.
    """
    seg = a[b:e].astype(float)
    even = (seg.mean(axis=2).std(axis=1) < 7).mean()
    typed = text_rows(a, b, e).mean()
    colour = (seg.max(axis=2) - seg.min(axis=2)).mean()
    return even > 0.32 and typed > 0.25 and colour < 25


def extract(slug):
    path = os.path.join(SRC, slug + '.jpg')
    im = Image.open(path).convert('RGB')
    a = np.asarray(im).astype(np.int16)
    height = a.shape[0]
    std = a.std(axis=(1, 2))
    ink = (np.abs(255 - a).max(axis=2) > 18).mean(axis=1)

    candidates = []
    for b, e in content_blocks(std, height):
        if e - b < 250:
            continue
        run, rb, re_ = longest_photo_run(ink, b, e)
        if run < 250:
            continue
        candidates.append((rb, re_))

    # The first band is the hero — a composite with the Korean product name set
    # into it. The English page uses the clean shot from img/product/ instead, so
    # the hero is never written out and no Korean lettering ships.
    bands = []
    for rb, re_ in candidates[1:]:
        tb, te = trim_caption(a, rb, re_)
        if te - tb < 200 or is_copy_panel(a, tb, te):
            continue
        if (slug, tb, te) in VERIFIED_CLEAN:
            cleaned = (tb, te)
        else:
            cleaned = trim_until_clean(im, tb, te)
        if cleaned is None:
            continue
        bands.append(cleaned)

    # One flat folder, <slug>-NN.jpg — a folder per product meant 34 separate
    # uploads every time these were rebuilt.
    os.makedirs(OUT, exist_ok=True)
    for old in glob.glob(os.path.join(OUT, f'{slug}-*.jpg')):
        os.remove(old)
    saved = []
    for i, (b, e) in enumerate(bands):
        if e - b < 200 or (slug, i) in DROP:
            continue
        name = f'{slug}-{i:02d}.jpg'
        im.crop((0, b, 900, e)).save(os.path.join(OUT, name),
                                     quality=86, optimize=True)
        saved.append({'file': name, 'y0': b, 'y1': e, 'h': e - b})
    return saved


if __name__ == '__main__':
    slugs = sys.argv[1:] or sorted(
        f[:-4] for f in os.listdir(SRC) if f.endswith('.jpg'))
    index = {}
    for slug in slugs:
        index[slug] = extract(slug)
        print(f'  {slug}: {len(index[slug])} bands')
    manifest = os.path.join(OUT, 'index.json')
    if os.path.exists(manifest) and len(slugs) < 30:
        old = json.load(open(manifest, encoding='utf-8'))
        old.update(index)
        index = old
    json.dump(index, open(manifest, 'w', encoding='utf-8'), indent=1)
    print('wrote', manifest)
