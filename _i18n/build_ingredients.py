#!/usr/bin/env python3
"""Build the INGREDIENTS page from the original active-ingredient copy.

The old site carried an ingredient reference under the custom-compounding
section: 45 actives, each with an introduction, a benefit list, a longer read
and a research citation. The compounding service is gone but the reference is
the most substantial technical content the brand has, so it comes back as a
page of its own — and the ACTIVE CODE letters on the product pages link into it.

The copy is the 2021 original, carried over as written. It describes the raw
materials, not any finished product, which is what the page's footnote says.

Source: 맞춤형 액티브 문안_최종-20210208.xlsx, parsed into _i18n/ingredients.json.
"""
import html
import json
import os
import re

from bs4 import BeautifulSoup

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, '_i18n', 'ingredients.json')

GROUP_ORDER = ['미백', '주름', '보습', '민감성', '베이스']
GROUP_EN = {
    '미백': 'Brightening', '주름': 'Wrinkle Care', '보습': 'Moisture',
    '민감성': 'Sensitive Skin', '베이스': 'Base',
}

COPY = {
    'ko': {
        'title': '원료 · INGREDIENTS · 코코드메르',
        'desc': '코코드메르가 처방에 사용하는 액티브 원료 45종. 코드별 원료 소개와 효능, '
                '연구 출처를 확인하실 수 있습니다.',
        'h1': 'INGREDIENTS',
        'sub': '액티브 원료 45종',
        'lead': '코코드메르는 피부 활성 성분을 코드로 분류합니다. 스킨 코드 세럼 16종과 '
                '완제품 라인의 ACTIVE CODE는 모두 아래 원료 체계에서 나옵니다. '
                '코드를 선택하시면 원료 소개와 효능을 보실 수 있습니다.',
        'all': '전체',
        'pick': '왼쪽에서 원료를 선택해 주십시오.',
        'intro_lb': '원료 소개',
        'benefit_lb': '효능',
        'deep_lb': '더 알아보기',
        'source_lb': '참고 문헌',
        'source_go': '원문 보기 ↗',
        'pending': '원료명 확인 중',
        'count': '종',
        'note': '※ 위 내용은 완제품이 아닌 원료에 관한 설명입니다. '
                '실제 제품의 배합 목적과 함량은 제품별 전성분 표기를 따릅니다.',
        'b2b': '원료·처방 문의',
        'lc_h3': '코코 드 메르에서 나온 <b>독자 원료</b>',
        'lc_lead': '코코드메르가 과거 맞춤형 라인업에서 개발한 독자 원료입니다. '
                   '세이셸에서만 자라는 코코 드 메르 씨앗에서 출발했습니다.',
        'lc_p1': '<b>코코넛수</b> — 천연 아미노산이 풍부한 코코 드 메르를 모방한 성분입니다.',
        'lc_p2': '<b>피토스테롤</b> — 식물이 상처를 스스로 치유하기 위해 생성되는 성분입니다.',
        'lc_p3': '<b>아미노산 20종 · 허니</b> — 탄탄한 피부 바탕을 만들어 줍니다.',
        'lc_p4': '<b>전달 기술</b> — 지질 멤브레인 연구와 난용성 물질의 가용화 기술을 결합했습니다.',
        'lc_note': '※ 지난 라인업 33종에 적용된 원료입니다. 해당 제품은 현재 판매되지 않으며, '
                   '처방 기록은 보관하고 있습니다.',
    },
    'en': {
        'title': 'Ingredients · COCODEMER',
        'desc': 'The 45 active ingredients behind COCODEMER formulations — what each '
                'one is, what it does, and the research behind it.',
        'h1': 'INGREDIENTS',
        'sub': '45 Actives',
        'lead': 'COCODEMER classifies skin actives as codes. The ACTIVE CODE on every '
                'product, and the 16 Skin Code Serums, are drawn from the system '
                'below. Select a code to read about the ingredient.',
        'all': 'All',
        'pick': 'Select an ingredient to read about it.',
        'intro_lb': 'About',
        'benefit_lb': 'Benefits',
        'deep_lb': 'In depth',
        'source_lb': 'Reference',
        'source_go': 'Read the paper ↗',
        'pending': 'Name to be confirmed',
        'count': '',
        'note': '* The descriptions above relate to the ingredients, not to any '
                'finished product. The purpose and level at which each is used is '
                "given in the individual product's ingredient declaration.",
        'b2b': 'Ingredient & formulation enquiry',
        'lc_h3': 'A proprietary material from the <b>coco de mer</b>',
        'lc_lead': 'A proprietary material COCODEMER developed during its bespoke years, '
                   'starting from the seed of the coco de mer — a palm that grows only '
                   'in the Seychelles.',
        'lc_p1': '<b>Coconut water</b> — modelled on the coco de mer, rich in natural amino acids.',
        'lc_p2': '<b>Phytosterol</b> — what a plant produces to heal its own wounds.',
        'lc_p3': '<b>20 amino acids · honey</b> — builds a firm base for the skin.',
        'lc_p4': '<b>Delivery</b> — lipid-membrane research combined with solubilisation '
                 'of poorly soluble compounds.',
        'lc_note': '* Used across the 33-piece archive. Those products are no longer sold; '
                   'the formulation records are kept.',
    },
}


