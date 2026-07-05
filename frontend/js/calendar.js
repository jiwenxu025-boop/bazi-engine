  let now = new Date();
  let yr = now.getFullYear();
  let mo = now.getMonth() + 1; // 0-indexed
  let months = ['1月','2月','3月','4月','5月','6月','7月','8月','9月','10月','11月','12月'];
  let weekdays = ['日','一','二','三','四','五','六'];

  let h = '<div class=section-title>择日</div>';
  h += '<div class=info-panel>';
  h += '<div class=calendar-section id=calendarSection>';
  h += '<div class=calendar-header>';
  h += '<button class=calendar-nav onclick="_calendarNav(-1)" title="上个月">◀</button>';
  h += '<span class=calendar-month id=calendarMonth>' + yr + '年' + months[mo-1] + '</span>';
  h += '<button class=calendar-nav onclick="_calendarNav(1)" title="下个月">▶</button>';
  h += '</div>';

  // 星期头
  h += '<div class=calendar-grid>';
  for (let w = 0; w < 7; w++) h += '<div class=calendar-day-header>' + weekdays[w] + '</div>';

  // 日期格子（初始占位）
  let firstDay = new Date(yr, mo-1, 1).getDay();
  let lastDate = new Date(yr, mo, 0).getDate();
  for (let i = 0; i < firstDay; i++) h += '<div class="calendar-day empty"></div>';
  for (let day = 1; day <= lastDate; day++){
    h += '<div class=calendar-day id=calDay' + day + '>' + day + '</div>';
  }
  h += '</div>';

  h += '<div class=calendar-legend>';
  h += '<span><span class="dot great"></span>大吉</span>';
  h += '<span><span class="dot good"></span>小吉</span>';
  h += '<span><span class="dot avoid"></span>小凶</span>';
  h += '<span><span class="dot bad"></span>大凶</span>';
  h += '</div>';

  h += '<div class=calendar-actions>';
  h += '<button class=calendar-export-btn onclick="_exportICS()">📅 导出日历</button>';
  h += '</div>';

  h += '</div></div>'; // /calendar-section + /info-panel

  // 存储当前年月，供翻页时使用
  window._calYear = yr;
  window._calMonth = mo;
  window._calChart = d;  // 保存命盘数据供 API 请求用

  // 异步加载当月吉凶标记
  setTimeout(function(){ _loadCalendarMarks(yr, mo); }, 100);

  return h;
}

function _calendarNav(dir){
  let m = window._calMonth + dir;
  let y = window._calYear;
  if (m > 12){ m = 1; y++; }
  if (m < 1){ m = 12; y--; }
  window._calYear = y;
  window._calMonth = m;

  let months = ['1月','2月','3月','4月','5月','6月','7月','8月','9月','10月','11月','12月'];
  document.getElementById('calendarMonth').textContent = y + '年' + months[m-1];

  // 重绘日期格子
  let grid = document.querySelector('.calendar-grid');
  let weekdays = ['日','一','二','三','四','五','六'];
  let firstDay = new Date(y, m-1, 1).getDay();
  let lastDate = new Date(y, m, 0).getDate();
  let cells = '';
  for (let w = 0; w < 7; w++) cells += '<div class=calendar-day-header>' + weekdays[w] + '</div>';
  for (let i = 0; i < firstDay; i++) cells += '<div class="calendar-day empty"></div>';
  for (let day = 1; day <= lastDate; day++){
    cells += '<div class=calendar-day id=calDay' + day + '>' + day + '</div>';
  }
  grid.innerHTML = cells;

  _loadCalendarMarks(y, m);
}

function _loadCalendarMarks(yr, mo){
  let api = document.getElementById('apiUrl').value.replace(/\/$/, '') || window.location.origin;
  let chartData = window._calChart;
  if (!chartData) return;

  fetch(api + '/api/date-pick', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({chart: chartData, year: yr, month: mo})
  }).then(function(r){ return r.json(); }).then(function(data){
    // 存储结果供导出用
    window._calResults = data.results || [];
    // 清除旧标记
    let allDays = document.querySelectorAll('.calendar-day:not(.empty)');
    for (let i = 0; i < allDays.length; i++){
      allDays[i].classList.remove('good','great','avoid','bad');
      allDays[i].title = '';
    }
    // v2: 按 score 分级标记
    (data.results || []).forEach(function(r){
      let d = new Date(r.date + 'T00:00:00').getDate();
      let el = document.getElementById('calDay' + d);
      if (!el) return;
      let tooltip = r.day_ganzhi;
      if (r.good_tags && r.good_tags.length) tooltip += ' | ' + r.good_tags.join(', ');
      if (r.bad_tags && r.bad_tags.length) tooltip += ' | ⚠ ' + r.bad_tags.join(', ');
      el.title = tooltip;
      if (r.score >= 3) el.classList.add('great');
      else if (r.score >= 1) el.classList.add('good');
      else if (r.score <= -3) el.classList.add('bad');
      else if (r.score <= -1) el.classList.add('avoid');
    });
  }).catch(function(){});
}

function _exportICS(){
  let yr = window._calYear;
  let mo = window._calMonth;
  let calResults = window._calResults;
  if (!calResults || !calResults.length){ alert('请等待择日数据加载完成'); return; }

  let goodOnes = calResults.filter(function(r){ return r.score >= 1; });
  if (!goodOnes.length){ alert('当前月份无吉日可导出'); return; }

  let lines = [
    'BEGIN:VCALENDAR',
    'VERSION:2.0',
    'PRODID:-//BaziEngine//择日吉期//CN',
    'CALSCALE:GREGORIAN',
    'METHOD:PUBLISH',
    'X-WR-CALNAME:择日吉期'
  ];

  let now = new Date().toISOString().replace(/[-:]/g,'').slice(0,15) + 'Z';

  for (let i = 0; i < goodOnes.length; i++){
    let r = goodOnes[i];
    let d = new Date(r.date + 'T00:00:00');
    let ds = d.getFullYear() +
      String(d.getMonth()+1).padStart(2,'0') +
      String(d.getDate()).padStart(2,'0');

    let desc = '八字择日系统筛选的吉日。\n评分: ' + r.score + '\n吉相: ' + (r.good_tags || []).join(', ') + '\n干支: ' + r.day_ganzhi;
    if (r.reasons && r.reasons.length) desc += '\n说明: ' + r.reasons.join('; ');

    lines.push('BEGIN:VEVENT');
    lines.push('UID:' + ds + '-bazi@zhaiji');
    lines.push('DTSTAMP:' + now);
    lines.push('DTSTART;VALUE=DATE:' + ds);
    lines.push('DTEND;VALUE=DATE:' + ds);
    lines.push('SUMMARY:宜：择日吉期 (' + r.day_ganzhi + ')');
    lines.push('DESCRIPTION:' + desc);
    lines.push('TRANSP:TRANSPARENT');
    lines.push('END:VEVENT');
  }

  lines.push('END:VCALENDAR');

  let blob = new Blob([lines.join('\r\n')], {type: 'text/calendar;charset=utf-8'});
  let url = URL.createObjectURL(blob);
  let a = document.createElement('a');
  a.href = url;
  a.download = '择日吉期_' + yr + '_' + mo + '.ics';
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

function md2html(t){
