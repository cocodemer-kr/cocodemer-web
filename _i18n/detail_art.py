#!/usr/bin/env python3
"""Keep the Korean detail page's artwork; take only the Korean lettering out of it.

The Korean product detail is one tall JPG whose first two blocks are designed
artwork — a composed product photograph with the name set on it, and a tinted
panel carrying the headline copy with a second photograph bleeding in from the
right. Rebuilding those two blocks as plain HTML threw the design away, which is
what made the English page look like a different page rather than the same page
in English.

So keep the artwork and remove only the lettering. Both blocks put their Korean
on a smooth, near-flat ground, so a line can be lifted out by running the rows
above and below through it and smoothing across. Where each line sat is recorded
so the English can be set back in the same place.

Latin lines are left alone: the hero already carries the product's English name.
"""
import os
import re
import subprocess
import tempfile

import numpy as np
import cv2
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'img', 'detail')
OUT = os.path.join(ROOT, 'img', 'detail-en')
KO_RE = re.compile(r'[가-힣]')


def blocks(a, min_gap=12):
    """Split the page where a run of near-white rows spans the full width."""
    grey = a.mean(axis=2)
    white = (grey > 248).mean(axis=1)
    gaps, cur = [], None
    for y in range(a.shape[0]):
        if white[y] > 0.97:
            if cur is None:
                cur = y
        elif cur is not None:
            if y - cur >= min_gap:
                gaps.append((cur, y))
            cur = None
    if cur is not None:
        gaps.append((cur, a.shape[0]))
    out, prev = [], 0
    for b, e in gaps:
        if b - prev > 40:
            out.append((prev, b))
        prev = e
    if a.shape[0] - prev > 40:
        out.append((prev, a.shape[0]))
    return out


def text_runs(a, y0, y1, x0, x1, cut=55, thr=0.004, gap=2, least=6):
    """Rows carrying lettering, grouped into lines."""
    g = a[y0:y1, x0:x1].mean(axis=2)
    bg = np.median(g, axis=1, keepdims=True)
    r = (np.abs(g - bg) > cut).mean(axis=1)
    out, cur = [], None
    for i, v in enumerate(r):
        if v > thr:
            if cur is None:
                cur = i
        elif cur is not None:
            if i - cur >= least:
                out.append((y0 + cur, y0 + i))
            cur = None
    if cur is not None and (y1 - y0) - cur >= least:
        out.append((y0 + cur, y1))
    merged = []
    for s, t in out:
        if merged and s - merged[-1][1] <= gap:
            merged[-1] = (merged[-1][0], t)
        else:
            merged.append((s, t))
    return merged


LATIN_RE = re.compile(r'[A-Za-z]')


def _ocr(tmp, psm):
    try:
        return subprocess.run(['tesseract', tmp, 'stdout', '-l', 'kor+eng', '--psm', psm],
                              capture_output=True, text=True, timeout=60).stdout
    except Exception:                                 # noqa: BLE001
        return ''


def is_korean_line(im, a, y0, y1):
    """A line is Korean when Hangul outweighs Latin in it.

    Asking only whether any Hangul appears is too strict: Tesseract drops the
    odd phantom syllable into a Latin line, which was enough to wipe the
    product's English name off the hero.

    Two things decide whether the read is usable at all. The crop has to be
    tight around the ink and enlarged — handed a line of 24px type floating in
    900px of white, Tesseract returns Latin gibberish. And --psm 7 ("one
    line") returns nothing when the run holds two lines of a centred tagline,
    which then read as Latin by default and left the Korean standing, so fall
    back to the block mode whenever the single-line pass comes back empty.
    """
    xa, xb = ink_span(a, y0, y1, 0, im.width, thr=0.01)
    if xa < 0:
        return False
    box = (max(0, xa - 6), max(0, y0 - 4), min(im.width, xb + 6), y1 + 4)
    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as fh:
        tmp = fh.name
    try:
        c = im.crop(box)
        c.resize((c.width * 3, c.height * 3), Image.LANCZOS).save(tmp)
        txt = _ocr(tmp, '7')
        if len(re.findall(r'[0-9A-Za-z가-힣]', txt)) < 2:
            txt = _ocr(tmp, '6')
        if not txt.strip():
            return True      # 못 읽으면 지우는 쪽이 안전하다
    finally:
        os.unlink(tmp)
    return len(KO_RE.findall(txt)) > len(LATIN_RE.findall(txt))