def esc(s):
    return html.escape(s or '', quote=False)


def load():
    with open(DATA, encoding='utf-8') as fh:
        rows = json.load(fh)
    rows.sort(key=lambda r: (GROUP_ORDER.index(r['group']), r['id']))
    return rows


def card(row, lang):
    t = COPY[lang]
    name = row['name_ko'] if lang == 'ko' else (
        row.get('name_en') or row['inci'] or row['name_ko'])
    if row['pending_name']:
        name = t['pending']
    return (f'<button class="ing-card" data-code="{esc(row["id"])}" '
            f'data-group="{esc(row["group"])}" type="button">'
            f'<span class="hx">{esc(row["code"])}</span>'
            f'<span class="nm">{esc(name)}</span></button>')


def field(row, key, lang):
    return row.get(key if lang == 'ko' else key + '_en') or ''


def panel(row, lang):
    t = COPY[lang]
    name = row['name_ko'] if lang == 'ko' else (
        row.get('name_en') or row['inci'] or row['name_ko'])
    if row['pending_name']:
        name = t['pending']
    o = [f'<article class="ing-detail" data-code="{esc(row["id"])}" hidden>']
    o.append(f'<div class="ing-lb">{esc(GROUP_EN[row["group"]] if lang == "en" else row["group"])}'
             f' · {esc(row["code"])}</div>')
    o.append(f'<h2>{esc(name)}</h2>')
    if row['inci'] and lang == 'ko' and not row['pending_name']:
        o.append(f'<p class="ing-inci">{esc(row["inci"])}</p>')
    intro = field(row, 'intro', lang)
    benefits = row.get('benefits' if lang == 'ko' else 'benefits_en') or []
    deep = field(row, 'deep', lang)
    if intro:
        o.append(f'<div class="ing-lb2">{t["intro_lb"]}</div>'
                 f'<p>{esc(intro).replace(chr(10), "<br/>")}</p>')
    if benefits:
        o.append(f'<div class="ing-lb2">{t["benefit_lb"]}</div><ul>'
                 + ''.join(f'<li>{esc(b)}</li>' for b in benefits) + '</ul>')
    if deep:
        o.append(f'<div class="ing-lb2">{t["deep_lb"]}</div>'
                 f'<p>{esc(deep).replace(chr(10), "<br/>")}</p>')
    if row['source']:
        o.append(f'<div class="ing-lb2">{t["source_lb"]}</div>'
                 f'<p><a class="ing-src" href="{esc(row["source"])}" rel="noopener nofollow" '
                 f'target="_blank">{t["source_go"]}</a></p>')
    o.append('</article>')
    return ''.join(o)


def page_body(rows, lang):
    t = COPY[lang]
    groups = [g for g in GROUP_ORDER if any(r['group'] == g for r in rows)]
    tabs = [f'<button class="on" data-g="" type="button">{t["all"]}</button>']
    for g in groups:
        n = sum(1 for r in rows if r['group'] == g)
        label = GROUP_EN[g] if lang == 'en' else g
        tabs.append(f'<button data-g="{esc(g)}" type="button">{esc(label)} '
                    f'<span>{n}{t["count"]}</span></button>')

    o = [f'<div class="pagehead"><img alt="" src="img/hero-4-lab.jpg"/>'
         f'<div class="t"><h1>{t["h1"]}</h1><p>{esc(t["sub"])}</p></div></div>',
         # 독자 원료 — 현재 시스템의 기초로 오인되지 않도록 TECHNOLOGY가 아닌 이 페이지에 둔다
         '<section class="sys" style="padding-top:52px"><div class="wrap">',
         '<div class="sec-top"><div class="sec-en">L-CODEMAR ELIXIR&trade;</div>'
         f'<div class="rule"></div><h3>{t["lc_h3"]}</h3>'
         f'<p class="lead">{esc(t["lc_lead"])}</p></div>',
         '<div class="split wide">',
         '<div class="fig"><img alt="L-CODEMAR ELIXIR" loading="lazy" src="img/elixir.jpg"'
         ' style="object-fit:contain;background:#000"/></div>',
         '<div class="copy"><div class="en">FOUR PILLARS</div>',
         f'<p>{t["lc_p1"]}</p><p>{t["lc_p2"]}</p><p>{t["lc_p3"]}</p><p>{t["lc_p4"]}</p>',
         f'<p style="font-size:13px;color:var(--muted);margin-top:4px">{esc(t["lc_note"])}</p>',
         '</div></div></div></section>',
         '<section><div class="wrap">',
         f'<p class="ing-lead">{esc(t["lead"])}</p>',
         '<div class="ing-tabs">' + ''.join(tabs) + '</div>',
         '<div class="ing-layout">',
         '<div class="ing-grid">' + ''.join(card(r, lang) for r in rows) + '</div>',
         '<div class="ing-pane">',
         f'<p class="ing-empty">{esc(t["pick"])}</p>',
         ''.join(panel(r, lang) for r in rows),
         '</div></div>',
         f'<p class="ing-note">{esc(t["note"])}</p>',
         f'<p class="ing-cta"><a class="btn" href="b2b.html">{esc(t["b2b"])}</a></p>',
         '</div></section>']
    return ''.join(o)


