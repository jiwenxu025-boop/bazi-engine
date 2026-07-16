'use strict';
/* HTML 转义：防止用户输入中的 <>&'" 破坏页面结构 */
function esc(s){ return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;'); }

/* ==========================================
   Theme
   ========================================== */
(function(){
  let saved = localStorage.getItem('bazi-theme');
  let prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
  let theme = saved || (prefersDark ? 'dark' : 'light');
  if (theme === 'dark') document.documentElement.classList.add('dark');
  updateToggle();
})();

function toggleLifeStage(currentStage, direction){
  // 始终允许所有阶段切换，用户最了解自己的实际情况
  let allStages = ['中学','大学','深造','职场','晚年'];
  let curIdx = allStages.indexOf(currentStage);
  if (curIdx < 0) curIdx = 2;

  let newIdx = curIdx + direction;
  if (newIdx >= allStages.length) newIdx = 0;
  if (newIdx < 0) newIdx = allStages.length - 1;

  sessionStorage.setItem('bazi-life-stage', allStages[newIdx]);
  go();
}

function toggleTheme(){
  let html = document.documentElement;
  html.classList.toggle('dark');
  localStorage.setItem('bazi-theme', html.classList.contains('dark') ? 'dark' : 'light');
  updateToggle();
}

function updateToggle(){
  let btn = document.getElementById('themeToggle');
  let isDark = document.documentElement.classList.contains('dark');
  btn.textContent = isDark ? '☾' : '☀';
  btn.title = isDark ? '切换浅色模式' : '切换深色模式';
}

document.getElementById('themeToggle').addEventListener('click', toggleTheme);

/* ==========================================
   API URL auto-set
   ========================================== */
(function(){
  let el = document.getElementById('apiUrl');
  if (!el.value) el.value = window.location.origin;
})();

/* ==========================================
   Form: Enter to submit
   ========================================== */
document.getElementById('formCard').addEventListener('keydown', function(e){
  if (e.key === 'Enter') {
    e.preventDefault();
    go();
  }
});

/* ==========================================
   Submit
   ========================================== */
document.getElementById('submitBtn').addEventListener('click', go);

/* ==========================================
   Shared app state
   ========================================== */
let AppState = {
  chart: null,
  currentContext: null,
  streamStatus: 'idle',
  lifeStageOverride: null,
};

function setChartData(chart){
  AppState.chart = chart || null;
  AppState.currentContext = AppState.chart && AppState.chart.current_context ? AppState.chart.current_context : null;
  try { CHAT.chartData = AppState.chart; } catch(e) {}
  if (typeof window !== 'undefined') window._calChart = AppState.chart;
  return AppState.chart;
}

function getChartData(){
  if (AppState.chart) return AppState.chart;
  try { return CHAT.chartData || null; } catch(e) { return null; }
}

function getCurrentContext(){
  if (AppState.currentContext) return AppState.currentContext;
  let chart = getChartData();
  return chart && chart.current_context ? chart.current_context : null;
}

function setStreamStatus(status){
  AppState.streamStatus = status || 'idle';
  return AppState.streamStatus;
}

function mergeAnnualSignals(year, signals){
  let chart = getChartData();
  if (!chart || !chart.annual_scans || !signals || !signals.length) return chart;
  for (let si = 0; si < chart.annual_scans.length; si++){
    if (chart.annual_scans[si].year === year){
      if (!chart.annual_scans[si].events) chart.annual_scans[si].events = [];
      for (let sj = 0; sj < signals.length; sj++){
        chart.annual_scans[si].events.push(signals[sj]);
      }
      break;
    }
  }
  setChartData(chart);
  return chart;
}

function setDayunInterpretations(items){
  let chart = getChartData();
  if (!chart) return null;
  if (!chart.dayun) chart.dayun = {};
  chart.dayun.interpretations = items || [];
  setChartData(chart);
  return chart;
}

function _buildChatFactHint(){
  let ctx = getCurrentContext() || {};
  let parts = [];
  if (ctx.current_dayun && ctx.current_dayun.ganzhi){
    let ageRange = ctx.current_dayun.age_range ? '（' + ctx.current_dayun.age_range + '）' : '';
    parts.push(ctx.current_dayun.ganzhi + '大运' + ageRange);
  }
  if (ctx.current_liunian && ctx.current_liunian.year && ctx.current_liunian.ganzhi){
    parts.push(ctx.current_liunian.year + '年' + ctx.current_liunian.ganzhi + '流年');
  }
  if (ctx.solar_age !== undefined && ctx.solar_age !== null) parts.push('周岁' + ctx.solar_age);
  if (ctx.liunian_age !== undefined && ctx.liunian_age !== null) parts.push('流年' + ctx.liunian_age);
  return parts.join(' · ');
}

function _buildChartParams(){
  let lnFrom = document.getElementById('lnFrom').value;
  let lnTo = document.getElementById('lnTo').value;
  if (!lnFrom && !lnTo){
    let currentYear = new Date().getFullYear();
    lnFrom = String(currentYear);
    lnTo = String(currentYear + 5);
  } else if (lnFrom && !lnTo){
    lnTo = lnFrom;
  } else if (!lnFrom && lnTo){
    lnFrom = lnTo;
  }
  let params = new URLSearchParams({
    name: document.getElementById('name').value || '未知',
    gender: document.getElementById('gender').value,
    year: document.getElementById('year').value,
    month: document.getElementById('month').value,
    day: document.getElementById('day').value,
    hour: document.getElementById('hour').value || '12',
    hour_confirmed: document.getElementById('hourConfirmed').checked,
    practical: true,  // 公网只显示白话解读，不暴露技术推导
  });
  if (lnFrom) params.set('liunian_from', lnFrom);
  if (lnTo) params.set('liunian_to', lnTo);
  let fl = document.getElementById('familyLevel').value;
  if (fl) params.set('family_level', fl);
  let fj = document.getElementById('fatherJob').value.trim();
  if (fj) params.set('father_job', fj);
  let mj = document.getElementById('motherJob').value.trim();
  if (mj) params.set('mother_job', mj);
  let lsOverride = sessionStorage.getItem('bazi-life-stage');
  if (lsOverride) params.set('life_stage', lsOverride);
  return params;
}

async function go(){
  let btn = document.getElementById('submitBtn');
  btn.disabled = true; btn.textContent = '计算中...';
  let r = document.getElementById('result');
  r.className = 'result visible';
  r.innerHTML = '<div class=loading-state><div class=spinner></div><div>计算中&#x2026;</div></div>';
  document.getElementById('copyBtn').style.display = 'none';
  document.getElementById('reportActions').classList.remove('active');

  let api = document.getElementById('apiUrl').value.replace(/\/$/, '');
  let params = _buildChartParams();

  try {
    // v0.11.2: 流式排盘——规则引擎立即渲染，LLM结果流式追加
    let streamUrl = api + '/api/chart/stream?' + params;
    let resp = await fetch(streamUrl);
    if (!resp.ok) throw new Error('API ' + resp.status);

    let streamReader = resp.body.getReader();
    let decoder = new TextDecoder();
    let buf = '';
    let d = null;           // 完整命盘数据
    let personalityEl = null;
    let personalityText = '';
    let llmTokens = {};  // v0.11.2: {year: accumulated_text}

    while(true){
      let chunk = await streamReader.read();
      if (chunk.done) break;
      buf += decoder.decode(chunk.value, {stream:true});
      let lines = buf.split('\n');
      buf = lines.pop() || '';
      for (let i = 0; i < lines.length; i++){
        let line = lines[i].trim();
        if (!line.startsWith('data: ')) continue;
        let payload = line.slice(6);
        if (payload === '[DONE]'){ buf = ''; break; }
        try {
          let msg = JSON.parse(payload);
          if (msg.phase === 'started'){
            // 连接已建立，更新加载提示
            r.innerHTML = '<div class=loading-state><div class=spinner></div><div>规则引擎计算中...</div></div>';
          } else if (msg.phase === 'llm_token'){
            // LLM推理逐token——某年的推理文字流式追加
            if (!llmTokens[msg.year]) llmTokens[msg.year] = '';
            llmTokens[msg.year] += msg.token;
            updateLlmTokenDisplay(msg.year, llmTokens[msg.year]);
          } else if (msg.phase === 'rules_done'){
            // 1. 规则引擎完成，立即渲染
            d = setChartData(msg.chart);
            render(d);
            setTimeout(function(){
              r.scrollIntoView({behavior: 'smooth', block: 'start'});
            }, 80);
          } else if (msg.phase === 'llm_result'){
            // 2. LLM审查某年完成，合并信号到对应年份
            if (d && d.annual_scans){
              d = mergeAnnualSignals(msg.year, msg.signals) || d;
              // 局部刷新流年区域
              refreshFlowSection(d);
            }
          } else if (msg.phase === 'personality_token'){
            // 3. 性格报告逐token → 渐进markdown渲染
            if (!personalityEl){
              personalityEl = document.querySelector('.personality-text');
              if (personalityEl) personalityEl.innerHTML = '';
            }
            if (personalityEl){
              personalityText += msg.token;
              // 防抖：每80ms渲染一次，避免逐token刷DOM
              clearTimeout(personalityEl._debounce);
              personalityEl._debounce = setTimeout(function(){
                let html = md2html(personalityText);
                // 增量：只更新最后一段，避免全量 re-parse
                let cursor = document.querySelector('.fusion-cursor');
                if (cursor) cursor.remove();
                personalityEl.innerHTML = html;
                personalityEl.insertAdjacentHTML('beforeend', '<span class=fusion-cursor>|</span>');
                personalityEl.scrollTop = personalityEl.scrollHeight;
              }, 16);  // 16ms ≈ 60fps，而非 80ms
            }
          } else if (msg.phase === 'fusion_status'){
            // 诊断：融合引擎状态
            console.log('[bazi] fusion_status:', msg.message);
          } else if (msg.phase === 'personality_done'){
            // 4. 性格报告完成——最终渲染
            if (personalityEl){
              clearTimeout(personalityEl._debounce);
              let finalText = msg.full || personalityText;
              personalityEl.innerHTML = md2html(finalText);
              showFusionFeedback(finalText, msg.meta || {});
            }
          } else if (msg.phase === 'personality_error'){
            // 4b. 性格融合失败——仅融合模式才覆盖文本
            if (!(d && d.personality && d.personality._fusion_ready)) continue;
            if (!personalityEl){
              personalityEl = document.querySelector('.personality-text');
            }
            showPersonalityRawFallback(msg.message || 'fusion error');
            continue;
          } else if (msg.phase === 'dayun_done'){
            // 5. 大运解读完成——更新DOM
            if (msg.interpretations && msg.interpretations.length){
              d = setDayunInterpretations(msg.interpretations) || d;
              let dyEls = document.querySelectorAll('.dayun-interpretations');
              for (let di = 0; di < dyEls.length; di++) dyEls[di].innerHTML = _buildDayunInterpretations(d);
            }
          } else if (msg.phase === 'dayun_error'){
            // 5b. 大运解读失败——显示原因
            let dyEls2 = document.querySelectorAll('.dayun-interpretations');
            for (let de = 0; de < dyEls2.length; de++) dyEls2[de].innerHTML = '<div class=dayun-error>⚠ 大运解读暂不可用：' + (msg.message || '未知错误') + '</div>';
          } else if (msg.phase === 'done'){
            // 6. 全流程结束——清理LLM推理实时显示区
            let liveEl = document.querySelector('.llm-live-section');
            if (liveEl) liveEl.remove();
          }
        } catch(e){}
      }
    }
  } catch(e) {
    r.innerHTML = '<div class=error-state>请求失败: ' + e.message + '<br><small style="color:' + (document.documentElement.classList.contains('dark') ? '#a0a0b0' : '#78716c') + '">请确认 API 地址可访问</small></div>';
  }
  btn.disabled = false; btn.textContent = '生成解读';
}

/* ==========================================
   Term definitions
   ========================================== */
let TERMS = {
  '纳音': '干支组合的五行音律属性，用于判断命局气韵',
  '藏干': '地支中潜藏的天干，反映暗藏的能量与人事',
  '十神': '日干与其他天干的生克关系定位',
  '日主': '出生日的天干，代表命主本人，是命盘核心',
  '格局': '基于月令透干取格的八字结构整体分类',
  '大运': '十年一换的运势阶段，由月柱顺逆推导',
  '命宫': '命盘十二宫的起点，主一生运势基调',
  '身宫': '表征命主安身立命之所',
  '胎元': '母体受胎之月，表征先天禀赋',
};

/* ==========================================
   Personality helpers
   ========================================== */
function _buildBingyaoCard(combos){
  let top = combos[0];
  let h = '<div class=bingyao-card>';
  h += '<div class=bingyao-badge>全局矛盾</div>';
  h += '<div class=bingyao-title>' + esc(top.combo) + '</div>';
  h += '<div class=bingyao-directive>' + esc(top.directive) + '</div>';
  if (combos.length > 1){
    h += '<div class=bingyao-secondary>';
    for (let i = 1; i < Math.min(combos.length, 3); i++){
      h += '<span>' + esc(combos[i].combo) + '</span>';
    }
    h += '</div>';
  }
  h += '</div>';
  return h;
}

function _buildShishenRank(scores){
  let entries = [];
  for (let k in scores) entries.push({name: k, val: scores[k]});
  entries.sort(function(a,b){return b.val - a.val;});
  let top5 = entries.slice(0, 5);
  let maxVal = top5[0] ? top5[0].val : 10;
  let h = '<div class=shishen-rank>';
  h += '<div class=shishen-rank-title>十神强度</div>';
  for (let i = 0; i < top5.length; i++){
    let pct = Math.round(top5[i].val / maxVal * 100);
    h += '<div class=shishen-bar><span class=shishen-name>' + top5[i].name + '</span>';
    h += '<span class=shishen-val>' + top5[i].val.toFixed(1) + '</span>';
    h += '<span class=shishen-fill style=width:' + pct + '%></span></div>';
  }
  h += '</div>';
  return h;
}

function setPersonalityMode(mode){
  let body = document.getElementById('personalityBody');
  let raw = document.getElementById('personalityRaw');
  let btn = document.querySelector('.toggle-btn');
  if (!body || !raw) return;
  if (mode === 'raw'){
    raw.style.display = 'block';
    body.style.display = 'none';
    if (btn){
      btn.dataset.personalityMode = 'raw';
      btn.textContent = '\u8fd4\u56deAI\u878d\u5408\u62a5\u544a';
    }
  } else {
    raw.style.display = 'none';
    body.style.display = 'block';
    if (btn){
      btn.dataset.personalityMode = 'fusion';
      btn.textContent = '\u67e5\u770b\u539f\u59cb\u6570\u636e';
    }
  }
}

function showPersonalityRawFallback(message){
  let body = document.getElementById('personalityBody');
  if (body && message) body.dataset.fusionError = message;
  setPersonalityMode('raw');
}

function togglePersonalityMode(){
  let rawForMode = document.getElementById('personalityRaw');
  let btnForMode = document.querySelector('.toggle-btn');
  let currentMode = btnForMode && btnForMode.dataset.personalityMode;
  let isRaw = currentMode ? currentMode === 'raw' : rawForMode && rawForMode.style.display !== 'none';
  setPersonalityMode(isRaw ? 'fusion' : 'raw');
}

function _buildReportOverview(d){
  let dayMaster = d.day_master ? (d.day_master.stem || '') + (d.day_master.wuxing || '') : '';
  let strength = d.yongshen && d.yongshen.strength ? d.yongshen.strength : '待判断';
  let favorable = d.yongshen && d.yongshen.favorable_wuxing ? d.yongshen.favorable_wuxing.join('、') : '待判断';
  let stage = d.life_stage || '未标记';
  let pattern = d.pattern || '待判断';
  let focusMap = {};
  if (d.annual_scans && d.annual_scans.length){
    for (let i = 0; i < d.annual_scans.length; i++){
      let events = d.annual_scans[i].events || [];
      for (let j = 0; j < events.length; j++){
        if (events[j].strength >= 2 && events[j].category){
          focusMap[events[j].category] = (focusMap[events[j].category] || 0) + events[j].strength;
        }
      }
    }
  }
  let focus = Object.keys(focusMap).sort(function(a,b){return focusMap[b] - focusMap[a];}).slice(0, 3);
  let focusText = focus.length ? focus.join('、') : '暂无明显高强度流年信号';
  let headline = dayMaster ? dayMaster + '日主，' + pattern + '，' + strength : pattern + '，' + strength;

  let h = '<section class=report-overview>';
  h += '<div class=report-overview-copy>';
  h += '<div class=report-eyebrow>命盘总览</div>';
  h += '<div class=report-headline>' + esc(headline) + '</div>';
  h += '<div class=report-subline>先看结论，再看依据。下面的四柱、流年和规则细节用于解释这些判断从哪里来。</div>';
  h += '</div>';
  h += '<div class=overview-grid>';
  h += '<div class=overview-item><span>日主</span><b>' + esc(dayMaster || '待判断') + '</b></div>';
  h += '<div class=overview-item><span>格局</span><b>' + esc(pattern) + '</b></div>';
  h += '<div class=overview-item><span>强弱</span><b>' + esc(strength) + '</b></div>';
  h += '<div class=overview-item><span>当前阶段</span><b>' + esc(stage) + '</b></div>';
  h += '<div class=overview-item><span>喜用</span><b>' + esc(favorable) + '</b></div>';
  h += '<div class=overview-item><span>近期重点</span><b>' + esc(focusText) + '</b></div>';
  h += '</div>';
  h += '</section>';
  return h;
}

function _getStageInfo(d){
  let stage = sessionStorage.getItem('bazi-life-stage') || d.life_stage || '未标记';
  let labels = {中学:'中学时期',大学:'大学时期',深造:'深造时期',职场:'职场时期',晚年:'晚年时期'};
  let isStudent = stage === '中学' || stage === '大学' || stage === '深造';
  return {
    value: stage,
    label: labels[stage] || stage,
    isStudent: isStudent
  };
}

function _summarizeAnnualScan(scan, d){
  if (!scan || !scan.events) return ['运势平稳'];
  let significant = scan.events.filter(function(e){return e.strength >= 2});
  let cats = significant.map(function(e){return e.category});
  let dirs = significant.map(function(e){return e.direction});
  let stageInfo = _getStageInfo(d || {});
  let summary = [];
  if (cats.indexOf('桃花') !== -1) summary.push(dirs[cats.indexOf('桃花')] === '负面' ? '感情波动' : '感情运升');
  if (cats.indexOf('事业') !== -1) summary.push(dirs[cats.indexOf('事业')] === '负面' ? (stageInfo.isStudent ? '学业压力' : '事业有压') : (stageInfo.isStudent ? '校园活跃' : '事业有进'));
  if (cats.indexOf('学业') !== -1) summary.push(dirs[cats.indexOf('学业')] === '负面' ? '学业压力' : '校园活跃');
  if (cats.indexOf('财运') !== -1) summary.push(dirs[cats.indexOf('财运')] === '负面' ? (stageInfo.isStudent ? '手头偏紧' : '注意财务') : (stageInfo.isStudent ? '经济宽松' : '财运关注'));
  if (cats.indexOf('健康') !== -1) summary.push('留意健康');
  if (cats.indexOf('升学') !== -1) summary.push(stageInfo.isStudent ? '学业运佳' : '进修运佳');
  if (cats.indexOf('进修') !== -1) summary.push('进修运佳');
  if (cats.indexOf('搬迁') !== -1) summary.push('可能搬迁');
  if (cats.indexOf('状态') !== -1) summary.push(dirs[cats.indexOf('状态')] === '负面' ? '状态低迷' : '状态良好');
  if (cats.indexOf('人际') !== -1) summary.push(dirs[cats.indexOf('人际')] === '负面' ? '人际有摩擦' : '人际和谐');
  if (!summary.length) summary.push('运势平稳');
  return summary;
}

function _formatAgeText(age){
  let text = String(age || '').trim();
  if (!text) return '';
  return text.indexOf('岁') === -1 ? text + '岁' : text;
}

function _getCurrentContext(d){
  return d && d.current_context ? d.current_context : {};
}

function _getCurrentScan(d){
  let ctx = _getCurrentContext(d);
  if (ctx.current_liunian){
    return {
      year: ctx.current_liunian.year,
      age: ctx.current_liunian.age,
      liunian: ctx.current_liunian.ganzhi,
      dayun: ctx.current_liunian.dayun,
      events: (ctx.current_liunian.key_events || []).map(function(e){
        return {
          category: e.category,
          direction: e.direction,
          strength: e.strength,
          prediction: e.prediction || ''
        };
      })
    };
  }

  let currentYear = new Date().getFullYear();
  if (d.annual_scans && d.annual_scans.length){
    for (let i = 0; i < d.annual_scans.length; i++){
      if (d.annual_scans[i].year === currentYear){
        return d.annual_scans[i];
      }
    }
    return d.annual_scans[0];
  }
  return null;
}

function _currentAgeNote(d){
  let ctx = _getCurrentContext(d);
  let parts = [];
  if (ctx.solar_age !== undefined && ctx.solar_age !== null) parts.push('周岁' + ctx.solar_age);
  if (ctx.liunian_age !== undefined && ctx.liunian_age !== null) parts.push('流年' + ctx.liunian_age);
  return parts.join(' · ');
}

function _collectCategorySignals(d, wanted){
  let counts = {};
  if (!d.annual_scans) return [];
  for (let i = 0; i < d.annual_scans.length; i++){
    let events = d.annual_scans[i].events || [];
    for (let j = 0; j < events.length; j++){
      let ev = events[j];
      if (ev.strength >= 2 && wanted.indexOf(ev.category) !== -1){
        counts[ev.category] = (counts[ev.category] || 0) + ev.strength;
      }
    }
  }
  return Object.keys(counts).sort(function(a,b){return counts[b] - counts[a];}).slice(0, 4);
}

function _findCurrentDayun(d){
  let ctx = _getCurrentContext(d);
  let scan = _getCurrentScan(d);
  let label = ctx.current_dayun && ctx.current_dayun.ganzhi ? ctx.current_dayun.ganzhi : (scan && scan.dayun ? scan.dayun : '');
  let age = ctx.current_dayun && ctx.current_dayun.age_range ? ctx.current_dayun.age_range : (scan && scan.age ? scan.age + '岁' : '');
  let mod = null;
  let mods = d.dayun && d.dayun.modulations ? d.dayun.modulations : [];
  for (let m = 0; m < mods.length; m++){
    let item = mods[m];
    let itemLabel = (item.dayun_stem || '') + (item.dayun_branch || '');
    if (label && itemLabel === label){
      mod = item;
      break;
    }
    if (!mod && scan && item.age_range){
      let nums = String(item.age_range).match(/\d+/g) || [];
      if (nums.length >= 2 && scan.age >= Number(nums[0]) && scan.age <= Number(nums[1])){
        mod = item;
      }
    }
  }
  if (!label && d.dayun && d.dayun.periods && d.dayun.periods.length){
    let p = d.dayun.periods[0];
    label = (p.stem || '') + (p.branch || '');
    age = _formatAgeText(p.age);
  }
  let offset = mod ? mod.baseline_offset || 0 : 0;
  let offsetText = offset > 0 ? '基调偏顺' : offset < 0 ? '基调有压' : '基调平稳';
  return {
    label: label || '待判断',
    age: age,
    theme: mod && mod.theme ? mod.theme : '综合节奏',
    offsetText: offsetText,
    note: mod && mod.branch_interactions && mod.branch_interactions.length ? mod.branch_interactions[0] : ''
  };
}

function _getXiaoyunChipTexts(d){
  let periods = d && d.xiaoyun && Array.isArray(d.xiaoyun.periods) ? d.xiaoyun.periods : [];
  return periods.map(function(period){
    if (!period || typeof period !== 'object') return '';
    let ageText = period.age ? String(period.age).trim() : '';
    let stem = period.stem ? String(period.stem).trim() : '';
    let branch = period.branch ? String(period.branch).trim() : '';
    return [ageText, stem + branch].filter(Boolean).join(' · ');
  }).filter(Boolean);
}

function _formatJiaoyunAge(detail){
  detail = detail || {};
  let units = [
    ['years', '岁'],
    ['months', '个月'],
    ['days', '天'],
    ['hours', '小时']
  ];
  let parts = [];
  let hasValidAge = false;
  for (let i = 0; i < units.length; i++){
    let rawValue = detail[units[i][0]];
    if ((typeof rawValue !== 'number' && typeof rawValue !== 'string') || !String(rawValue).trim()) continue;
    let value = Number(rawValue);
    if (!Number.isFinite(value) || value < 0) continue;
    hasValidAge = true;
    if (value > 0) parts.push(value + units[i][1]);
  }
  if (parts.length) return parts.join('');
  return hasValidAge ? '不足一月' : '';
}

function _getNormalizedJiaoyun(d){
  let detail = d && d.dayun && d.dayun.jiao_yun;
  if (!detail || typeof detail !== 'object') return {reference:'', formula:'', ageText:''};
  return {
    reference: detail.reference === undefined || detail.reference === null ? '' : String(detail.reference).trim(),
    formula: detail.formula === undefined || detail.formula === null ? '' : String(detail.formula).trim(),
    ageText: _formatJiaoyunAge(detail)
  };
}

function _getNormalizedKinshipRows(d){
  let kinship = d && d.kinship ? d.kinship : {};
  let keys = ['spouse', 'child', 'father_in_law', 'mother_in_law'];
  let rows = [];
  for (let i = 0; i < keys.length; i++){
    let item = kinship[keys[i]];
    if (!item || typeof item !== 'object') continue;
    let label = item.label === undefined || item.label === null ? '' : String(item.label).trim();
    let rawStars = Array.isArray(item.stars) ? item.stars : [item.stars];
    let stars = rawStars.map(function(value){
      return value === undefined || value === null ? '' : String(value).trim();
    }).filter(Boolean);
    if (label || stars.length) rows.push({label:label, stars:stars.join(' / ')});
  }
  return rows;
}

function _hasGenderLuckData(d, xiaoyunChipTexts, jiaoyun, kinshipRows){
  if (!d) return false;
  xiaoyunChipTexts = Array.isArray(xiaoyunChipTexts) ? xiaoyunChipTexts : _getXiaoyunChipTexts(d);
  jiaoyun = jiaoyun || _getNormalizedJiaoyun(d);
  kinshipRows = Array.isArray(kinshipRows) ? kinshipRows : _getNormalizedKinshipRows(d);
  return Boolean(jiaoyun.reference || jiaoyun.formula || jiaoyun.ageText || xiaoyunChipTexts.length || kinshipRows.length);
}

function _buildGenderLuckSection(d){
  let xiaoyunChipTexts = _getXiaoyunChipTexts(d);
  let jiaoyun = _getNormalizedJiaoyun(d);
  let kinshipRows = _getNormalizedKinshipRows(d);
  if (!_hasGenderLuckData(d, xiaoyunChipTexts, jiaoyun, kinshipRows)) return '';

  let dayun = d.dayun || {};
  let xiaoyun = d.xiaoyun || {};
  let dayunDirection = dayun.direction === undefined || dayun.direction === null ? '' : String(dayun.direction).trim();
  let xiaoyunDirection = xiaoyun.direction === undefined || xiaoyun.direction === null ? '' : String(xiaoyun.direction).trim();
  let direction = dayunDirection || xiaoyunDirection;
  let genderLabel = d.gender ? String(d.gender) + '命' : '';
  let heading = [genderLabel, direction].filter(Boolean).join(' · ') || '运势起点与六亲';
  let periods = Array.isArray(dayun.periods) ? dayun.periods : [];
  let summaryRows = '';
  let h = '';

  h += '<section id=section-gender-luck class="report-section gender-luck-section">';
  h += '<div class=report-section-head><div><span>运势起点与六亲</span><h2>' + esc(heading) + '</h2></div><p>本节只展示后端返回的规则事实，前端不重新计算顺逆排、起运或六亲规则。</p></div>';
  h += '<div class=gender-luck-panel>';
  if (direction) summaryRows += '<div class=gender-luck-summary-row><span>排运方向</span><b>' + esc(direction) + '</b></div>';

  if (periods.length){
    let firstPeriod = periods[0] || {};
    let firstStem = firstPeriod.stem === undefined || firstPeriod.stem === null ? '' : String(firstPeriod.stem).trim();
    let firstBranch = firstPeriod.branch === undefined || firstPeriod.branch === null ? '' : String(firstPeriod.branch).trim();
    let firstAge = firstPeriod.age === undefined || firstPeriod.age === null ? '' : String(firstPeriod.age).trim();
    let firstGanzhi = firstStem + firstBranch;
    if (firstGanzhi || firstAge){
      summaryRows += '<div class=gender-luck-summary-row><span>首步大运</span><b>' + esc(firstGanzhi || firstAge) + '</b>';
      if (firstGanzhi && firstAge) summaryRows += '<p>' + esc(firstAge) + '</p>';
      summaryRows += '</div>';
    }
  }

  if (jiaoyun.reference || jiaoyun.formula || jiaoyun.ageText){
    let mainText = [jiaoyun.reference, jiaoyun.ageText].filter(Boolean).join(' · ');
    summaryRows += '<div class=gender-luck-summary-row><span>交运时间</span>';
    if (mainText) summaryRows += '<b data-tip="' + esc(jiaoyun.formula) + '">' + esc(mainText) + '</b>';
    if (jiaoyun.formula){
      let formulaTip = mainText ? '' : ' data-tip="' + esc(jiaoyun.formula) + '"';
      summaryRows += '<p' + formulaTip + '>' + esc(jiaoyun.formula) + '</p>';
    }
    summaryRows += '</div>';
  }
  if (summaryRows) h += '<div class=gender-luck-summary>' + summaryRows + '</div>';

  if (xiaoyunChipTexts.length){
    h += '<div class=gender-luck-xiaoyun><h3>小运</h3><div class=gender-luck-chips tabindex="0" aria-label="小运列表">';
    for (let i = 0; i < xiaoyunChipTexts.length; i++){
      h += '<span class=gender-luck-chip>' + esc(xiaoyunChipTexts[i]) + '</span>';
    }
    h += '</div></div>';
  }

  let kinshipHtml = '';
  for (let i = 0; i < kinshipRows.length; i++){
    kinshipHtml += '<div class=gender-luck-kinship-row><span>' + esc(kinshipRows[i].label) + '</span><b>' + esc(kinshipRows[i].stars) + '</b></div>';
  }
  if (kinshipHtml) h += '<div class=gender-luck-kinship><h3>六亲对应</h3>' + kinshipHtml + '</div>';

  let sensitiveName = d.gender === '男' ? '孤辰' : d.gender === '女' ? '寡宿' : '';
  let spirits = Array.isArray(d.spirits) ? d.spirits : [];
  let sensitiveSpirit = null;
  for (let i = 0; i < spirits.length; i++){
    if (sensitiveName && spirits[i] && spirits[i].name === sensitiveName){
      sensitiveSpirit = spirits[i];
      break;
    }
  }
  if (sensitiveSpirit){
    let unfavorable = d.spirit_score && d.spirit_score.unfavorable;
    h += '<div class=gender-luck-sensitive-note><b>' + esc(sensitiveSpirit.name) + '敏感提示</b><p>传统规则将此作为关系议题的敏感信号，不代表确定结果。';
    if (unfavorable !== undefined && unfavorable !== null) h += ' 后端不利神煞分：' + esc(unfavorable) + '。';
    h += '</p></div>';
  }

  h += '</div></section>';
  return h;
}

function _buildReportFocusSections(d){
  let stageInfo = _getStageInfo(d);
  let workSignals = _collectCategorySignals(d, ['事业','学业','升学','进修','财运']);
  let relationSignals = _collectCategorySignals(d, ['桃花','人际','婚恋','家宅']);
  let currentScan = _getCurrentScan(d);
  let scanSummary = currentScan ? _summarizeAnnualScan(currentScan, d).slice(0, 3).join('、') : '暂无当前年份信号';
  let ageNote = _currentAgeNote(d);
  let dy = _findCurrentDayun(d);
  let h = '';

  h += '<section class="report-section report-focus-section" id=section-focus>';
  h += '<div class=report-section-head><div><span>事业财运</span><h2>' + (stageInfo.isStudent ? '学业、进修与资源' : '事业、财务与资源') + '</h2></div><p>把命盘信息转成现实主题，先看当前阶段和未来高频信号。</p></div>';
  h += _buildModulePrompts(stageInfo.isStudent ? '学业财运' : '事业财运', [stageInfo.isStudent ? '学业和进修重点是什么？' : '事业推进重点是什么？', '财运上应该注意什么？']);
  h += '<div class=report-card-grid>';
  h += '<div class=report-mini-card><span>当前阶段</span><b>' + esc(stageInfo.label) + '</b><p>' + (stageInfo.isStudent ? '默认把事业类信号转译为学业、考试、进修和资源支持。' : '默认按职场、项目、收入结构和资源调度来阅读。') + '</p></div>';
  h += '<div class=report-mini-card><span>高频主题</span><b>' + esc(workSignals.length ? workSignals.join('、') : '暂无明显集中信号') + '</b><p>这里只汇总已有流年事件类别，不额外新增判断。</p></div>';
  h += '<div class=report-mini-card><span>关系牵引</span><b>' + esc(relationSignals.length ? relationSignals.join('、') : '暂无明显集中信号') + '</b><p>关系和家庭信息保留在性格关系模块中阅读。</p></div>';
  h += '<div class=report-mini-card><span>当前年份</span><b>' + esc(scanSummary) + '</b><p>' + (currentScan ? esc([currentScan.year + '年 ' + (currentScan.liunian || ''), currentScan.dayun ? currentScan.dayun + '大运' : '', ageNote].filter(Boolean).join(' · ')) : '生成流年后会显示年份主线。') + '</p></div>';
  h += '</div>';
  h += '</section>';

  h += '<section class="report-section report-dayun-section" id=section-dayun>';
  h += '<div class=report-section-head><div><span>当前大运</span><h2>十年背景节奏</h2></div><p>大运、流年和年龄为规则事实；下方 AI 解读只做解释翻译，若冲突以规则事实为准。</p></div>';
  h += _buildModulePrompts('当前大运', ['当前大运对我影响最大的是什么？', '这步大运适合主动还是保守？']);
  h += '<div class=dayun-focus-card>';
  h += '<div><span>大运</span><b>' + esc(dy.label) + '</b><p>' + esc([dy.age, ageNote, dy.theme, dy.offsetText].filter(Boolean).join(' · ')) + '</p></div>';
  if (dy.note) h += '<div class=dayun-focus-note>' + esc(dy.note) + '</div>';
  h += '<div class=dayun-interpretations>';
  h += _buildDayunInterpretations(d) || '<div class=dayun-loading>⏳ 大运解读生成中...</div>';
  h += '</div>';
  h += '</div>';
  h += '</section>';

  return h;
}

function _buildReportNav(d){
  let items = [
  ];
  if (d.personality || d.family) items.push({id:'section-personality', label:'性格关系'});
  items.push({id:'section-focus', label:'事业财运'});
  items.push({id:'section-dayun', label:'当前大运'});
  if (_hasGenderLuckData(d)) items.push({id:'section-gender-luck', label:'运势起点'});
  if (d.annual_scans && d.annual_scans.length) items.push({id:'section-flow', label:'未来流年'});
  items.push({id:'section-calendar', label:'择日'});
  items.push({id:'section-foundation', label:'原始依据'});

  let h = '<nav class=report-nav aria-label=报告导航>';
  h += '<span class=report-nav-label>报告导航</span>';
  for (let i = 0; i < items.length; i++){
    h += '<a href="#' + items[i].id + '">' + items[i].label + '</a>';
  }
  h += '</nav>';
  return h;
}

function _buildModulePrompts(contextLabel, prompts){
  if (!prompts || !prompts.length) return '';
  let h = '<div class=module-prompts>';
  for (let i = 0; i < prompts.length; i++){
    h += '<button type=button onclick="askModuleQuestion(\'' + esc(contextLabel) + '\', \'' + esc(prompts[i]) + '\')">' + esc(prompts[i]) + '</button>';
  }
  h += '</div>';
  return h;
}

/* ==========================================
   Render
   ========================================== */
function render(d){
  // 存储命盘数据供 AI 追问用
  d = setChartData(d);
  let ym = d.four_pillars;
  let labels = {year:'年', month:'月', day:'日', hour:'时'};
  let h = '';

  h += _buildReportOverview(d);
  h += _buildReportNav(d);
  h += _buildReportFocusSections(d);
  h += _buildGenderLuckSection(d);

  // Four pillars
  h += '<section class=report-section id=section-foundation>';
  h += '<div class=report-section-head><div><span>原始依据</span><h2>命盘与规则细节</h2></div><p>四柱、格局、喜忌和大运是规则事实来源；AI 解读只负责把这些事实转成白话。</p></div>';
  h += _buildModulePrompts('命盘', ['这个格局现实里意味着什么？', '这条判断依据是什么？']);
  h += '<details class=evidence-details><summary>查看原始命盘与规则依据</summary><div class=evidence-body>';
  h += '<div class=section-title>四柱</div><div class=pillars>';
  for (let i = 0, keys = ['year','month','day','hour']; i < keys.length; i++){
    let k = keys[i], pv = ym[k];
    let cg = pv.hidden_stems.map(function(x){return x.stem}).join('');
    let tg = pv.ten_god || '日主';
    let isDay = k === 'day' ? ' day-pillar' : '';
    let clickAttr = k === 'day' ? ' data-daymaster' : '';
    h += '<div class="pillar' + isDay + '"' + clickAttr + '>';
    h += '<div class=pillar-label>' + labels[k] + '</div>';
    h += '<div class=stem-branch>' + pv.stem + pv.branch + '</div>';
    h += '<div class=nayin-text data-tip="' + TERMS['纳音'] + '">' + pv.nayin + '</div>';
    h += '<div class=hidden-stems data-tip="' + TERMS['藏干'] + '">' + (cg || '—') + '</div>';
    h += '<div class=ten-god data-tip="' + TERMS['十神'] + '">' + tg + '</div>';
    h += '</div>';
  }
  h += '</div>';

  // Info panel
  h += '<div class=section-title>命盘</div><div class=info-panel><div class=info-grid>';

  h += '<div class=info-item>';
  h += '<span class=info-label data-tip="' + TERMS['日主'] + '">日主</span>';
  h += '<span class=info-value>' + d.day_master.stem + '（' + d.day_master.wuxing + '）<span style="font-weight:400;color:var(--text-tertiary)">' + d.day_master.yinyang + '</span></span>';
  h += '</div>';

  h += '<div class=info-item>';
  h += '<span class=info-label data-tip="' + TERMS['格局'] + '">格局</span>';
  h += '<span class=info-value>' + d.pattern + '</span>';
  h += '</div>';

  if (d.yongshen){
    h += '<div class=info-item>';
    h += '<span class=info-label>身强弱</span>';
    h += '<span class=info-value>' + d.yongshen.strength + ' <span style="font-weight:400;color:var(--text-tertiary)">' + d.yongshen.score + '分</span></span>';
    h += '</div>';
    h += '<div class=info-item>';
    h += '<span class=info-label>喜用 / 忌神</span>';
    h += '<span class=info-value><span class=modal-good>' + d.yongshen.favorable_wuxing.join(' ') + '</span> &nbsp;<span style="color:var(--text-tertiary)">|</span>&nbsp; <span class=modal-bad>' + d.yongshen.harmful_wuxing.join(' ') + '</span></span>';
    h += '</div>';
  }

  if (d.minggong && d.minggong.stem){
    h += '<div class=info-item>';
    h += '<span class=info-label data-tip="' + TERMS['命宫'] + '">命宫</span>';
    h += '<span class=info-value>' + d.minggong.stem + d.minggong.branch + ' <span style="font-weight:400;color:var(--text-tertiary)">' + d.minggong.nayin + '</span></span>';
    h += '</div>';
    h += '<div class=info-item>';
    h += '<span class=info-label data-tip="' + TERMS['身宫'] + '">身宫</span>';
    h += '<span class=info-value>' + d.shengong.stem + d.shengong.branch + ' <span style="font-weight:400;color:var(--text-tertiary)">' + d.shengong.nayin + '</span></span>';
    h += '</div>';
    if (d.taiyuan && d.taiyuan.stem){
      h += '<div class=info-item>';
      h += '<span class=info-label data-tip="' + TERMS['胎元'] + '">胎元</span>';
      h += '<span class=info-value>' + d.taiyuan.stem + d.taiyuan.branch + ' <span style="font-weight:400;color:var(--text-tertiary)">' + d.taiyuan.nayin + '</span></span>';
      h += '</div>';
    }
  }

  h += '<div class="info-item full">';
  h += '<span class=info-label data-tip="' + TERMS['大运'] + '">大运（' + d.dayun.start_age + '岁起运 · ' + d.dayun.direction + '）</span>';
  h += '<div class=dayun-scroll>';
  for (let j = 0; j < Math.min(d.dayun.periods.length, 8); j++){
    let p = d.dayun.periods[j];
    h += '<span class=dayun-tag>' + p.stem + p.branch + ' <span style="color:var(--text-tertiary)">' + _formatAgeText(p.age) + '</span></span>';
  }
  h += '</div></div>';
  // 大运 LLM 解读（v0.14.0: SSE 异步填充）
  h += '<div class=dayun-interpretations>';
  h += _buildDayunInterpretations(d) || '<div class=dayun-loading>⏳ 大运解读生成中...</div>';
  h += '</div>';
  h += '</div></div>'; // /info-panel + /info-grid

  // 人生阶段指示器
  if (d.life_stage){
    let stageLabels = {中学:'中学时期',大学:'大学时期',深造:'深造时期',职场:'职场时期',晚年:'晚年时期'};
    let stageLabel = stageLabels[d.life_stage] || d.life_stage;
    let isStudent = d.life_stage === '中学' || d.life_stage === '大学' || d.life_stage === '深造';
    let canToggle = true;
    h += '<div class=life-stage-bar>';
    h += '<span class=life-stage-label>当前判定：</span>';
    h += '<span class="life-stage-badge ' + (isStudent ? 'student' : '') + '">' + stageLabel + '</span>';
    h += '<span class=life-stage-desc>';
    if (d.life_stage === '大学'){
      h += '— 事业/财运标签已适配学生身份。如果实际已工作，可切换：';
    } else if (d.life_stage === '中学'){
      h += '— 事业/财运标签已适配学生身份。如果实际已辍学工作，可切换：';
    } else if (d.life_stage === '深造'){
      h += '— 如果还在读研/读博，当前判定已为深造；如果已工作，可切换为职场：';
    } else {
      h += '— 自动判定结果。如果不符合实际，可点击切换按钮手动指定身份阶段。';
    }
    h += '</span>';
    if (canToggle){
      let allStages2 = ['中学','大学','深造','职场','晚年'];
      let curStage2 = sessionStorage.getItem('bazi-life-stage') || d.life_stage;
      let curIdx2 = allStages2.indexOf(curStage2);
      if (curIdx2 < 0) curIdx2 = 2;
      let prevIdx2 = curIdx2 - 1; if (prevIdx2 < 0) prevIdx2 = allStages2.length - 1;
      let nextIdx2 = curIdx2 + 1; if (nextIdx2 >= allStages2.length) nextIdx2 = 0;
      h += '<span style="font-size:11px;color:var(--text-tertiary);margin-right:6px">引擎判定: ' + stageLabel + '</span>';
      h += '<button class="stage-toggle-btn" onclick="toggleLifeStage(\'' + curStage2 + '\', -1)" style="margin-right:4px">◀</button>';
      h += '<button class="stage-toggle-btn" onclick="toggleLifeStage(\'' + curStage2 + '\', 1)">▶</button>';
    }
    h += '</div>';
  }

  // 格局/喜忌指示条
  if (d.pattern && d.yongshen){
    let fav = d.yongshen.favorable || [];
    let harm = d.yongshen.harmful || [];
    h += '<div class=info-panel style="margin-bottom:12px;padding:10px 16px">';
    h += '<span style="font-size:12px;color:var(--text-tertiary)">格局:</span> ';
    h += '<span style="font-size:14px;font-weight:600;color:var(--text)">' + esc(d.pattern) + '</span>';
    h += '<span style="margin:0 12px;color:var(--border)">|</span>';
    h += '<span style="font-size:12px;color:var(--text-tertiary)">喜:</span> ';
    h += '<span class="pattern-fav">' + esc(fav.join(' ')) + '</span>';
    h += '<span style="margin:0 8px;color:var(--border)">·</span>';
    h += '<span style="font-size:12px;color:var(--text-tertiary)">忌:</span> ';
    h += '<span class="pattern-harm">' + esc(harm.join(' ')) + '</span>';
    h += '</div>';
  }

  // 性格与家境分析
  h += '</div></details>';
  h += '</section>';

  let fusionReady = d.personality && d.personality._fusion_ready;
  if (d.personality || d.family){
    h += '<section class=report-section id=section-personality>';
    h += '<div class=report-section-head><div><span>性格关系</span><h2>行为模式与家庭背景</h2></div><p>默认阅读报告正文，需要核对时再展开规则依据。</p></div>';
    h += _buildModulePrompts('性格', ['这段性格最需要注意什么？', '这会如何影响关系？', '这条判断依据是什么？']);
  }
  if (d.personality){
    h += '<div class=section-title>' + (fusionReady ? '性格与家境' : '性格') + ' <span class=ask-ai-btn onclick="event.stopPropagation();openChat(\'性格\')">问AI</span></div>';
    h += '<div class=info-panel>';

    // ── 病药高亮卡片 ──
    if (!fusionReady && d.personality.bingyao_combos && d.personality.bingyao_combos.length){
      h += _buildBingyaoCard(d.personality.bingyao_combos);
    }

    // ── 十神排行 ──
    if (!fusionReady && d.personality.weighted_shishen && d.personality.weighted_shishen.scores){
      h += _buildShishenRank(d.personality.weighted_shishen.scores);
    }

    // ── 性格内容区 ──
    h += '<div class=personality-body id=personalityBody>';
    h += '<div class=personality-text>';
    if (fusionReady){
      h += '<span class=fusion-placeholder>⏳ AI 融合报告生成中...</span>';
    } else {
      h += d.personality.profile;
    }
    h += '</div>';

    // 六维度网格：仅非融合模式显示
    if (!fusionReady){
      h += '<div class=traits-grid>';
      let traitLabels = {社交:'社交',感情:'感情',决策:'决策',内心:'内心',事业:'事业',财富观:'财富观'};
      for (let tk in traitLabels){
        if (d.personality.traits && d.personality.traits[tk]){
          h += '<div class=trait-tile><span class=trait-label>' + tk + '</span><span class=trait-text>' + d.personality.traits[tk] + '</span></div>';
        }
      }
      h += '</div>';
    }
    h += '</div>';

    if (fusionReady){
      h += '<div class=fusion-feedback hidden>';
      h += '<div class=fusion-feedback-title>这份分析像你吗？</div>';
      h += '<div class=fusion-rating-options role=group aria-label="报告命中度">';
      h += '<button type=button data-rating=very onclick="selectFusionRating(\'very\',this)">很像</button>';
      h += '<button type=button data-rating=partial onclick="selectFusionRating(\'partial\',this)">部分像</button>';
      h += '<button type=button data-rating=low onclick="selectFusionRating(\'low\',this)">不太像</button>';
      h += '</div>';
      h += '<div class=fusion-feedback-detail hidden><span>哪部分偏差最大？</span>';
      h += '<div class=fusion-section-options>';
      h += '<button type=button onclick="submitFusionFeedback(\'core\')">核心画像</button>';
      h += '<button type=button onclick="submitFusionFeedback(\'moments\')">三个瞬间</button>';
      h += '<button type=button onclick="submitFusionFeedback(\'analysis\')">重点分析</button>';
      h += '<button type=button onclick="submitFusionFeedback(\'misunderstood\')">容易被误解</button>';
      h += '<button type=button class=fusion-feedback-skip onclick="submitFusionFeedback(\'\')">跳过</button>';
      h += '</div></div><div class=fusion-feedback-status role=status></div></div>';
    }

    // ── 融合/原始切换 ──
    if (fusionReady){
      h += '<div class=personality-toggle><button class=toggle-btn data-personality-mode=fusion onclick="togglePersonalityMode()" title="查看规则引擎原始数据">查看原始数据</button></div>';
      h += '<div class=personality-raw id=personalityRaw style="display:none">';
      // 病药
      if (d.personality.bingyao_combos && d.personality.bingyao_combos.length){
        h += _buildBingyaoCard(d.personality.bingyao_combos);
      }
      // 十神排行
      if (d.personality.weighted_shishen && d.personality.weighted_shishen.scores){
        h += _buildShishenRank(d.personality.weighted_shishen.scores);
      }
      // profile + 六维度
      h += '<div class=personality-profile-raw>' + (d.personality.profile || '') + '</div>';
      h += '<div class=traits-grid>';
      for (let tk2 in {社交:'社交',感情:'感情',决策:'决策',内心:'内心',事业:'事业',财富观:'财富观'}){
        if (d.personality.traits && d.personality.traits[tk2]){
          h += '<div class=trait-tile><span class=trait-label>' + tk2 + '</span><span class=trait-text>' + d.personality.traits[tk2] + '</span></div>';
        }
      }
      h += '</div></div>';
    }

    h += '</div>';
  }

  if (d.family && !fusionReady){
    h += '<div class=section-title>家境 <span class=ask-ai-btn onclick="event.stopPropagation();openChat(\'家境\')">问AI</span></div>';
    h += '<div class=info-panel>';
    h += '<div class=family-level><span class=family-badge>' + (d.family.level_label || '') + '</span></div>';
    // 显示差异对比（引擎推断 vs 用户反馈）
    if (d.family.reality && d.family.reality.indexOf('你反馈') !== -1){
      h += '<div style="font-size:12px;color:var(--gold);text-align:center;margin:4px 0 10px;line-height:1.5">' + esc(d.family.reality) + '</div>';
    }
    if (d.family.family_type) h += '<div style=font-size:12px;color:var(--text-secondary);margin-bottom:8px;line-height:1.6>' + d.family.family_type + '</div>';
    h += '<div class=family-text>' + ((d.family.profile || '').replace(/\n/g, '<br>')) + '</div>';
    h += '</div>';
  }
  if (d.personality || d.family){
    h += '</section>';
  }

  // Store day_master data for modal
  let dmData = {
    stem: d.day_master.stem,
    wuxing: d.day_master.wuxing,
    yinyang: d.day_master.yinyang,
    pattern: d.pattern,
    strength: d.yongshen ? d.yongshen.strength : '',
    score: d.yongshen ? d.yongshen.score : '',
    good: d.yongshen ? d.yongshen.favorable_wuxing.join(' ') : '',
    bad: d.yongshen ? d.yongshen.harmful_wuxing.join(' ') : '',
    nayin: ym.day.nayin,
    canggan: ym.day.hidden_stems.map(function(x){return x.stem}).join(''),
  };
  document.getElementById('result').dataset.dm = JSON.stringify(dmData);

  // ── 择日月历 ──
  h += '<section class=report-section id=section-calendar>';
  h += '<div class=report-section-head><div><span>择日</span><h2>近期可用日历</h2></div><p>用于快速查看近期开启行动的日期参考。</p></div>';
  h += _buildCalendar(d);
  h += '</section>';

  // Flow years
  if (d.annual_scans && d.annual_scans.length){
    h += '<section class=report-section id=section-flow>';
    h += '<div class=report-section-head><div><span>流年</span><h2>年份趋势时间线</h2></div><p>优先看年份主线，展开后再看触发依据和详细事件。</p></div>';
    h += _buildModulePrompts('流年', ['未来三年重点注意哪一年？', '这些流年信号怎么理解？', '哪一年适合主动推进？']);
    h += '<div class=section-title>流年</div>';

    // Collect unique categories for filter
    let allCats = {};
    for (let si = 0; si < d.annual_scans.length; si++){
      let scan = d.annual_scans[si];
      for (let ei = 0; ei < scan.events.length; ei++){
        if (scan.events[ei].strength >= 2) allCats[scan.events[ei].category] = true;
      }
    }
    let cats = Object.keys(allCats);
    if (cats.length > 1){
      h += '<div class=filter-bar>';
      h += '<span class="filter-pill active" data-filter="all">全部</span>';
      for (let ci = 0; ci < cats.length; ci++){
        h += '<span class="filter-pill" data-filter="' + cats[ci] + '">' + cats[ci] + '</span>';
      }
      h += '</div>';
    }

    h += '<div class=events-section>';
    let hasAny = false;
    for (let s = 0; s < d.annual_scans.length; s++){
      let scan = d.annual_scans[s];
      let significant = scan.events.filter(function(e){return e.strength >= 2});
      if (!significant.length) continue;
      hasAny = true;

      let summary = _summarizeAnnualScan(scan, d);

      // 构建顶栏标签: 类别 + 方向
      let tagBadges = [];
      for (let e = 0; e < significant.length; e++){
        let ev = significant[e];
        let dirSymbol = ev.direction === '正面' ? '↑' : ev.direction === '负面' ? '↓' : '·';
        tagBadges.push('<span class=header-tag>' + ev.category + dirSymbol + '</span>');
      }

      h += '<div class=event-card>';
      h += '<div class=event-header>';
      h += '<span class=event-year>' + scan.year + '</span>';
      h += '<span class=event-ganzhi>' + scan.liunian + '</span>';
      h += '<span class=event-age>' + scan.age + '岁</span>';
      h += '<span class=event-tags>' + tagBadges.join('') + '</span>';
      h += '<span class=chevron>▶</span>';
      h += '</div>';
      h += '<div class=event-summary-line>' + esc(summary.slice(0, 3).join('、')) + '</div>';
      // 可展开详情: 每个事件独立一行，小提示归类到各自事件下
      h += '<div class=event-body>';
      for (let e = 0; e < significant.length; e++){
        let ev2 = significant[e];
        let cls2 = ev2.direction === '负面' ? 'direction-bad' : ev2.direction === '正面' ? 'direction-good' : '';
        h += '<div class=event-item data-category="' + ev2.category + '">';
        // 主行: 星级 + 类别 + 方向 + 预测
        h += '<div class=event-main>';
        h += '<span class=stars>' + '★'.repeat(ev2.strength) + '</span>';
        h += '<span class=tag>' + ev2.category + '</span>';
        h += '<span class="' + cls2 + '">' + ev2.direction + '</span>';
        if (ev2.prediction) h += '<span class=prediction-text>' + ev2.prediction + '</span>';
        h += '</div>';
        // 触发词
        if (ev2.triggers[0]) {
          let trigFull = ev2.triggers[0];
          trigFull = trigFull.replace(/\[忌\]/g, '<span class=tag-ji>忌</span>');
          trigFull = trigFull.replace(/\[喜\]/g, '<span class=tag-xi>喜</span>');
          h += '<div class=event-trigger>' + trigFull + '</div>';
        }
        // 小提示: 性格联动 + 引擎备注
        let hints = [];
        if (ev2.personality_note) hints.push(ev2.personality_note);
        if (ev2.notes) hints = hints.concat(ev2.notes);
        if (hints.length) {
          h += '<div class=event-hints>';
          for (let hi = 0; hi < hints.length; hi++) {
            h += '<div class=event-hint><span class=hint-dot></span>' + hints[hi] + '</div>';
          }
          h += '</div>';
        }
        h += '</div>';
      }
      h += '</div></div>'; // /event-body + /event-card
    }
    if (!hasAny) h += '<div class=empty-state>该年份范围无显著信号</div>';
    h += '</div>'; // /events-section
    h += '</section>';
  }

  // 时辰未确认警告
  if (d.warnings && d.warnings.length){
    h += '<div class=report-warning style="background:var(--error-bg);border:1px solid var(--gold);border-radius:8px;padding:12px 16px;margin-bottom:16px;font-size:13px;color:var(--gold);line-height:1.7">';
    for (let wi = 0; wi < d.warnings.length; wi++){
      h += esc(d.warnings[wi]) + '<br>';
    }
    h += '</div>';
  }

  document.getElementById('result').innerHTML = h;
  document.getElementById('copyBtn').style.display = 'inline-block';
  document.getElementById('reportActions').classList.add('active');

  // 如果用户填写了家境信息，自动提交反馈
  let fl = document.getElementById('familyLevel').value;
  if (fl){
    fetch('/api/feedback', {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        chart_data: d,
        family_level: fl,
        father_job: document.getElementById('fatherJob').value.trim(),
        mother_job: document.getElementById('motherJob').value.trim()
      })
    }).catch(function(){});
  }
}

