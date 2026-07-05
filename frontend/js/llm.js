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
    let cats2 = significant.map(function(e){return e.category});
    let dirs2 = significant.map(function(e){return e.direction});
    let curStage = sessionStorage.getItem('bazi-life-stage') || d.life_stage || '职场';
    let isStudent = curStage === '中学' || curStage === '大学' || curStage === '深造';
    let summary = [];
    if (cats2.indexOf('桃花') !== -1) summary.push(dirs2[cats2.indexOf('桃花')] === '负面' ? '感情波动' : '感情运升');
    if (cats2.indexOf('事业') !== -1) summary.push(dirs2[cats2.indexOf('事业')] === '负面' ? (isStudent ? '学业压力' : '事业有压') : (isStudent ? '校园活跃' : '事业有进'));
    if (cats2.indexOf('学业') !== -1) summary.push(dirs2[cats2.indexOf('学业')] === '负面' ? '学业压力' : '校园活跃');
    if (cats2.indexOf('财运') !== -1) summary.push(dirs2[cats2.indexOf('财运')] === '负面' ? (isStudent ? '手头偏紧' : '注意财务') : (isStudent ? '经济宽松' : '财运关注'));
    if (cats2.indexOf('健康') !== -1) summary.push('留意健康');
    if (cats2.indexOf('升学') !== -1) summary.push(isStudent ? '学业运佳' : '进修运佳');
    if (cats2.indexOf('搬迁') !== -1) summary.push('可能搬迁');
    if (cats2.indexOf('状态') !== -1) summary.push(dirs2[cats2.indexOf('状态')] === '负面' ? '状态低迷' : '状态良好');
    if (cats2.indexOf('人际') !== -1) summary.push(dirs2[cats2.indexOf('人际')] === '负面' ? '人际有摩擦' : '人际和谐');
    if (!summary.length) summary.push('运势平稳');
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
