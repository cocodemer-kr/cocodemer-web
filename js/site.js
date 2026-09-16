// 모바일 메뉴
(function(){
  var b=document.querySelector('.burger'), m=document.querySelector('.mnav');
  if(!b||!m) return;
  b.addEventListener('click',function(){
    var on=m.classList.toggle('on');
    b.setAttribute('aria-expanded',on?'true':'false');
  });
})();

// 히어로 슬라이더
(function(){
  var sl=document.querySelectorAll('.hero .slides img'), dt=document.querySelectorAll('.hero .dots button'), i=0, timer;
  if(sl.length<2) return;
  var cap=document.getElementById('heroCap');
  var hc=document.querySelectorAll('.hero .hcap');
  function go(n){ i=n; sl.forEach(function(x,k){x.classList.toggle('on',k===n)}); dt.forEach(function(x,k){x.classList.toggle('on',k===n)});
    hc.forEach(function(x,k){x.classList.toggle('on',k===n)});
    if(cap){ var t=sl[n].getAttribute('data-cap'); if(t){ cap.style.opacity=0; setTimeout(function(){ cap.textContent=t; cap.style.opacity=1; },300); } } }
  function next(){ go((i+1)%sl.length); }
  dt.forEach(function(btn){ btn.addEventListener('click',function(){ go(+btn.dataset.i); clearInterval(timer); timer=setInterval(next,6000); }); });
  if(!window.matchMedia('(prefers-reduced-motion: reduce)').matches) timer=setInterval(next,6000);
})();

// 브랜드 필름
document.querySelectorAll('.film .frame').forEach(function(f){
  f.addEventListener('click',function(){
    var v=f.dataset.video; if(!v) return;
    var ifr=document.createElement('iframe');
    ifr.src=v+'?autoplay=1&rel=0';
    ifr.setAttribute('allow','autoplay; encrypted-media');
    ifr.setAttribute('allowfullscreen','');
    ifr.setAttribute('title','COCODEMER Brand Film');
    f.innerHTML=''; f.appendChild(ifr);
  });
});

// 제품 상세 탭
document.querySelectorAll('.tabs2 button').forEach(function(b){
  b.addEventListener('click',function(){
    document.querySelectorAll('.tabs2 button').forEach(function(x){x.classList.remove('on')});
    b.classList.add('on');
    document.querySelectorAll('.pane').forEach(function(p){p.classList.remove('on')});
    var t=document.getElementById(b.dataset.p); if(t) t.classList.add('on');
  });
});

// 제품 목록 필터
(function(){
  var btns=document.querySelectorAll('.filters button'), cards=document.querySelectorAll('#grid .pcard'), cnt=document.getElementById('cnt');
  if(!btns.length||!cards.length) return;
  function apply(f){
    var n=0;
    cards.forEach(function(c){
      var show = (f==='all' || c.dataset.cat===f);
      c.style.display = show?'':'none';
      if(show) n++;
    });
    if(cnt) cnt.textContent='Total '+n;
  }
  btns.forEach(function(b){
    b.addEventListener('click',function(){
      btns.forEach(function(x){x.classList.remove('on')});
      b.classList.add('on');
      apply(b.dataset.f);
      history.replaceState(null,'', b.dataset.f==='all' ? location.pathname : location.pathname+'#'+b.dataset.f);
    });
  });
  var h=location.hash.replace('#','');
  if(h){ var m=document.querySelector('.filters button[data-f="'+h+'"]'); if(m) m.click(); }
})();

/* 제품 상세 이미지 갤러리 — 썸네일(누끼·패키지·제형)을 눌러 메인 이미지를 바꾼다 */
(function(){
  var thumbs = document.querySelector('.pd .gal-thumbs');
  if (!thumbs) return;
  var main = document.querySelector('.pd .gal-main img');
  thumbs.addEventListener('click', function(e){
    var b = e.target.closest('button');
    if (!b || !main) return;
    main.src = b.dataset.src;
    [].forEach.call(thumbs.querySelectorAll('button'), function(x){
      x.classList.toggle('on', x === b);
    });
  });
})();

/* 라인 탭 — PRODUCT / BRAND / B2B 공통 */
(function(){
  var tabs = [].slice.call(document.querySelectorAll('.ltabs button[data-lp]'));
  if (!tabs.length) return;
  var PANES = tabs.map(function(b){ return b.dataset.lp; });
  var FILTERS = ['all','cleansing','mask','basic','special','body','sun','serum'];
  var FIRST = PANES[0];
  function open(name, push){
    if (PANES.indexOf(name) < 0) return false;
    tabs.forEach(function(b){ b.classList.toggle('on', b.dataset.lp === name); });
    [].forEach.call(document.querySelectorAll('.lpane'), function(p){
      p.classList.toggle('on', p.id === 'lp-' + name);
    });
    if (push) history.replaceState(null, '', location.pathname + (name === FIRST ? '' : '#' + name));
    return true;
  }
  tabs.forEach(function(b){
    b.addEventListener('click', function(){
      open(b.dataset.lp, true);
      window.scrollTo({top:0, behavior:'smooth'});
    });
  });
  // 패널 안의 "다른 탭으로" 버튼
  [].forEach.call(document.querySelectorAll('[data-goto]'), function(b){
    b.addEventListener('click', function(){
      open(b.dataset.goto, true);
      window.scrollTo({top:0, behavior:'smooth'});
    });
  });
  function fromHash(){
    var k = location.hash.replace('#','');
    if (!k) return;
    if (open(k, false)) return;
    if (FILTERS.indexOf(k) >= 0 && PANES.indexOf('archive') >= 0) {
      open('archive', false);
      var fb = document.querySelector('.filters button[data-f="' + k + '"]');
      if (fb && !fb.classList.contains('on')) fb.click();
    }
  }
  fromHash();
  window.addEventListener('hashchange', fromHash);
})();