/* ==========================================
   Global click delegation
   ========================================== */
document.addEventListener('click', function(e){
  let target = e.target;

  // Toggle event card collapse
  let header = target.closest('.event-header');
  if (header) {
    let card = header.parentElement;
    card.classList.toggle('open');
    return;
  }

  // Category filter
  if (target.classList.contains('filter-pill')) {
    let filter = target.dataset.filter;
    let pills = document.querySelectorAll('.filter-pill');
    for (let i = 0; i < pills.length; i++) pills[i].classList.remove('active');
    target.classList.add('active');
    // Clear old placeholders
    let oldMsgs = document.querySelectorAll('.no-signal-msg');
    for (let m = 0; m < oldMsgs.length; m++) oldMsgs[m].remove();
    applyEventFilter(filter);
    return;
  }

  // Day pillar modal
  let p = target.closest('.pillar[data-daymaster]');
  if (p && !target.closest('.event-header')){
    let dm = JSON.parse(document.getElementById('result').dataset.dm || '{}');
    if (!dm.stem) return;
    let mc = document.getElementById('modalContent');
    mc.innerHTML =
      '<div class=modal-row><span class=modal-label>日主</span><span class=modal-value>' + dm.stem + '（' + dm.wuxing + ' · ' + dm.yinyang + '）</span></div>' +
      '<div class=modal-row><span class=modal-label>纳音</span><span class=modal-value>' + dm.nayin + '</span></div>' +
      '<div class=modal-row><span class=modal-label>藏干</span><span class=modal-value>' + dm.canggan + '</span></div>' +
      '<div class=modal-row><span class=modal-label>格局</span><span class=modal-value>' + dm.pattern + '</span></div>' +
      (dm.strength ? '<div class=modal-row><span class=modal-label>身强弱</span><span class=modal-value>' + dm.strength + ' <span style="font-weight:400;color:var(--text-tertiary)">' + dm.score + '分</span></span></div>' : '') +
      (dm.good ? '<div class=modal-row><span class=modal-label>喜用神</span><span class="modal-value modal-good">' + dm.good + '</span></div>' : '') +
      (dm.bad ? '<div class=modal-row><span class=modal-label>忌神</span><span class="modal-value modal-bad">' + dm.bad + '</span></div>' : '');
    document.getElementById('modal').classList.add('open');
    document.body.style.overflow = 'hidden';
    return;
  }

  // Close modal
  if (target.id === 'modalClose' || target.id === 'modal') {
    document.getElementById('modal').classList.remove('open');
    document.body.style.overflow = '';
    return;
  }

  // Back to top
  if (target.id === 'backTop' || target.closest('#backTop')) {
    window.scrollTo({top: 0, behavior: 'smooth'});
    return;
  }
});

