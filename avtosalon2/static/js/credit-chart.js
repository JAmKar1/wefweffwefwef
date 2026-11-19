// Живой кредитный калькулятор: считает на лету, без перезагрузки страницы.
// Формула та же, что в logic.py (аннуитетный платёж).
(function () {
  var form = document.getElementById('credit-form');
  if (!form) return;
  var $ = function (id) { return document.getElementById(id); };
  var price = $('price'), down = $('down'), downRange = $('down-range'),
      years = $('years'), rate = $('rate');
  var fmt = function (n) { return Math.round(n).toLocaleString('ru-RU') + '\u00a0₽'; };

  function calc() {
    var p = Math.max(parseFloat(price.value) || 0, 0);
    var d = Math.min(Math.max(parseFloat(down.value) || 0, 0), p);
    var y = parseInt(years.value, 10) || 1;
    var r = Math.min(Math.max(parseFloat(String(rate.value).replace(',', '.')) || 0.1, 0.1), 40);
    var body = Math.max(p - d, 0), n = y * 12, mr = r / 100 / 12;
    var monthly = 0;
    if (body > 0) { var f = Math.pow(1 + mr, n); monthly = body * mr * f / (f - 1); }
    return { p: p, d: d, y: y, r: r, body: body, n: n, mr: mr, monthly: monthly,
             total: monthly * n, over: monthly * n - body };
  }

  function drawChart(c) {
    var el = $('chart');
    if (!el) return;
    if (c.body <= 0) { el.textContent = 'Кредит не нужен: взнос покрывает всю стоимость'; return; }
    var pts = [], bal = c.body;
    for (var m = 0; m <= c.n; m++) { pts.push(bal); bal = Math.max(bal - (c.monthly - bal * c.mr), 0); }
    var W = 560, H = 200, P = 10, step = (W - 2 * P) / c.n;
    var xy = pts.map(function (v, i) { return (P + i * step).toFixed(1) + ',' + (P + (1 - v / pts[0]) * (H - 2 * P)).toFixed(1); });
    el.innerHTML =
      '<svg viewBox="0 0 ' + W + ' ' + H + '" style="width:100%;height:auto" role="img" aria-label="Остаток долга по месяцам">' +
      '<polygon points="' + P + ',' + (H - P) + ' ' + xy.join(' ') + ' ' + (W - P) + ',' + (H - P) + '" fill="#d32a1e" fill-opacity=".14"/>' +
      '<polyline points="' + xy.join(' ') + '" fill="none" stroke="#d32a1e" stroke-width="2.5" stroke-linejoin="round"/></svg>' +
      '<div style="display:flex;justify-content:space-between;font-size:.8rem;color:#5e6872;margin-top:6px">' +
      '<span>Остаток долга: ' + fmt(pts[0]) + '</span><span>' + c.n + ' мес.</span><span>0\u00a0₽</span></div>';
  }

  function drawSchedule(c) {
    var body = $('schedule-body'), note = $('schedule-note');
    if (!body) return;
    var rows = '', bal = c.body, shown = Math.min(c.n, 60);
    for (var i = 1; i <= shown && c.body > 0; i++) {
      var int_ = bal * c.mr, pr = Math.min(c.monthly - int_, bal);
      bal = Math.max(bal - pr, 0);
      rows += '<tr><td>' + i + '</td><td>' + fmt(c.monthly) + '</td><td>' + fmt(int_) + '</td><td>' + fmt(pr) + '</td><td>' + fmt(bal) + '</td></tr>';
    }
    body.innerHTML = rows;
    if (note) note.textContent = c.n > shown ? 'Показаны первые ' + shown + ' из ' + c.n + ' платежей.' : '';
  }

  function render() {
    var c = calc();
    downRange.max = c.p;
    $('years-out').textContent = c.y + ' ' + (c.y === 1 ? 'год' : c.y < 5 ? 'года' : 'лет');
    $('down-out').textContent = fmt(c.d) + ' (' + (c.p ? Math.round(c.d / c.p * 100) : 0) + '%)';
    $('monthly').textContent = fmt(c.monthly);
    $('c-body').textContent = fmt(c.body);
    $('overpay').textContent = fmt(c.over);
    $('total').textContent = fmt(c.total);
    $('months').textContent = c.n + ' мес.';
    drawChart(c); drawSchedule(c);
    if (history.replaceState) {
      history.replaceState(null, '', '?price=' + Math.round(c.p) + '&down=' + Math.round(c.d) + '&years=' + c.y + '&rate=' + c.r);
    }
  }

  downRange.addEventListener('input', function () { down.value = downRange.value; render(); });
  [price, down, years, rate].forEach(function (el) {
    el.addEventListener('input', function () { if (el === down) downRange.value = down.value; render(); });
  });
  form.addEventListener('submit', function (e) { e.preventDefault(); render(); });
  render();
})();