SCRIPT = """
(function(){
  var grid=document.querySelector('.ing-grid');
  if(!grid) return;
  var pane=document.querySelector('.ing-pane');
  var empty=pane.querySelector('.ing-empty');
  var cards=[].slice.call(grid.querySelectorAll('.ing-card'));
  var panels=[].slice.call(pane.querySelectorAll('.ing-detail'));
  function show(code){
    var found=false;
    panels.forEach(function(p){
      var on=p.dataset.code===code;
      p.hidden=!on; if(on) found=true;
    });
    cards.forEach(function(c){ c.classList.toggle('on', c.dataset.code===code); });
    empty.hidden=found;
    if(found && window.matchMedia('(max-width:900px)').matches){
      pane.scrollIntoView({behavior:'smooth', block:'start'});
    }
  }
  grid.addEventListener('click', function(e){
    var b=e.target.closest('.ing-card'); if(!b) return;
    show(b.dataset.code);
    history.replaceState(null,'','#'+b.dataset.code);
  });
  document.querySelector('.ing-tabs').addEventListener('click', function(e){
    var b=e.target.closest('button'); if(!b) return;
    var g=b.dataset.g||'';
    [].forEach.call(this.querySelectorAll('button'),function(x){x.classList.toggle('on',x===b);});
    cards.forEach(function(c){ c.hidden = !!g && c.dataset.group!==g; });
  });
  function fromHash(){
    var h=decodeURIComponent(location.hash.replace('#',''));
    if(h) show(h);
  }
  // also handle arriving from another link on the same page
  window.addEventListener('hashchange', fromHash);
  fromHash();
})();
"""


def render(lang, out_path, depth=0):
    """Build the page for one language.

    The English page is built from the English shell so the navigation, footer
    and language switch come out right; asset paths then need the extra '../'
    that every /en/ page carries.
    """
    rows = load()
    base = os.path.join(ROOT, 'en', 'technology.html') if lang == 'en' \
        else os.path.join(ROOT, 'technology.html')
    soup = BeautifulSoup(open(base, encoding='utf-8').read(), 'html.parser')
    t = COPY[lang]

    soup.title.string = t['title']
    for tag in soup.find_all('meta'):
        if tag.get('name') == 'description' or tag.get('property') == 'og:description':
            tag['content'] = t['desc']
        if tag.get('property') == 'og:title':
            tag['content'] = t['title']
    for l in soup.select('link[hreflang], link[rel=canonical]'):
        l.decompose()

    main = soup.find('main')
    main.clear()
    body = page_body(rows, lang)
    if lang == 'en':
        body = body.replace('src="img/', 'src="../img/')
    main.append(BeautifulSoup(body, 'html.parser'))

    for a in soup.select('.gnb a, .mnav a'):
        classes = [c for c in a.get('class', []) if c != 'cur']
        if (a.get('href') or '').endswith('ingredients.html'):
            classes.append('cur')
        a['class'] = classes

    site = 'https://www.cocodemer.co.kr'
    switch = ('<div class="lang"><span class="on">KO</span><span class="sep">/</span>'
              '<a href="en/ingredients.html">EN</a></div>') if lang == 'ko' else (
             '<div class="lang"><a href="../ingredients.html">KO</a>'
             '<span class="sep">/</span><span class="on">EN</span></div>')
    util = soup.select_one('.util')
    if util:
        util.clear()
        util.append(BeautifulSoup(switch, 'html.parser'))
    for old in soup.select('.mnav .lang'):
        old.decompose()
    mnav = soup.select_one('.mnav')
    if mnav:
        mnav.append(BeautifulSoup(switch, 'html.parser'))
    head = soup.head
    for rel, hl, href in (('alternate', 'ko', f'{site}/ingredients.html'),
                          ('alternate', 'en', f'{site}/en/ingredients.html'),
                          ('alternate', 'x-default', f'{site}/ingredients.html')):
        link = soup.new_tag('link', rel=rel, href=href)
        link['hreflang'] = hl
        head.append(link)
    self_url = f'{site}/ingredients.html' if lang == 'ko' else f'{site}/en/ingredients.html'
    head.append(soup.new_tag('link', rel='canonical', href=self_url))

    tag = soup.new_tag('script')
    tag.string = SCRIPT
    soup.body.append(tag)

    open(out_path, 'w', encoding='utf-8').write(str(soup))
    return out_path


if __name__ == '__main__':
    print(' built', render('ko', os.path.join(ROOT, 'ingredients.html')))
    os.makedirs(os.path.join(ROOT, 'en'), exist_ok=True)
    print(' built', render('en', os.path.join(ROOT, 'en', 'ingredients.html')))
