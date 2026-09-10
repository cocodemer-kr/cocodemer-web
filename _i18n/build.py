#!/usr/bin/env python3
"""COCODEMER — build the English (/en/) mirror from the Korean source pages."""
import json, os, re, sys, glob, shutil
from bs4 import BeautifulSoup, NavigableString

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
I18N = os.path.join(ROOT, '_i18n')
KO_RE = re.compile(r'[가-힣]')
SITE = 'https://www.cocodemer.co.kr'

def load_dicts():
    d = {}
    for f in sorted(glob.glob(os.path.join(I18N, '*.json'))):
        if os.path.basename(f).startswith('_'):
            continue
        for k, v in json.load(open(f, encoding='utf-8')).items():
            if k.startswith('_'):
                continue
            d[k] = v
    return d

TR = load_dicts()
MISSING = {}

SERUM_RE = re.compile(r'^스킨 코드 세럼 (\d{2}) ([A-Z]{4})$')

def _rule(key):
    """Mechanical name rules, applied before falling back to 'missing'."""
    m = SERUM_RE.match(key)
    if m:
        return f'Skin Code Serum {m.group(1)} {m.group(2)}'
    if key.startswith('코코드메르 '):
        rest = key[len('코코드메르 '):]
        sub = TR.get(rest) or _rule(rest)
        if sub:
            return 'COCODEMER ' + sub
    for suffix, repl in ((' 상세 1', ' detail 1'), (' 상세 2', ' detail 2')):
        if key.endswith(suffix):
            base = key[: -len(suffix)]
            sub = TR.get(base) or _rule(base)
            if sub:
                return sub + repl
    return None

def tr(s, where=''):
    """Translate a whole string; record misses."""
    key = s.strip()
    if not key or not KO_RE.search(key):
        return s
    if key not in TR:
        r = _rule(key)
        if r:
            TR[key] = r
    if key in TR:
        out = TR[key]
        # preserve surrounding whitespace
        lead = s[:len(s) - len(s.lstrip())]
        tail = s[len(s.rstrip()):]
        return lead + out + tail
    MISSING.setdefault(key, set()).add(where)
    return s

# ---------- path rewriting ----------
ASSET_DIRS = ('css/', 'img/', 'js/')

def fix_paths(soup, depth):
    """depth 1 = /en/x.html, depth 2 = /en/product/x.html.
    Root-relative asset refs need one extra '../' per level below /en/ ... but
    because the KO source already carries the right depth for its own location,
    we only add ONE extra '../' (the /en/ level itself)."""
    for tag in soup.find_all(['a', 'img', 'link', 'script', 'source']):
        attr = 'href' if tag.name in ('a', 'link') else 'src'
        v = tag.get(attr)
        if not v or v.startswith(('http://', 'https://', '#', 'mailto:', 'tel:', 'data:', '/')):
            continue
        # asset paths only — page links stay relative and resolve inside /en/
        parts = v.split('/')
        stripped = v
        prefix = ''
        while stripped.startswith('../'):
            prefix += '../'
            stripped = stripped[3:]
        if stripped.startswith(ASSET_DIRS):
            tag[attr] = '../' + prefix + stripped

def lang_switch(ko_href, en_href, mobile=False):
    """HTML for the KO/EN switch."""
    if mobile:
        return (f'<div class="lang"><a href="{ko_href}">KO</a>'
                f'<span class="sep">/</span><span class="on">EN</span></div>')
    return (f'<div class="lang"><a href="{ko_href}">KO</a>'
            f'<span class="sep">/</span><span class="on">EN</span></div>')

def ko_lang_switch(en_href):
    return (f'<div class="lang"><span class="on">KO</span>'
            f'<span class="sep">/</span><a href="{en_href}">EN</a></div>')

def set_util(soup, inner_html):
    util = soup.select_one('.util')
    if util:
        util.clear()
        util.append(BeautifulSoup(inner_html, 'html.parser'))

def add_mobile_lang(soup, inner_html):
    mnav = soup.select_one('.mnav')
    if mnav:
        mnav.append(BeautifulSoup(inner_html, 'html.parser'))

