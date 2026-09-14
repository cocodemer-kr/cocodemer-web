#!/usr/bin/env python3
"""Rebuild the product "Detail" tab in English.

The Korean site shows the detail page as one tall JPG with every line of copy
baked into the pixels, so it cannot be translated. Here the same page is laid
out in HTML instead: the photography is reused from the Korean JPG (cut out by
detail_assets.py) and all the copy is read from the page's own English
Description pane, so the two can never drift apart.

The renderer is deliberately structure-agnostic — it walks whatever sections the
Description pane happens to have. Skincare, cleansing and the Skin Code serums
all use different section sets, and new products will just work.
"""
import html
import json
import re
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load(path, default):
    full = os.path.join(ROOT, path)
    if not os.path.exists(full):
        return default
    with open(full, encoding='utf-8') as fh:
        return json.load(fh)


_CODES = _load('_i18n/active_codes.json', {})
# codes that have an entry on the ingredients page (Mo/Aw/Wh/Tb/Bs are the
# formulation axes, not ingredients, so they stay plain text)
INGREDIENT_IDS = {r['code']: r['id'] for r in _load('_i18n/ingredients.json', [])}
CHIP_ALIAS = {'Hi': 'Hl'}
CHIP_LABELS = _CODES.get('_labels', {})
ACTIVE_CODES = {k: v for k, v in _CODES.items() if not k.startswith('_')}
BANDS = _load('img/detail-en/index.json', {})
# 한글 상세 이미지에서 글자만 지운 아트워크와, 그 글자가 놓여 있던 자리
ART = _load('img/detail-en/art.json', {})
# 영문 상세가 원본으로 존재하는 제품 — 재구성 없이 그대로 쓴다
NATIVE = {k: v for k, v in _load('_i18n/detail_native.json', {}).items()
          if not k.startswith('_')}

# The Korean page prints a large heading over these sections; the English
# Description pane only carries the small eyebrow label, so supply the heading.
HEADINGS = {
    'ACTIVE CODE': 'Key Active Code',
    'HOW TO USE': 'How To Use',
    'RECOMMENDED CARE': 'Your Care Routine',
    'TYPE SUMMARY': 'Your Skin at a Glance',
}


NUM_RE = re.compile(r'^(\d+)\.\s*(.+)$')


def esc(s):
    return html.escape(s, quote=False)


def para(text):
    """Source copy uses newlines as deliberate line breaks — keep them."""
    lines = [esc(l.strip()) for l in text.split('\n') if l.strip()]
    return '<br/>'.join(lines)


def read_sections(p2):
    """Pull the English Description pane apart into ordered sections."""
    out = []
    for ib in p2.select('.ib'):
        lb = ib.select_one('.lb')
        h4 = ib.select_one('h4')
        items = []
        for pt in ib.select('.pt'):
            b = pt.select_one('b')
            ing = pt.select_one('.ing')
            items.append({
                'title': b.get_text(strip=True) if b else '',
                'ing': ing.get_text(strip=True) if ing else '',
                'body': '\n'.join(p.get_text('\n', strip=True)
                                  for p in pt.find_all('p')),
            })
        out.append({
            'label': lb.get_text(strip=True) if lb else '',
            'h4': h4.get_text(strip=True) if h4 else '',
            'items': items,
            'loose': [p.get_text('\n', strip=True)
                      for p in ib.find_all('p', recursive=False)],
        })
    return out


def _chips(slug, up):
    codes = ACTIVE_CODES.get(slug) or []
    if not codes:
        return ''
    items = []
    for c in codes:
        inner = (f'<span class="hx">{esc(c)}</span>'
                 f'<span class="hl">{esc(CHIP_LABELS.get(c, c))}</span>')
        ref = INGREDIENT_IDS.get(CHIP_ALIAS.get(c, c))
        if ref:
            inner = f'<a href="{up}ingredients.html#{esc(ref)}">{inner}</a>'
        items.append(f'<li>{inner}</li>')
    return '<ul class="dx-chips">' + ''.join(items) + '</ul>'