/* ── LLM推理逐字显示 ── */
function _buildDayunInterpretations(d){
  let h = '';
  if (d.dayun.interpretations && d.dayun.interpretations.length){
    h += '<div class="info-item full dayun-interps">';
    h += '<span class=info-label>大运解读</span>';
    for (let i = 0; i < Math.min(d.dayun.interpretations.length, 8); i++){
      let di = d.dayun.interpretations[i];
      let p = d.dayun.periods[di.index] || {};
      h += '<div style="padding:4px 0;font-size:13px;line-height:1.7;color:var(--text-secondary)">';
      h += '<strong style="color:var(--text-primary)">' + (p.stem||'') + (p.branch||'') + '</strong> ';
      h += '<span style="color:var(--text-tertiary)">' + (p.age||'') + '</span> — ';
      h += di.interpretation;
      h += '</div>';
    }
    h += '</div>';
  }
  return h;
}

function updateLlmTokenDisplay(year, text){
  let el = document.querySelector('.llm-live-section');
  if (!el){
    // 在流年区域前插入实时显示区
    let flowEl = document.querySelector('.events-section');
    if (!flowEl) return;
    el = document.createElement('div');
    el.className = 'llm-live-section';
    el.innerHTML = '<div class=section-title>AI 分析中...</div>';
    flowEl.parentNode.insertBefore(el, flowEl);
  }
  let yearEl = el.querySelector('[data-llm-year="' + year + '"]');
  if (!yearEl){
    yearEl = document.createElement('div');
    yearEl.className = 'llm-year-item';
    yearEl.setAttribute('data-llm-year', year);
    yearEl.innerHTML = '<span class=llm-year-label>' + year + '年：</span><span class=llm-year-text></span>';
    el.appendChild(yearEl);
  }
  let textEl = yearEl.querySelector('.llm-year-text');
  if (textEl) textEl.textContent = text;
  // 自动滚动到最新
  el.scrollTop = el.scrollHeight;
}

