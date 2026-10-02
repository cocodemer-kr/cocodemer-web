/* COCODEMER — language menu (17 languages). Shared by every language version. */
(function(){
  var CLOSE={"zh-Hans": "关闭", "zh-Hant": "關閉", "ja": "閉じる", "ar": "إغلاق", "de": "Schließen", "nl": "Sluiten", "cs": "Zavřít", "fr": "Fermer", "it": "Chiudi", "es": "Cerrar", "vi": "Đóng", "th": "ปิด", "id": "Tutup", "ms": "Tutup", "ru": "Закрыть", "en": "Close", "ko": "닫기"};
  var lang=document.documentElement.getAttribute('lang')||'ko';
  [].forEach.call(document.querySelectorAll('[data-lang-dd]'),function(dd){
    var b=dd.querySelector('.lang-btn'), l=dd.querySelector('.lang-list');
    if(!b||!l) return;
    function links(){return [].slice.call(l.querySelectorAll('a'));}
    function open(focus){l.hidden=false;b.setAttribute('aria-expanded','true');
      if(focus){var c=l.querySelector('a[aria-current]')||links()[0]; if(c) c.focus();}}
    function close(ret){l.hidden=true;b.setAttribute('aria-expanded','false'); if(ret) b.focus();}
    b.addEventListener('click',function(){ if(l.hidden) open(false); else close(false); });
    b.addEventListener('keydown',function(e){
      if(e.key==='ArrowDown'||e.key==='ArrowUp'){e.preventDefault();open(true);}
      else if(e.key==='Escape'&&!l.hidden){e.preventDefault();close(true);}
    });
    l.addEventListener('keydown',function(e){
      var a=links(), i=a.indexOf(document.activeElement);
      if(e.key==='Escape'){e.preventDefault();close(true);}
      else if(e.key==='ArrowDown'){e.preventDefault();a[(i+1)%a.length].focus();}
      else if(e.key==='ArrowUp'){e.preventDefault();a[(i-1+a.length)%a.length].focus();}
      else if(e.key==='Home'){e.preventDefault();a[0].focus();}
      else if(e.key==='End'){e.preventDefault();a[a.length-1].focus();}
    });
    document.addEventListener('click',function(e){ if(!l.hidden&&!dd.contains(e.target)) close(false); });
    dd.addEventListener('focusout',function(e){ if(!l.hidden&&e.relatedTarget&&!dd.contains(e.relatedTarget)) close(false); });
  });
  /* keep the open section (#hash) when switching language */
  [].forEach.call(document.querySelectorAll('a[data-lang-link]'),function(a){
    a.addEventListener('click',function(){ if(location.hash) a.setAttribute('href',a.getAttribute('href').split('#')[0]+location.hash); });
  });
  /* image viewer close button: name it in the page language */
  var lbl=CLOSE[lang];
  if(lbl&&lbl!=='닫기'){
    var fix=function(){[].forEach.call(document.querySelectorAll('button.x[aria-label="닫기"]'),function(x){x.setAttribute('aria-label',lbl);});};
    fix(); if(window.MutationObserver) new MutationObserver(fix).observe(document.body,{childList:true,subtree:true});
  }
})();