def wipe(a, y0, y1, x0, x1, pad=5, grow=2):
    """Lift a line of type off the photograph underneath it.

    Only the glyphs are taken out, not the band they sit in. Replacing the
    whole band with a vertical blend and smoothing it turned a tilted black
    card behind one product name into mush and left a grey smear across
    another's paper texture. So mark the pixels that differ from what the rows
    above and below predict — that is the lettering, and nothing else — and let
    the surrounding photograph grow back over them.
    """
    lo, hi = max(0, y0 - pad), min(a.shape[0] - 1, y1 + pad)
    n = hi - lo
    if n < 2:
        return
    t = (np.arange(n) / n)[:, None, None]
    interp = a[lo][None] * (1 - t) + a[hi][None] * t
    m = np.abs(a[lo:hi] - interp).mean(axis=2) > 14
    m[:, :x0] = False
    m[:, x1:] = False
    xs = np.where(m.any(axis=0))[0]
    if not len(xs):
        return
    # 인페인트가 참고할 깨끗한 원본을 위아래·좌우에 남겨 둔다
    pad_y, pad_x = 40, 40
    ry0, ry1 = max(0, lo - pad_y), min(a.shape[0], hi + pad_y)
    rx0, rx1 = max(0, xs.min() - pad_x), min(a.shape[1], xs.max() + pad_x)
    mask = np.zeros((ry1 - ry0, rx1 - rx0), 'uint8')
    mask[lo - ry0:hi - ry0] = m[:, rx0:rx1] * 255
    mask = cv2.dilate(mask, np.ones((3, 3), 'uint8'), iterations=grow)
    sub = np.ascontiguousarray(a[ry0:ry1, rx0:rx1].astype('uint8'))
    a[ry0:ry1, rx0:rx1] = cv2.inpaint(sub, mask, 3, cv2.INPAINT_TELEA).astype(float)


def ink_span(a, y0, y1, x0, x1, cut=55, thr=0.02):
    """Where a band of rows actually carries ink, left and right."""
    seg = a[y0:y1, x0:x1].mean(axis=2)
    bg = np.median(seg, axis=1, keepdims=True)
    col = (np.abs(seg - bg) > cut).mean(axis=0)
    xs = np.where(col > thr)[0]
    return (x0 + xs.min(), x0 + xs.max()) if len(xs) else (-1, -1)


def hl_text_zone(a, g0, g1, w):
    """The rectangle the highlight panel's Korean copy sits in, photo excluded.

    The two designed panels put the copy in different places — one sets it in a
    left column beside the bottle, the other runs it full width above the still
    life — so the zone is measured rather than assumed. A line of type is short
    and narrow; the photograph reads as one tall run of ink spanning most of
    the width, which is what marks the end of the copy.
    """
    wide = []
    for y0, y1 in text_runs(a, g0, g1, 0, w, thr=0.002):
        if y1 - y0 > 200:
            continue
        _, xb = ink_span(a, y0, y1, 0, w)
        if 0 < xb <= w * .75:
            wide.append(xb)
    if not wide:
        return None
    right = min(w, max(wide) + 6)
    runs = []
    for y0, y1 in text_runs(a, g0, g1, 0, right, thr=0.002):
        if y1 - y0 > 200:
            if runs:
                break
            continue
        runs.append((y0, y1))
    if not runs:
        return None
    return runs[0][0], runs[-1][1], right