/* ── 流式排盘: 局部刷新流年区域（LLM结果到达时）── */
function refreshFlowSection(d){
  if (!d || !d.annual_scans) return;
  let el = document.querySelector('.events-section');
  if (!el) return;
  let h = '';
  let hasAny = false;
  for (let s = 0; s < d.annual_scans.length; s++){
    let scan = d.annual_scans[s];
    let significant = scan.events.filter(function(e){return e.strength >= 2});
    if (!significant.length) continue;
    hasAny = true;
    let summary = _summarizeAnnualScan(scan, d);
    let tagBadges = [];
    for (let e = 0; e < significant.length; e++){
      let ev = significant[e];
      let dirSymbol = ev.direction === '正面' ? '↑' : ev.direction === '负面' ? '↓' : '·';
      tagBadges.push('<span class=header-tag>' + ev.category + dirSymbol + '</span>');
    }
    h += '<div class=event-card>';
    h += '<div class=event-header>';
    h += '<span class=event-year>' + scan.year + '</span>';
    h += '<span class=event-ganzhi>' + scan.liunian + '</span>';
    h += '<span class=event-age>' + scan.age + '岁</span>';
    h += '<span class=event-tags>' + tagBadges.join('') + '</span>';
    h += '<span class=chevron>▶</span>';
    h += '</div>';
    h += '<div class=event-summary-line>' + esc(summary.slice(0, 3).join('、')) + '</div>';
    h += '<div class=event-body>';
    for (let e = 0; e < significant.length; e++){
      let ev2 = significant[e];
      let cls2 = ev2.direction === '负面' ? 'direction-bad' : ev2.direction === '正面' ? 'direction-good' : '';
      h += '<div class=event-item data-category="' + ev2.category + '">';
      h += '<div class=event-main>';
      h += '<span class=stars>' + '★'.repeat(ev2.strength) + '</span>';
      h += '<span class=tag>' + ev2.category + '</span>';
      h += '<span class="' + cls2 + '">' + ev2.direction + '</span>';
      if (ev2.source === 'llm') h += '<span class=llm-badge>🤖</span>';
      if (ev2.prediction) h += '<span class=prediction-text>' + ev2.prediction + '</span>';
      h += '</div>';
      if (ev2.triggers[0]){
        let trigFull = ev2.triggers[0];
        trigFull = trigFull.replace(/\[忌\]/g, '<span class=tag-ji>忌</span>');
        trigFull = trigFull.replace(/\[喜\]/g, '<span class=tag-xi>喜</span>');
        h += '<div class=event-trigger>' + trigFull + '</div>';
      }
      let hints = [];
      if (ev2.personality_note) hints.push(ev2.personality_note);
      if (ev2.notes) hints = hints.concat(ev2.notes);
      if (hints.length){
        h += '<div class=event-hints>';
        for (let hi = 0; hi < hints.length; hi++){
          h += '<div class=event-hint><span class=hint-dot></span>' + hints[hi] + '</div>';
        }
        h += '</div>';
      }
      h += '</div>';
    }
    h += '</div></div>';
  }
  if (!hasAny) h += '<div class=empty-state>该年份范围无显著信号</div>';
  // 只替换事件卡片列表（筛选栏是.events-section的兄弟节点，不受影响）
  el.innerHTML = h;
  // 恢复筛选状态
  let activeFilter = document.querySelector('.filter-pill.active');
  if (activeFilter){
    let cat = activeFilter.dataset.filter;
    if (cat && cat !== 'all') applyEventFilter(cat);
  }
}