def _how_to_use(text):
    """Korean copy numbers the steps with ①②③; turn those into a real list."""
    steps, notes = [], []
    for line in text.split('\n'):
        line = line.strip()
        if not line:
            continue
        if line[0] in '①②③④⑤⑥':
            steps.append(line[1:].strip())
        elif line[0] in '*※':
            notes.append(line.lstrip('*※ ').strip())
        elif steps:
            steps[-1] += ' ' + line
        else:
            notes.append(line)
    out = []
    if steps:
        out.append('<ol>' + ''.join(f'<li>{esc(s)}</li>' for s in steps) + '</ol>')
    out += [f'<p class="dx-note">* {esc(n)}</p>' if steps else
            f'<p>{esc(n)}</p>' for n in notes]
    return ''.join(out)


def _section(sec, slug, shots, up=''):
    """Render one Description section. `shots` is consumed for ACTIVE CODE."""
    label = sec['label']
    is_code = label.upper() == 'ACTIVE CODE'
    is_use = label.upper() == 'HOW TO USE'
    o = [f'<section class="dx-sec{" dx-code" if is_code else ""}">']
    if label:
        o.append(f'<div class="dx-lb">{esc(label)}</div>')
    heading = sec['h4'] or HEADINGS.get(label.upper(), '')
    if heading:
        o.append(f'<h3>{esc(heading)}</h3>')
    if is_code:
        o.append(_chips(slug, up))

    if is_use:
        o.append(_how_to_use('\n'.join(sec['loose'])))
        o.append('</section>')
        return ''.join(o)

    paired = is_code and len(shots) == len(sec['items']) and shots
    for i, it in enumerate(sec['items']):
        # 한글판은 특장점을 큰 번호 + 제목으로 짜 놓았다 — 번호가 붙어 있으면 그대로 따른다
        num = NUM_RE.match(it['title'] or '')
        cls = 'dx-it dx-num' if num and not paired else 'dx-it'
        o.append(f'<figure class="{cls}">' if paired else f'<div class="{cls}">')
        if paired:
            o.append(f'<img alt="" loading="lazy" src="{shots[i]}"/>')
        if num and not paired:
            o.append(f'<span class="n">{esc(num.group(1))}.</span>')
        o.append('<figcaption>' if paired else '<div>')
        if it['title']:
            o.append(f'<b>{esc(num.group(2) if num and not paired else it["title"])}</b>')
        if it['ing']:
            o.append(f'<span class="dx-ing">{esc(it["ing"])}</span>')
        if it['body']:
            o.append(f'<p>{para(it["body"])}</p>')
        o.append('</figcaption>' if paired else '</div>')
        o.append('</figure>' if paired else '</div>')

    for text in sec['loose']:
        cls = ' class="dx-note"' if text.strip()[:1] in '*※' else ''
        o.append(f'<p{cls}>{para(text)}</p>')
    o.append('</section>')
    return ''.join(o)


def _highlight(sec, slug, hl, up):
    """The HIGHLIGHT copy set back onto its own panel artwork."""
    art = f'<img alt="" src="{up}img/detail-en/{slug}-hl.jpg"/>'
    if hl.get('stack'):
        # 글자리를 배경으로 늘리고 사진은 그 아래 — 영문이 길어져도 넘치지 않는다
        o = ['<section class="dx-hl dx-stack">',
             f'<div class="in" style="background-image:url({up}img/detail-en/'
             f'{slug}-hlbg.jpg)">']
    else:
        col = hl['col'] / 900 * 100      # 한글 원본의 글 단 폭을 비율로
        o = ['<section class="dx-hl">', art,
             f'<div class="in" style="--t:{hl["top"] * 100:.1f}%;--w:{col:.1f}%">']
    if sec['h4']:
        o.append(f'<h3>{esc(sec["h4"])}</h3>')
    for it in sec['items']:
        o.append('<div class="pt">')
        if it['title']:
            o.append(f'<b>{esc(it["title"])}</b>')
        if it['body']:
            o.append(f'<p>{para(it["body"])}</p>')
        o.append('</div>')
    o.append('</div>')
    if hl.get('stack'):
        o.append(art)
    o.append('</section>')
    return ''.join(o)