def row_ground(a, y0, y1, x0, x1):
    """The ground colour of each row of a column band, with the type ignored.

    Interpolating between clean rows is fine for a single line, but the
    highlight panel's left column is type nearly all the way down — there are
    no clean rows to interpolate from, and the leftovers showed as ghost
    lettering. The ground is a smooth vertical wash instead, so read it off
    each row directly: type never covers most of a row, so a percentile taken
    away from the ink side of the row lands on the ground.
    """
    seg = a[y0:y1, x0:x1]
    light = np.median(seg.mean(axis=2)) > 160          # 밝은 바탕 + 어두운 글자
    bg = np.percentile(seg, 85 if light else 15, axis=1)
    k = np.ones(9) / 9
    pad = np.pad(bg, ((4, 4), (0, 0)), mode='edge')
    return np.stack([np.convolve(pad[:, c], k, 'valid') for c in range(3)], axis=1)


# 자동으로 못 잡은 한글 줄 — 눈으로 확인해 좌표를 적어 둔다.
# 세 제품은 한글 제품명이 사진 위에 흰 여백 없이 바로 얹혀 있어 사진과 한 덩어리로
# 잡히고, 선 젤 한 줄은 한글이 작아 Tesseract가 통째로 라틴 문자로 읽는다.
EXTRA_KO = {
    'meilleur-nourishing-cream': [(848, 880)],          # 메이에르 인퓨전 나리싱 크림
    'precieux-body-essence-oil': [(776, 806)],          # 프리셔스 바디 에센셜 오일
    'relaxing-body-cleansing-gel': [(836, 870)],        # 릴렉싱 바디 클렌징 젤
    'meilleur-uv-sun-protecter': [(1088, 1120)],        # 유브이 선 젤 ( UV SUN GEL )
}