def add_hreflang(soup, ko_url, en_url, self_url):
    head = soup.head
    for rel, hl, href in (('alternate', 'ko', ko_url),
                          ('alternate', 'en', en_url),
                          ('alternate', 'x-default', ko_url)):
        t = soup.new_tag('link', rel=rel, href=href)
        t['hreflang'] = hl
        head.append(t)
    c = soup.new_tag('link', rel='canonical', href=self_url)
    head.append(c)

# ---------- page build ----------
def build(src, depth):
    """src: KO source path relative to ROOT. depth: 1 or 2."""
    html = open(os.path.join(ROOT, src), encoding='utf-8').read()
    soup = BeautifulSoup(html, 'html.parser')

    # language attr
    soup.html['lang'] = 'en'

    # translate text nodes
    for node in soup.find_all(string=True):
        if node.parent.name in ('script', 'style'):
            continue
        s = str(node)
        if KO_RE.search(s):
            node.replace_with(NavigableString(tr(s, src)))
    # translate attributes
    for tag in soup.find_all(attrs={'content': True}):
        if KO_RE.search(tag['content']):
            tag['content'] = tr(tag['content'], src)
    for tag in soup.find_all(attrs={'alt': True}):
        if KO_RE.search(tag['alt']):
            tag['alt'] = tr(tag['alt'], src)
    for tag in soup.find_all(attrs={'aria-label': True}):
        if KO_RE.search(tag['aria-label']):
            tag['aria-label'] = tr(tag['aria-label'], src)
    if soup.title and KO_RE.search(soup.title.string or ''):
        soup.title.string = tr(soup.title.string, src)

    # product cards: KO name row now holds the English name -> drop the duplicate
    for nm_en in soup.select('.pcard .nm-en'):
        nm = nm_en.find_previous_sibling(class_='nm')
        if nm and nm.get_text(strip=True) == nm_en.get_text(strip=True):
            nm_en.decompose()

    fix_paths(soup, depth)

    # language switch + hreflang
    up = '../' * (depth - 1)
    ko_rel = ('../' * depth) + src            # from /en/[product/] back to KO
    set_util(soup, lang_switch(ko_rel, ''))
    add_mobile_lang(soup, lang_switch(ko_rel, '', mobile=True))
    add_hreflang(soup,
                 f'{SITE}/{src}',
                 f'{SITE}/en/{src}',
                 f'{SITE}/en/{src}')

    out = os.path.join(ROOT, 'en', src)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    open(out, 'w', encoding='utf-8').write(str(soup))
    return out

def patch_ko(src, depth):
    """Add the KO/EN switch + hreflang to the Korean page."""
    p = os.path.join(ROOT, src)
    soup = BeautifulSoup(open(p, encoding='utf-8').read(), 'html.parser')
    if soup.select_one('.util .lang'):
        pass  # already patched — rebuild anyway
    en_rel = ('../' * (depth - 1)) + 'en/' + src if depth == 1 else '../en/' + src
    set_util(soup, ko_lang_switch(en_rel))
    for old in soup.select('.mnav .lang'):
        old.decompose()
    add_mobile_lang(soup, (f'<div class="lang"><span class="on">KO</span>'
                           f'<span class="sep">/</span><a href="{en_rel}">EN</a></div>'))
    for l in soup.select('link[hreflang], link[rel=canonical]'):
        l.decompose()
    add_hreflang(soup, f'{SITE}/{src}', f'{SITE}/en/{src}', f'{SITE}/{src}')
    open(p, 'w', encoding='utf-8').write(str(soup))

if __name__ == '__main__':
    targets = sys.argv[1:] or ['index.html', 'brand.html', 'products.html',
                               'technology.html', 'b2b.html', 'privacy.html']
    for t in targets:
        depth = 2 if t.startswith('product/') else 1
        build(t, depth)
        patch_ko(t, depth)
        print('  built en/' + t)
    if MISSING:
        print(f'\n미번역 {len(MISSING)}건:')
        for k, v in list(MISSING.items())[:40]:
            print(f'  [{",".join(sorted(v))[:28]}] {k[:90]}')
    else:
        print('\n미번역 없음')