def build_pane(soup, slug, depth):
    """Return the English detail pane markup, or None if there's nothing to build."""
    # 영문 상세가 원본으로 있는 제품은 재구성할 이유가 없다 — 그대로 얹는다
    if slug in NATIVE:
        up = '../' * (depth - 1)
        name = soup.select_one('.pd-info h1')
        alt = esc(name.get_text(strip=True)) if name else ''
        return '<div class="detail-img">' + ''.join(
            f'<img alt="{alt} detail {i}" loading="lazy" src="{up}{f}"/>'
            for i, f in enumerate(NATIVE[slug], 1)) + '</div>'
    p2 = soup.select_one('#p2')
    if not p2:
        return None
    # Paths are written as the Korean source would write them; build.py's
    # fix_paths() adds the one extra '../' for the /en/ level afterwards.
    up = '../' * (depth - 1)
    sections = read_sections(p2)
    if not sections:
        return None

    # detail_assets.py already drops the hero band; everything listed is usable
    bands = [f'{up}img/detail-en/{b["file"]}' for b in BANDS.get(slug, [])]

    code_sec = next((s for s in sections if s['label'].upper() == 'ACTIVE CODE'), None)
    # 원료 사진은 ACTIVE CODE 항목과 1:1로 붙는다. 다만 항목이 하나뿐인 세럼은
    # 한 장뿐인 밴드가 원료 사진이 아니라 16타입 도표라서, 짝을 지으면 도표가
    # 원료 사진 자리에 들어가 버린다.
    n_items = len(code_sec['items']) if code_sec and len(code_sec['items']) > 1 else 0
    shots = bands[-n_items:] if n_items and len(bands) >= n_items else []
    spare = bands[:len(bands) - len(shots)]

    h1 = soup.select_one('.pd-info h1')
    lead = soup.select_one('.pd-lead')
    name = h1.get_text(strip=True) if h1 else ''
    tagline = lead.get_text(strip=True) if lead else ''

    art = ART.get(slug) or {}
    o = ['<div class="dx">']
    if art:
        # 한글 상세 이미지의 표지 그대로, 글자만 영문으로 앉힌다
        hero = art['hero']
        o.append('<section class="dx-hero dx-art%s">'
                 % (' on-dark' if hero.get('dark') else ''))
        o.append(f'<img alt="{esc(name)}" src="{up}img/detail-en/{slug}-hero.jpg"/>')
        if 'name' in hero:
            o.append(f'<h2 style="top:{hero["name"] * 100:.1f}%">{esc(name)}</h2>')
        if tagline and 'tag' in hero:
            o.append(f'<p class="dx-tag" style="top:{hero["tag"] * 100:.1f}%">'
                     f'{esc(tagline)}</p>')
        o.append('</section>')
    else:
        o.append('<section class="dx-hero">')
        o.append(f'<img alt="{esc(name)}" loading="lazy" '
                 f'src="{up}img/product/{slug}.jpg"/>')
        o.append(f'<h2>{esc(name)}</h2>')
        # the serums repeat their lead line as the first section heading
        if tagline and tagline != (sections[0]['h4'] or ''):
            o.append(f'<p class="dx-tag">{esc(tagline)}</p>')
        o.append('</section>')

    # 하이라이트 패널이 아트워크인 제품은 그 판을 그대로 쓰고 글만 얹는다
    hl = art.get('hl')
    if hl and sections and sections[0]['label'].upper() == 'HIGHLIGHT':
        o.append(_highlight(sections.pop(0), slug, hl, up))

    for i, sec in enumerate(sections):
        o.append(_section(sec, slug, shots, up))
        # spare photography goes between sections, as the original page does
        if i < len(spare):
            o.append(f'<img alt="" class="dx-band" loading="lazy" src="{spare[i]}"/>')
        if sec['label'].upper() == 'TECHNOLOGY':
            o.append(f'<img alt="L-CODEMAR ELIXIR" class="dx-elixir" '
                     f'loading="lazy" src="{up}img/elixir.jpg"/>')
            o.append(f'<img alt="How the skin barrier works" class="dx-band" '
                     f'loading="lazy" src="{up}img/barrier-en.jpg"/>')

    for extra in spare[len(sections):]:
        o.append(f'<img alt="" class="dx-band" loading="lazy" src="{extra}"/>')

    o.append('</div>')
    return ''.join(o)
