document.addEventListener('DOMContentLoaded', function () {
  var $ = function (s, r) { return (r || document).querySelector(s); };
  var $$ = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };

  // Мобильное меню
  var burger = $('#burger'), nav = $('#nav');
  if (burger && nav) burger.addEventListener('click', function () { nav.classList.toggle('open'); });

  // Подтверждение опасных действий и автосохранение статусов в админке
  $$('form[data-confirm]').forEach(function (f) {
    f.addEventListener('submit', function (e) { if (!confirm(f.dataset.confirm)) { e.preventDefault(); e.stopImmediatePropagation(); } });
  });
  $$('select[data-autosubmit]').forEach(function (sel) {
    sel.addEventListener('change', function () { sel.form.submit(); });
  });

  // Закрытие уведомлений
  $$('.flash__close').forEach(function (b) {
    b.addEventListener('click', function () { b.closest('.flash').remove(); });
  });

  // Маска телефона
  $$('input[type="tel"]').forEach(function (input) {
    input.addEventListener('input', function () {
      var d = input.value.replace(/\D/g, '');
      if (!d) { input.value = ''; return; }
      if (d[0] === '8') d = '7' + d.slice(1);
      if (d[0] !== '7') d = '7' + d;
      d = d.slice(0, 11);
      var out = '+7';
      if (d.length > 1) out += ' (' + d.slice(1, 4);
      if (d.length >= 5) out += ') ' + d.slice(4, 7);
      if (d.length >= 8) out += '-' + d.slice(7, 9);
      if (d.length >= 10) out += '-' + d.slice(9, 11);
      input.value = out;
    });
  });

  // Защита от двойной отправки форм
  $$('form').forEach(function (form) {
    if (form.matches('[data-live], #credit-form, #tradein-form, .header__search, .js-fav, .js-compare')) return;
    form.addEventListener('submit', function (e) {
      if (!form.checkValidity()) { e.preventDefault(); form.reportValidity(); return; }
      var btn = $('button[type="submit"].btn--primary, button[type="submit"].btn--lg', form);
      if (!btn) return;
      var label = btn.textContent;
      btn.disabled = true; btn.textContent = 'Отправляем…';
      setTimeout(function () { btn.disabled = false; btn.textContent = label; }, 4000);
    });
  });

  var fmt = function (n) { return Math.round(n).toLocaleString('ru-RU') + '\u00a0₽'; };

  // Каталог: фильтры применяются сразу, страница не перезагружается
  var cform = $('#filters-form'), content = $('#catalog-content'), ctimer, creq = 0;
  function catalogUrl() {
    var p = new URLSearchParams();
    new FormData(cform).forEach(function (v, k) { if (v !== '' && v !== 'all') p.append(k, v); });
    var qs = p.toString();
    return cform.getAttribute('action') + (qs ? '?' + qs : '');
  }
  function loadCatalog(url, push) {
    var id = ++creq;
    content.style.opacity = '.45';
    fetch(url, { headers: { 'X-Requested-With': 'fetch' } }).then(function (r) { return r.text(); }).then(function (html) {
      if (id !== creq) return;
      var doc = new DOMParser().parseFromString(html, 'text/html');
      var fresh = doc.getElementById('catalog-content');
      if (fresh) content.innerHTML = fresh.innerHTML;
      var head = doc.querySelector('.page-head p'), mine = $('.page-head p');
      if (head && mine) mine.textContent = head.textContent;
      if (push && history.replaceState) history.replaceState(null, '', url);
    }).catch(function () { window.location = url; }).then(function () { content.style.opacity = ''; });
  }
  if (cform && content) {
    var apply = function (delay) { clearTimeout(ctimer); ctimer = setTimeout(function () { loadCatalog(catalogUrl(), true); }, delay); };
    cform.addEventListener('change', function () { apply(60); });
    cform.addEventListener('input', function (e) { if (e.target.matches('input[type=search],input[type=number]')) apply(400); });
    cform.addEventListener('submit', function (e) { e.preventDefault(); apply(0); });
    var range = $('#price-range'), out = $('#price-out'), maxInput = $('input[name="max_price"]');
    if (range) range.addEventListener('input', function () {
      out.textContent = fmt(range.value); if (maxInput) maxInput.value = range.value;
    });
    if (range) range.addEventListener('change', function () { apply(0); });
    var reset = $('.filters__actions a');
    if (reset) reset.addEventListener('click', function (e) {
      e.preventDefault(); cform.reset();
      $$('input[type=search],input[type=number]', cform).forEach(function (i) { i.value = ''; });
      $$('select', cform).forEach(function (s) { s.selectedIndex = 0; });
      $$('.facet--any input', cform).forEach(function (r) { r.checked = true; });
      if (range) { range.value = range.max; out.textContent = fmt(range.max); }
      apply(0);
    });
    // пагинация, сортировка и чипы внутри выдачи тоже без перезагрузки
    content.addEventListener('click', function (e) {
      var a = e.target.closest('a.pagination__btn, a.active-filters__item, a.active-filters__reset');
      if (!a || !a.getAttribute('href') || a.classList.contains('is-disabled')) return;
      e.preventDefault(); loadCatalog(a.getAttribute('href'), true);
      window.scrollTo({ top: content.offsetTop - 100, behavior: 'smooth' });
    });
    content.addEventListener('change', function (e) {
      if (e.target.id !== 'sort') return;
      var u = new URL(catalogUrl(), location.origin); u.searchParams.set('sort', e.target.value);
      loadCatalog(u.pathname + u.search, true);
    });
  }

  // Избранное и сравнение: без перезагрузки страницы
  document.addEventListener('submit', function (e) {
    var form = e.target.closest('form.js-fav, form.js-compare');
    if (!form) return;
    e.preventDefault(); e.stopImmediatePropagation();
    var isFav = form.classList.contains('js-fav');
    fetch(form.action, { method: 'POST', body: new FormData(form),
      headers: { 'X-Requested-With': 'fetch', 'X-CSRF-Token': window.CSRF } })
      .then(function (r) { return r.json(); }).then(function (d) {
        if (!d.ok) {
          toast(d.error || 'Не удалось выполнить действие');
          if (d.login) setTimeout(function () {
            window.location = '/login?next=' + encodeURIComponent(location.pathname + location.search);
          }, 1300);
          return;
        }
        var btn = form.querySelector('button');
        var on = isFav ? d.added : d.ids.indexOf(parseInt(form.dataset.id, 10)) > -1;
        btn.classList.toggle('is-active', on);
        var badge = $(isFav ? '#fav-count' : '#compare-count');
        if (badge) { badge.textContent = d.count; badge.hidden = !d.count; }
        toast(isFav ? (d.added ? 'Добавлено в избранное' : 'Удалено из избранного')
                    : (on ? 'Добавлено к сравнению' : 'Убрано из сравнения'));
        // на странице избранного убранная карточка исчезает сразу
        var grid = $('#fav-grid');
        if (isFav && !d.added && grid) {
          var card = form.closest('.card');
          if (card) card.remove();
          var sub = $('#fav-subtitle');
          if (sub) sub.textContent = 'Сохранено: ' + d.count;
          if (!grid.children.length) window.location.reload();
        }
      }).catch(function () { form.submit(); });
  }, true);

  function toast(text) {
    var t = document.createElement('div');
    t.className = 'toast'; t.textContent = text; t.setAttribute('role', 'status');
    document.body.appendChild(t);
    setTimeout(function () { t.classList.add('toast--hide'); }, 1800);
    setTimeout(function () { t.remove(); }, 2300);
  }

  // Trade-in: оценка пересчитывается сразу
  var tform = $('#tradein-form');
  if (tform) {
    var ttimer;
    var update = function () {
      var p = new URLSearchParams(new FormData(tform));
      fetch('/api/trade-in?' + p.toString()).then(function (r) { return r.json(); }).then(function (d) {
        $('#tradein-value').textContent = fmt(d.value);
        var g = $('#tradein-group'); if (g) g.textContent = { premium: 'премиум', mid: 'средний', main: 'массовый' }[d.group];
        var f = $('#tradein-find'); if (f) f.href = '/catalog?max_price=' + d.value;
      });
    };
    [['#year', '#year-out', function (v) { return v; }],
     ['#mileage', '#mileage-out', function (v) { return Number(v).toLocaleString('ru-RU') + ' км'; }]].forEach(function (x) {
      var el = $(x[0]); if (el) el.addEventListener('input', function () { $(x[1]).textContent = x[2](el.value); });
    });
    tform.addEventListener('input', function () { clearTimeout(ttimer); ttimer = setTimeout(update, 120); });
    tform.addEventListener('change', update);
    tform.addEventListener('submit', function (e) { e.preventDefault(); update(); });
  }

  // Подсказки поиска в шапке
  var search = $('#global-search'), box = $('#suggest'), timer;
  if (search && box) {
    search.addEventListener('input', function () {
      clearTimeout(timer);
      var q = search.value.trim();
      if (q.length < 2) { box.hidden = true; return; }
      timer = setTimeout(function () {
        fetch('/api/suggest?q=' + encodeURIComponent(q)).then(function (r) { return r.json(); }).then(function (d) {
          box.innerHTML = '';
          (d.items || []).slice(0, 6).forEach(function (it) {
            var a = document.createElement('a');
            a.href = it.url || ('/catalog?q=' + encodeURIComponent(it.title));
            a.textContent = it.title;
            box.appendChild(a);
          });
          box.hidden = !box.children.length;
        }).catch(function () { box.hidden = true; });
      }, 200);
    });
    search.addEventListener('keydown', function (e) {
      if (e.key === 'Enter' && search.value.trim()) { window.location = '/catalog?q=' + encodeURIComponent(search.value.trim()); }
      if (e.key === 'Escape') box.hidden = true;
    });
    document.addEventListener('click', function (e) { if (!e.target.closest('.header__search')) box.hidden = true; });
  }
});