function applyEventFilter(cat){
  let items = document.querySelectorAll('.event-item');
  for (let j = 0; j < items.length; j++){
    items[j].style.display = (cat === 'all' || items[j].dataset.category === cat) ? '' : 'none';
  }
  let cards = document.querySelectorAll('.event-card');
  for (let c = 0; c < cards.length; c++){
    let bodyItems = cards[c].querySelectorAll('.event-item');
    let anyVisible = false;
    for (let k = 0; k < bodyItems.length; k++){
      if (bodyItems[k].style.display !== 'none'){ anyVisible = true; break; }
    }
    if (cat === 'all'){
      cards[c].classList.remove('open');
    } else if (anyVisible){
      cards[c].classList.add('open');
    } else {
      cards[c].classList.add('open');
      let msg = document.createElement('div');
      msg.className = 'no-signal-msg';
      msg.textContent = '该年无此类信号';
      cards[c].querySelector('.event-body').appendChild(msg);
    }
  }
}

/* ==========================================
   Copy result
   ========================================== */
document.getElementById('copyBtn').addEventListener('click', function(){
  let result = document.getElementById('result');
  let text = result.innerText.trim();
  if (!text) return;
  navigator.clipboard.writeText(text).then(function(){
    let btn = document.getElementById('copyBtn');
    let orig = btn.textContent;
    btn.textContent = '✓ 已复制';
    setTimeout(function(){ btn.textContent = orig; }, 1800);
  }).catch(function(){
    // Fallback for older browsers
    let ta = document.createElement('textarea');
    ta.value = text; ta.style.position = 'fixed'; ta.style.opacity = '0';
    document.body.appendChild(ta); ta.select();
    document.execCommand('copy');
    document.body.removeChild(ta);
    let btn = document.getElementById('copyBtn');
    let orig2 = btn.textContent;
    btn.textContent = '✓ 已复制';
    setTimeout(function(){ btn.textContent = orig2; }, 1800);
  });
});