def build(slug):
    """Write <slug>-hero.jpg / <slug>-hl.jpg and say where the type sat."""
    path = os.path.join(SRC, slug + '.jpg')
    im = Image.open(path).convert('RGB')
    a = np.asarray(im).astype(float).copy()
    w = im.width
    bs = blocks(a)
    if len(bs) < 2:
        return None
    (h0, h1), (g0, g1) = bs[0], bs[1]
    meta = {'hero': {'h': h1 - h0}, 'hl': {'h': g1 - g0}}

    # ── 히어로: 한글 줄만 지우고, 그 자리를 기록한다 ──────────────
    ko_runs, latin = [], 0
    for y0, y1 in text_runs(a, h0 + 40, h1, int(w * .17), int(w * .83)):
        if y1 - y0 < 14 or y1 - y0 > 220:
            continue
        if is_korean_line(im, a, y0, y1):
            ko_runs.append((y0, y1))
        else:
            latin += 1
    for y0, y1 in EXTRA_KO.get(slug, []):
        if not any(abs(y0 - a0) < 20 for a0, _ in ko_runs):
            ko_runs.append((y0, y1))
            # 이 네 건은 영문 제품명이 아트워크에 남아 있는 걸 눈으로 확인했다.
            # 한글 줄이 사진과 한 덩어리로 잡히는 바람에 영문 줄도 같이 묻혔을 뿐이다.
            latin = max(latin, 1)
    ko_runs.sort()
    for y0, y1 in ko_runs:
        wipe(a, y0, y1, int(w * .13), int(w * .87))
    if ko_runs:
        # 첫 한글 줄은 제품명 자리 — 영문 제품명이 아트워크에 이미 박혀 있으면
        # 비워 두고, 없으면 그 자리에 영문 제품명을 앉힌다
        key = 'gap' if latin else 'name'
        meta['hero'][key] = (ko_runs[0][0] - h0) / (h1 - h0)
        if len(ko_runs) > 1:
            meta['hero']['tag'] = (ko_runs[1][0] - h0) / (h1 - h0)
            meta['hero']['taglines'] = len(ko_runs) - 1
        # 표지가 어두운 제품은 글자가 흰색이었다 — 영문도 흰색으로 얹어야 읽힌다
        lo, hi = ko_runs[0][0] - 20, ko_runs[-1][1] + 20
        meta['hero']['dark'] = bool(a[max(h0, lo):min(h1, hi)].mean() < 120)

    # ── 하이라이트: 왼쪽 글 단만 지운다 (사진은 오른쪽에 있다) ────
    # 이 자리가 얇은 띠면 디자인 패널이 아니라 그냥 다음 문단이다 (세럼류)
    zone = hl_text_zone(a, g0, g1, w) if g1 - g0 >= 700 else None
    if zone is None:
        meta['hl'] = None
    else:
        t, b, right = zone
        # 줄 하나씩 지우면 못 잡은 줄이 유령으로 남는다 — 글 자리 전체를 한 번에 민다
        top = g0 if t - g0 < 90 else t - 25
        bot = g1 if g1 - b < 60 else b + 25
        ground = row_ground(a, top, bot, 0, right)[:, None, :]
        a[top:bot, 0:right] = np.repeat(ground, right, axis=1)
        # 이음매는 원본 쪽으로 서서히 풀어 준다 — 세로줄이 남지 않게
        ramp = min(30, w - right)
        if ramp:
            f = np.linspace(1, 0, ramp)[None, :, None]
            a[top:bot, right:right + ramp] = (
                np.repeat(ground, ramp, axis=1) * f
                + a[top:bot, right:right + ramp] * (1 - f))
        meta['hl']['top'] = (t - g0) / (g1 - g0)
        meta['hl']['col'] = int(right) - 45
        # 글이 판 위쪽을 가로로 채우고 사진이 그 아래 깔린 판은, 글자리를 따로
        # 떼어 배경으로 늘려 쓴다. 영문 카피가 한글보다 길어 고정 높이에 얹으면
        # 사진 위로 흘러넘친다.
        meta['hl']['stack'] = bool(right > w * .6)
        meta['hl']['cut'] = int(bot)

    os.makedirs(OUT, exist_ok=True)
    done = Image.fromarray(a.astype('uint8'))
    done.crop((0, h0, w, h1)).save(
        os.path.join(OUT, f'{slug}-hero.jpg'), quality=90, optimize=True)
    meta['hero']['y'] = [h0, h1]
    hl_path = os.path.join(OUT, f'{slug}-hl.jpg')
    bg_path = os.path.join(OUT, f'{slug}-hlbg.jpg')
    for p in (hl_path, bg_path):
        if os.path.exists(p) and (meta['hl'] is None or p == bg_path):
            os.remove(p)
    if meta['hl'] is not None:
        cut = meta['hl']['cut'] if meta['hl']['stack'] else g0
        if meta['hl']['stack']:
            done.crop((0, g0, w, cut)).save(bg_path, quality=90, optimize=True)
        done.crop((0, cut, w, g1)).save(hl_path, quality=90, optimize=True)
        meta['hl']['y'] = [g0, g1]
    return meta


if __name__ == '__main__':
    import json
    import sys
    slugs = sys.argv[1:] or sorted(f[:-4] for f in os.listdir(SRC) if f.endswith('.jpg'))
    index = {}
    for s in slugs:
        try:
            m = build(s)
        except Exception as exc:                      # noqa: BLE001
            print(f'  {s}: 실패 — {exc}')
            continue
        if m:
            index[s] = m
            hl = f'hl {m["hl"]["h"]}px' if m['hl'] else 'hl 없음'
            print(f'  {s}: hero {m["hero"]["h"]}px, {hl}')
    p = os.path.join(OUT, 'art.json')
    if os.path.exists(p) and len(slugs) < 30:
        old = json.load(open(p, encoding='utf-8'))
        old.update(index)
        index = old
    json.dump(index, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('wrote', p)
