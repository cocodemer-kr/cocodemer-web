#!/usr/bin/env python3
"""Re-cut the product card shots from the Korean detail images.

The hero at the top of each detail JPG is a styled product photo with the
product name set underneath. The card needs the photo without the lettering,
and — this is what the first attempt got wrong — with the whole product inside
the frame. So: find where the name starts, find where the product sits, and
choose a window of fixed proportion that contains it.
"""
import csv
import io
import json
import os
import subprocess
import sys
import tempfile

import numpy as np
from PIL import Image, ImageOps
from scipy import ndimage

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'img', 'detail')
OUT = os.path.join(ROOT, 'img', 'product')

CARD_W, CARD_H = 900, 760          # card proportion, 900 wide by convention
BLOCK = 16                          # texture is measured in blocks this size
MARGIN = 26                         # clear space to keep around the product


def _ocr_tops(crop, floor, min_height):
    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as fh:
        tmp = fh.name
    try:
        crop.save(tmp)
        out = subprocess.run(
            ['tesseract', tmp, 'stdout', '-l', 'kor+eng', '--psm', '6', 'tsv'],
            capture_output=True, text=True, timeout=90).stdout
    except Exception:
        return []
    finally:
        os.unlink(tmp)
    tops = []
    for row in csv.DictReader(io.StringIO(out), delimiter='\t'):
        try:
            conf = float(row.get('conf', -1))
        except (TypeError, ValueError):
            continue
        if conf <= 45 or len((row.get('text') or '').strip()) < 2:
            continue
        top, height = int(row['top']), int(row['height'])
        if top >= floor and height >= min_height:
            tops.append(top)
    return tops


def text_top(im, look=1400, floor=380, min_height=18):
    """Where the product name starts, per OCR.

    Only large type below the halfway mark counts: the label on the bottle and
    the fine print on an ampoule are part of the photograph, and reading those
    as the name put the crop window in the wrong place. One product sets its
    name in white on a dark photograph, which Tesseract reads as nothing at
    all — so a page that comes back empty is read again inverted.
    """
    crop = im.crop((0, 0, im.width, look))
    tops = _ocr_tops(crop, floor, min_height)
    if not tops:
        tops = _ocr_tops(ImageOps.invert(crop.convert('L')), floor, min_height)
    return min(tops) if tops else look


def product_box(im, bottom):
    """Where the product sits in the photo area.

    The set is built from large flat planes — pale grey, black, mid grey — so
    the background is smooth almost everywhere and sharp only along the few
    long straight edges between planes. The product is the one compact patch of
    sustained fine detail: label type, the cap's curve, its shadow. Measuring
    texture per block and keeping the biggest blob that isn't a line finds it.
    """
    grey = np.asarray(im.convert('L'), dtype=float)[:bottom]
    h, w = grey.shape
    bh, bw = h // BLOCK, w // BLOCK
    blocks = grey[:bh * BLOCK, :bw * BLOCK].reshape(bh, BLOCK, bw, BLOCK)
    texture = blocks.std(axis=(1, 3))

    mask = texture > max(6.0, np.percentile(texture, 82))
    # a plane boundary is one block wide; erode it away, keep the product
    mask = ndimage.binary_opening(mask, np.ones((2, 2)))
    labels, count = ndimage.label(mask)
    if not count:
        return None
    best, best_score = None, 0
    for i in range(1, count + 1):
        ys, xs = np.where(labels == i)
        hgt = int(ys.max() - ys.min()) + 1
        wid = int(xs.max() - xs.min()) + 1
        area = len(ys)
        if min(hgt, wid) < 2:
            continue
        # favour solid, compact blobs over long thin edges
        score = area * min(hgt, wid) / max(hgt, wid)
        if score > best_score:
            best_score, best = score, (ys, xs)
    if best is None:
        return None
    ys, xs = best
    return (xs.min() * BLOCK, ys.min() * BLOCK,
            (xs.max() + 1) * BLOCK, (ys.max() + 1) * BLOCK)


def window(im, slug):
    """Pick the crop: as tall as the lettering allows, centred on the product."""
    limit = max(400, text_top(im) - 14)
    height = min(CARD_H, limit)
    box = product_box(im, limit)
    if box:
        top = (box[1] + box[3]) / 2 - height / 2
        top = min(max(0, top), limit - height)
        # never clip the product itself if it can be avoided
        top = min(top, max(0, box[1] - MARGIN))
        top = max(top, min(limit - height, box[3] + MARGIN - height))
    else:
        top = 0
    return int(round(top)), int(height), box


def cut(slug):
    im = Image.open(os.path.join(SRC, slug + '.jpg')).convert('RGB')
    top, height, box = window(im, slug)
    crop = im.crop((0, top, CARD_W, top + height))
    if height != CARD_H:                 # keep every card the same proportion
        crop = crop.resize((CARD_W, CARD_H), Image.LANCZOS)
    crop.save(os.path.join(OUT, slug + '.jpg'), quality=90, optimize=True)
    return {'top': top, 'height': height, 'box': box}


if __name__ == '__main__':
    slugs = sys.argv[1:] or sorted(
        f[:-4] for f in os.listdir(SRC)
        if f.endswith('.jpg') and f != 'skin-code-common.jpg')
    report = {}
    for slug in slugs:
        report[slug] = cut(slug)
        print(f'  {slug}: top={report[slug]["top"]} h={report[slug]["height"]}')
    print(json.dumps({k: v['box'] for k, v in report.items()}, indent=1)[:400])