/* ==========================================
   Back to top visibility
   ========================================== */
(function(){
  let btn = document.getElementById('backTop');
  let ticking = false;
  window.addEventListener('scroll', function(){
    if (!ticking){
      requestAnimationFrame(function(){
        if (window.scrollY > 400){
          btn.classList.add('visible');
        } else {
          btn.classList.remove('visible');
        }
        ticking = false;
      });
      ticking = true;
    }
  });
})();

/* ==========================================
   Escape to close modal
   ========================================== */
document.addEventListener('keydown', function(e){
  if (e.key === 'Escape'){
    let m = document.getElementById('modal');
    if (m) m.classList.remove('open');
    let p = document.getElementById('payModal');
    if (p){ p.classList.remove('active'); p.style.display = ''; }
    let d = document.getElementById('disclaimerModal');
    if (d) d.classList.remove('active');
    document.body.style.overflow = '';
  }
});


/* ═══════════════════════════════════════════════════════════════
   AI 聊天系统
   ═══════════════════════════════════════════════════════════════ */
let CHAT = {
  visible: false, chartData: null,
  history: [], activationCode: '',
  isStreaming: false, enabled: false
};

/* ── 字符串相似度（简单 Jaccard，用于重复问题检测）── */
function strSim(a, b){
  if (a === b) return 1;
  let setA = {}, setB = {};
  for (let i = 0; i < a.length - 1; i++){ let bg = a.substring(i, i+2); setA[bg] = (setA[bg]||0) + 1; }
  for (let j = 0; j < b.length - 1; j++){ let bg2 = b.substring(j, j+2); setB[bg2] = (setB[bg2]||0) + 1; }
  let intersection = 0, union = 0;
  let allKeys = {}; for (let k in setA) allKeys[k] = 1; for (let k in setB) allKeys[k] = 1;
  for (let k in allKeys){ let va = setA[k]||0, vb = setB[k]||0; intersection += Math.min(va, vb); union += Math.max(va, vb); }
  return union === 0 ? 0 : intersection / union;
}

/* ── 简易 Markdown → HTML ── */
function _stripScores(t){
  // 引擎数字评分 → 人类可读标签
  // "表达欲 7.2" → "表达欲偏高"  "拘谨度 2.5" → "拘谨度偏低"
  // "群体融入 5.1" → "群体融入"（4-6中等不标）
  t = t.replace(/([\u4e00-\u9fff\w]{2,8})\s+(\d+\.?\d*)/g, function(_, label, num){
    let v = parseFloat(num);
    if (v >= 7) return label + '偏高';
    if (v <= 3) return label + '偏低';
    return label;
  });
  // LLM 输出变体: "表达欲低（3.0）" / "表达欲低(3.0)" / "表达欲:3.0"
  t = t.replace(/([\u4e00-\u9fff\w]{2,12})[：:]\s*(\d+\.?\d*)/g, function(_, label, num){
    let v = parseFloat(num);
    if (v >= 7) return label + '偏高';
    if (v <= 3) return label + '偏低';
    return label;
  });
  // "拘谨度高达9.0" / "表达欲低至2.5" → "拘谨度偏高" / "表达欲偏低"
  t = t.replace(/([\u4e00-\u9fff\w]{2,12})(?:高达|低至|接近|约)\s*(\d+\.?\d*)/g, function(_, label, num){
    let v = parseFloat(num);
    if (v >= 7) return label + '偏高';
    if (v <= 3) return label + '偏低';
    return label;
  });
  // 中文括号包裹的数字: "表达欲低（3.0）" → "表达欲偏低"
  t = t.replace(/（\s*(\d+\.?\d*)\s*）/g, function(_, num){
    let v = parseFloat(num);
    if (v >= 7) return '（偏高）';
    if (v <= 3) return '（偏低）';
    return '';
  });
  // 英文括号包裹的数字: "表达欲低(3.0)" → "表达欲偏低"
  t = t.replace(/\(\s*(\d+\.?\d*)\s*\)/g, function(_, num){
    let v = parseFloat(num);
    if (v >= 7) return '（偏高）';
    if (v <= 3) return '（偏低）';
    return '';
  });
  // "综合分数 7.2" → ""
  t = t.replace(/综合分数\s*\d+\.?\d*/g, '');
  // "_需覆盖信号: ..." → 删除整行
  t = t.replace(/[「「]_需覆盖信号[：:][^」\n]*[」」]?/g, '');
  t = t.replace(/_需覆盖信号[：:][^\n]*/g, '');
  // 孤立的逗号分隔数字序列
  t = t.replace(/([，,]\s*\d+\.?\d*\s*)+/g, '');
  // 清理多余空格（保留换行，否则会吞掉 \n\n 导致 ##/### 失配）
  t = t.replace(/[^\S\n]{2,}/g, ' ');
  return t;
}

/* ==========================================
   Calendar (择日)
   ========================================== */
function _buildCalendar(d){
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
  setChartData(d);  // 保存命盘数据供 API 请求用

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
  let chartData = getChartData();
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
  // 过滤引擎数字泄露
  t = _stripScores(t);
  // 先跑 Markdown → HTML，再统一保护标签后转义纯文本
  // 宽松匹配：空格可选，兼容 LLM 输出 "##社交" 或 "## 社交"
  t = t.replace(/^###\s*(.+)/gm, '<h3>$1</h3>');
  t = t.replace(/^##\s*(.+)/gm, '<h2>$1</h2>');
  t = t.replace(/^#\s*(.+)/gm, '<h1>$1</h1>');
  t = t.replace(/^> (.+)/gm, '<blockquote>$1</blockquote>');
  t = t.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
  t = t.replace(/\*(.+?)\*/g, '<em>$1</em>');
  t = t.replace(/`([^`]+)`/g, '<code>$1</code>');
  t = t.replace(/^- (.+)/gm, '<li>$1</li>');
  t = t.replace(/(<li>.*<\/li>\s*)+/g, '<ul>$&</ul>');
  t = t.replace(/^---+/gm, '<hr>');
  t = t.replace(/^\|(.+)\|\n\|[-| ]+\|\n((?:\|.+\|\n?)+)/gm, function(m,hdr,rows){
    let h = '<tr>' + hdr.split('|').filter(Boolean).map(function(c){return '<th>'+c.trim()+'</th>'}).join('') + '</tr>';
    let r = rows.trim().split('\n').map(function(rw){
      return '<tr>' + rw.split('|').filter(Boolean).map(function(c){return '<td>'+c.trim()+'</td>'}).join('') + '</tr>';
    }).join('');
    return '<table>'+h+r+'</table>';
  });
  // 保护所有已生成的 HTML 标签（markdown 输出的 + 原文中的）
  let safe = [];
  t = t.replace(/(<[^>]+>)/g, function(m){ safe.push(m); return '\x00' + (safe.length-1) + '\x00'; });
  // 转义剩余纯文本
  t = t.replace(/[&<>"]/g, function(m){ return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[m]; });
  // 还原所有标签
  t = t.replace(/\x00(\d+)\x00/g, function(_,i){ return safe[parseInt(i)]; });
  t = t.replace(/\n\n/g, '</p><p>');
  t = '<p>' + t + '</p>';
  t = t.replace(/<p>\s*<\/p>/g, '');
  t = t.replace(/\n/g, '<br>');
  return t;
}

/* ── 复制 AI 回复 ── */
function copyBubble(btn){
  let bubble = btn.closest('.chat-bubble');
  let text = bubble.textContent || bubble.innerText || '';
  navigator.clipboard.writeText(text).then(function(){
    btn.textContent = '已复制';
    setTimeout(function(){ btn.textContent = '复制'; }, 1500);
  }).catch(function(){});
}

/* ── LLM 融合引擎流式加载 ── */
let FUSION_FEEDBACK_STATE = {reportText:'', generation:{}, rating:'', submitting:false};

function showFusionFeedback(reportText, generation){
  let box = document.querySelector('.fusion-feedback');
  if (!box || !reportText) return;
  FUSION_FEEDBACK_STATE = {reportText:reportText, generation:generation || {}, rating:'', submitting:false};
  box.hidden = false;
  let detail = box.querySelector('.fusion-feedback-detail');
  let status = box.querySelector('.fusion-feedback-status');
  if (detail) detail.hidden = true;
  if (status) status.textContent = '';
  box.querySelectorAll('button').forEach(function(btn){
    btn.disabled = false;
    btn.classList.remove('active');
    if (btn.dataset.rating) btn.setAttribute('aria-pressed', 'false');
  });
}

function selectFusionRating(rating, button){
  if (FUSION_FEEDBACK_STATE.submitting) return;
  FUSION_FEEDBACK_STATE.rating = rating;
  let box = button.closest('.fusion-feedback');
  box.querySelectorAll('[data-rating]').forEach(function(btn){
    let active = btn === button;
    btn.classList.toggle('active', active);
    btn.setAttribute('aria-pressed', active ? 'true' : 'false');
  });
  if (rating === 'very'){
    submitFusionFeedback('');
  } else {
    box.querySelector('.fusion-feedback-detail').hidden = false;
  }
}

async function submitFusionFeedback(section){
  let state = FUSION_FEEDBACK_STATE;
  let box = document.querySelector('.fusion-feedback');
  if (!box || !state.rating || state.submitting) return;
  state.submitting = true;
  let status = box.querySelector('.fusion-feedback-status');
  box.querySelectorAll('button').forEach(function(btn){ btn.disabled = true; });
  if (status) status.textContent = '提交中...';
  try{
    let resp = await fetch('/api/personality/fusion/feedback', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body:JSON.stringify({
        rating:state.rating,
        inaccurate_section:section || '',
        report_text:state.reportText,
        generation:state.generation
      })
    });
    if (!resp.ok) throw new Error('feedback ' + resp.status);
    box.innerHTML = '<div class=fusion-feedback-thanks role=status>感谢反馈</div>';
  }catch(e){
    state.submitting = false;
    box.querySelectorAll('button').forEach(function(btn){ btn.disabled = false; });
    if (status) status.textContent = '提交失败，请稍后重试';
  }
}

async function streamFusionReport(personality, family, lifeStage, dayMaster){
  let el = document.querySelector('.personality-text');
  if (!el) return;
  let initialText = el.textContent;
  el.innerHTML = '<span class=fusion-placeholder>正在生成融合报告</span><span class=fusion-cursor>|</span>';
  let text = '';

  try{
    let resp = await fetch('/api/personality/fusion/stream', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({personality: personality, family: family || null, life_stage: lifeStage, age_info: dayMaster || null})
    });
    let reader = resp.body.getReader();
    let decoder = new TextDecoder();
    let buf = '';

    while(true){
      let r = await reader.read();
      if (r.done) break;
      buf += decoder.decode(r.value, {stream:true});
      let lines = buf.split('\n');
      buf = lines.pop() || '';
      for (let i = 0; i < lines.length; i++){
        let line = lines[i].trim();
        if (!line.startsWith('data: ')) continue;
        let data = line.slice(6);
        if (data === '[DONE]'){
          el.innerHTML = md2html(text) || initialText;
          showFusionFeedback(text, {});
          return;
        }
        try{
          let chunk = JSON.parse(data);
          if (chunk.token){
            text += chunk.token;
            el.innerHTML = md2html(text) + '<span class=fusion-cursor>|</span>';
          } else if (chunk.done){
            let finalText = chunk.full || text;
            el.innerHTML = md2html(finalText) || initialText;
            showFusionFeedback(finalText, chunk.meta || {});
            return;
          } else if (chunk.error){
            el.textContent = initialText;
            return;
          }
        }catch(e){}
      }
    }
    el.innerHTML = md2html(text) || initialText;
    showFusionFeedback(text, {});
  }catch(e){
    el.textContent = initialText;
  }
}

/* ── Chat 面板控制 ── */
function openChat(contextLabel){
  if (!CHAT.enabled){
    CHAT.visible = true;
    document.getElementById('chatPanel').classList.add('open');
    document.getElementById('chatOverlay').classList.add('active');
    let msgs = document.getElementById('chatMessages');
    msgs.innerHTML = '<div class=chat-empty><div>AI 功能暂未开放<br><span style=font-size:11px>敬请期待</span></div><div style=margin-top:10px;padding:10px 14px;background:var(--tag-bg);border-radius:8px;font-size:11px;line-height:1.7;text-align:left>💬 <b>收费标准</b><br>· 每日免费 3 次<br>· ⚡体验版 ¥6.9 / 20次<br>· ⭐推荐版 ¥12.9 / 60次<br>· 👑尊享版 ¥19.9 / 永久<br>· 点击 <b>解锁</b> 获取激活码</div></div>';
    return;
  }
  if (!localStorage.getItem('bazi-disclaimer')){
    document.getElementById('disclaimerModal').classList.add('active');
    return;
  }
  if (!getChartData()){ showMsg('请先排盘');return; }
  CHAT.visible = true;
  document.getElementById('chatPanel').classList.add('open');
  document.getElementById('chatOverlay').classList.add('active');
  if (contextLabel) setChatContext(contextLabel);
  loadQuota();
  setTimeout(function(){
    let msgs = document.getElementById('chatMessages');
    msgs.scrollTop = msgs.scrollHeight;
  }, 100);
}
function closeChat(){
  CHAT.visible = false;
  document.getElementById('chatPanel').classList.remove('open');
  document.getElementById('chatOverlay').classList.remove('active');
}
function toggleChat(){ CHAT.visible ? closeChat() : openChat(); }

function askModuleQuestion(contextLabel, question){
  if (contextLabel) setChatContext(contextLabel);
  openChat(contextLabel);
  useSuggestion(question);
}

function setChatContext(label){
  let input = document.getElementById('chatInput');
  input.placeholder = '追问' + label + '…';
  input.dataset.context = label;
  let hint = document.getElementById('chatContextHint');
  if (hint){
    let factHint = _buildChatFactHint();
    hint.textContent = '当前上下文：' + label + '。'
      + (factHint ? '当前事实：' + factHint + '。' : '')
      + '输入框内容不会自动发送。';
    hint.classList.add('active');
  }
}

/* ── 发送消息 ── */
async function sendChat(){
  let input = document.getElementById('chatInput');
  let q = input.value.trim();
  if (!q || CHAT.isStreaming) return;
  // 检查是否与历史问题重复（相似度 > 80% 则提示）
  let dup = null;
  for (let i = 0; i < CHAT.history.length; i++){
    if (CHAT.history[i].role === 'user'){
      let similarity = strSim(q, CHAT.history[i].content);
      if (similarity > 0.8){ dup = CHAT.history[i].content; break; }
    }
  }
  if (dup){
    let confirmed = confirm('⚠ 你之前问过类似问题：「' + dup.substring(0,40) + '…」\n\n是否仍要发送？本次仍会消耗追问次数。');
    if (!confirmed){ input.focus(); return; }
  }
  input.value = ''; input.focus();
  appendBubble(q, 'user');
  appendTyping();

  CHAT.isStreaming = true;
  document.getElementById('chatSendBtn').disabled = true;

  let ctx = input.dataset.context || '';
  let fullQ = ctx ? '【关于' + ctx + '】' + q : q;

  try{
    let resp = await fetch('/api/chat', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({
        question: fullQ,
        chart_data: getChartData(),
        activation_code: CHAT.activationCode,
        history: CHAT.history
      })
    });
    removeTyping();
    let bubble = appendBubble('', 'ai');
    let text = '';
    let reader = resp.body.getReader();
    let decoder = new TextDecoder();
    let buf = '';

    while(true){
      let r = await reader.read();
      if (r.done) break;
      buf += decoder.decode(r.value, {stream:true});
      let lines = buf.split('\n');
      buf = lines.pop() || '';
      for (let i = 0; i < lines.length; i++){
        let line = lines[i].trim();
        if (!line.startsWith('data: ')) continue;
        let data = line.slice(6);
        if (data === '[DONE]'){
          break;
        }
        if (data.startsWith('[ERROR]')){
          text += data.slice(7);
          bubble.innerHTML = md2html(text);
          break;
        }
        try{
          let chunk = JSON.parse(data);
          if (chunk.token){
            text += chunk.token;
            bubble.innerHTML = md2html(text);
            let msgs = document.getElementById('chatMessages');
            msgs.scrollTop = msgs.scrollHeight;
          }
        }catch(e){}
      }
    }
    if (text){
      CHAT.history.push({role:'user',content:q});
      CHAT.history.push({role:'assistant',content:text});
      if (CHAT.history.length > 30) CHAT.history = CHAT.history.slice(-30);
    }
  }catch(e){
    removeTyping();
    appendBubble('请求失败: ' + e.message, 'ai');
  }
  CHAT.isStreaming = false;
  document.getElementById('chatSendBtn').disabled = false;
  loadQuota();
}

function appendBubble(text, role){
  let msgs = document.getElementById('chatMessages');
  let div = document.createElement('div');
  div.className = 'chat-bubble ' + role;
  let inner = role === 'ai' ? (text ? md2html(text) : '') : esc(text);
  div.innerHTML = inner;
  if (role === 'ai' && text){
    let actions = document.createElement('div');
    actions.className = 'bubble-actions';
    actions.innerHTML = '<button onclick=copyBubble(this)>复制</button>';
    div.appendChild(actions);
  }
  msgs.appendChild(div);
  msgs.scrollTop = msgs.scrollHeight;
  return div;
}
function appendTyping(){
  let msgs = document.getElementById('chatMessages');
  let div = document.createElement('div');
  div.className = 'typing-indicator';
  div.innerHTML = '<span></span><span></span><span></span>';
  div.id = 'typingIndicator';
  msgs.appendChild(div);
  msgs.scrollTop = msgs.scrollHeight;
}
function removeTyping(){
  let el = document.getElementById('typingIndicator');
  if (el) el.remove();
}
function showMsg(msg){
  let msgs = document.getElementById('chatMessages');
  let div = document.createElement('div');
  div.className = 'chat-bubble ai';
  div.textContent = msg;
  msgs.appendChild(div);
}

/* ── 追问建议 ── */
function useSuggestion(text){
  document.getElementById('chatInput').value = text;
  document.getElementById('chatInput').focus();
}

/* ── 额度 ── */
async function loadQuota(){
  let badge = document.getElementById('quotaBadge');
  try{
    let url = '/api/chat/quota';
    if (CHAT.activationCode) url += '?code=' + CHAT.activationCode;
    let r = await fetch(url);
    let d = await r.json();
    if (d.has_code){
      badge.textContent = '激活码剩余' + d.remaining + '次';
    } else {
      badge.textContent = '今日免费' + d.remaining + '次';
    }
  }catch(e){ badge.textContent = ''; }
}

/* ── 激活码 ── */
function openPayModal(){
  let m = document.getElementById('payModal');
  m.classList.add('active');
  m.style.display = 'flex';
}
function closePayModal(){
  let m = document.getElementById('payModal');
  m.classList.remove('active');
  m.style.display = '';
}
function submitActivationCode(){
  let code = document.getElementById('actCodeInput').value.trim().toUpperCase();
  let status = document.getElementById('actCodeStatus');
  if (!code){ status.textContent = '请输入激活码'; status.className='status-msg error'; return; }
  fetch('/api/chat/quota?code=' + code).then(function(r){return r.json()}).then(function(d){
    if (d.remaining > 0){
      CHAT.activationCode = code;
      localStorage.setItem('bazi-act-code', code);
      status.textContent = '激活成功！剩余' + d.remaining + '次';
      status.className = 'status-msg success';
      loadQuota();
      setTimeout(closePayModal, 1200);
    } else {
      status.textContent = d.remaining === 0 ? '该激活码次数已用完' : '激活码无效';
      status.className = 'status-msg error';
    }
  });
}

/* ── 免责弹窗 ── */
function closeDisclaimer(){
  document.getElementById('disclaimerModal').classList.remove('active');
}
function acceptDisclaimer(){
  localStorage.setItem('bazi-disclaimer', '1');
  document.getElementById('disclaimerModal').classList.remove('active');
}
document.addEventListener('DOMContentLoaded', function(){
  // 自动检测 API 地址（当前页面同源）
  let autoUrl = location.protocol + '//' + location.host;
  document.getElementById('apiUrl').value = autoUrl;
  let saved = localStorage.getItem('bazi-act-code');
  if (saved){ CHAT.activationCode = saved; }
  // 检测 AI 功能可用性
  fetch(autoUrl + '/api/health').then(function(r){return r.json()}).then(function(d){
    CHAT.enabled = d.ai_enabled === true;
  }).catch(function(){});
});
