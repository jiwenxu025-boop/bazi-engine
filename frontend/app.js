/* HTML 转义：防止用户输入中的 <>&'" 破坏页面结构 */
function esc(s){ return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;'); }

/* ==========================================
   Theme
   ========================================== */
(function(){
  var saved = localStorage.getItem('bazi-theme');
  var prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
  var theme = saved || (prefersDark ? 'dark' : 'light');
  if (theme === 'dark') document.documentElement.classList.add('dark');
  updateToggle();
})();

function toggleLifeStage(currentStage, direction){
  // 始终允许所有阶段切换，用户最了解自己的实际情况
  var allStages = ['中学','大学','深造','职场','晚年'];
  var curIdx = allStages.indexOf(currentStage);
  if (curIdx < 0) curIdx = 2;

  var newIdx = curIdx + direction;
  if (newIdx >= allStages.length) newIdx = 0;
  if (newIdx < 0) newIdx = allStages.length - 1;

  sessionStorage.setItem('bazi-life-stage', allStages[newIdx]);
  go();
}

function toggleTheme(){
  var html = document.documentElement;
  html.classList.toggle('dark');
  localStorage.setItem('bazi-theme', html.classList.contains('dark') ? 'dark' : 'light');
  updateToggle();
}

function updateToggle(){
  var btn = document.getElementById('themeToggle');
  var isDark = document.documentElement.classList.contains('dark');
  btn.textContent = isDark ? '☾' : '☀';
  btn.title = isDark ? '切换浅色模式' : '切换深色模式';
}

document.getElementById('themeToggle').addEventListener('click', toggleTheme);

/* ==========================================
   API URL auto-set
   ========================================== */
(function(){
  var el = document.getElementById('apiUrl');
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

async function go(){
  var btn = document.getElementById('submitBtn');
  btn.disabled = true; btn.textContent = '计算中...';
  var r = document.getElementById('result');
  r.className = 'result visible';
  r.innerHTML = '<div class=loading-state><div class=spinner></div><div>计算中&#x2026;</div></div>';
  document.getElementById('copyBtn').style.display = 'none';

  var api = document.getElementById('apiUrl').value.replace(/\/$/, '');
  var params = new URLSearchParams({
    name: document.getElementById('name').value || '未知',
    gender: document.getElementById('gender').value,
    year: document.getElementById('year').value,
    month: document.getElementById('month').value,
    day: document.getElementById('day').value,
    hour: document.getElementById('hour').value,
    liunian_from: document.getElementById('lnFrom').value,
    liunian_to: document.getElementById('lnTo').value,
    hour_confirmed: document.getElementById('hourConfirmed').checked,
    practical: true,  // 公网只显示白话解读，不暴露技术推导
  });
  var fl = document.getElementById('familyLevel').value;
  if (fl) params.set('family_level', fl);
  var fj = document.getElementById('fatherJob').value.trim();
  if (fj) params.set('father_job', fj);
  var mj = document.getElementById('motherJob').value.trim();
  if (mj) params.set('mother_job', mj);
  var lsOverride = sessionStorage.getItem('bazi-life-stage');
  if (lsOverride) params.set('life_stage', lsOverride);

  try {
    // v0.11.2: 流式排盘——规则引擎立即渲染，LLM结果流式追加
    var streamUrl = api + '/api/chart/stream?' + params;
    var resp = await fetch(streamUrl);
    if (!resp.ok) throw new Error('API ' + resp.status);

    var streamReader = resp.body.getReader();
    var decoder = new TextDecoder();
    var buf = '';
    var d = null;           // 完整命盘数据
    var personalityEl = null;
    var personalityText = '';

    while(true){
      var chunk = await streamReader.read();
      if (chunk.done) break;
      buf += decoder.decode(chunk.value, {stream:true});
      var lines = buf.split('\n');
      buf = lines.pop() || '';
      for (var i = 0; i < lines.length; i++){
        var line = lines[i].trim();
        if (!line.startsWith('data: ')) continue;
        var payload = line.slice(6);
        if (payload === '[DONE]'){ buf = ''; break; }
        try {
          var msg = JSON.parse(payload);
          if (msg.phase === 'started'){
            // 连接已建立，更新加载提示
            r.innerHTML = '<div class=loading-state><div class=spinner></div><div>规则引擎计算中...</div></div>';
          } else if (msg.phase === 'rules_done'){
            // 1. 规则引擎完成，立即渲染
            d = msg.chart;
            render(d);
            setTimeout(function(){
              r.scrollIntoView({behavior: 'smooth', block: 'start'});
            }, 80);
          } else if (msg.phase === 'llm_result'){
            // 2. LLM审查某年完成，合并信号到对应年份
            if (d && d.annual_scans){
              for (var si = 0; si < d.annual_scans.length; si++){
                if (d.annual_scans[si].year === msg.year){
                  for (var sj = 0; sj < msg.signals.length; sj++){
                    d.annual_scans[si].events.push(msg.signals[sj]);
                  }
                  break;
                }
              }
              // 局部刷新流年区域
              refreshFlowSection(d);
            }
          } else if (msg.phase === 'personality_token'){
            // 3. 性格报告逐token
            if (!personalityEl){
              personalityEl = document.querySelector('.personality-text');
              if (personalityEl) personalityEl.innerHTML = '';
            }
            if (personalityEl){
              personalityText += msg.token;
              personalityEl.innerHTML = md2html(personalityText) + '<span class=fusion-cursor>|</span>';
            }
          } else if (msg.phase === 'personality_done'){
            // 4. 性格报告完成
            if (personalityEl && msg.full){
              personalityEl.innerHTML = md2html(msg.full);
            }
          }
          // phase===done → 流结束，循环自然退出
        } catch(e){}
      }
    }
  } catch(e) {
    r.innerHTML = '<div class=error-state>请求失败: ' + e.message + '<br><small style="color:' + (document.documentElement.classList.contains('dark') ? '#a0a0b0' : '#78716c') + '">请确认 API 地址可访问</small></div>';
  }
  btn.disabled = false; btn.textContent = '排盘';
}

/* ==========================================
   Term definitions
   ========================================== */
var TERMS = {
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
   Render
   ========================================== */
function render(d){
  // 存储命盘数据供 AI 追问用
  CHAT.chartData = d;
  var ym = d.four_pillars;
  var labels = {year:'年', month:'月', day:'日', hour:'时'};
  var h = '';

  // Four pillars
  h += '<div class=section-title>四柱</div><div class=pillars>';
  for (var i = 0, keys = ['year','month','day','hour']; i < keys.length; i++){
    var k = keys[i], pv = ym[k];
    var cg = pv.hidden_stems.map(function(x){return x.stem}).join('');
    var tg = pv.ten_god || '日主';
    var isDay = k === 'day' ? ' day-pillar' : '';
    var clickAttr = k === 'day' ? ' data-daymaster' : '';
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
  for (var j = 0; j < Math.min(d.dayun.periods.length, 8); j++){
    var p = d.dayun.periods[j];
    h += '<span class=dayun-tag>' + p.stem + p.branch + ' <span style="color:var(--text-tertiary)">' + p.age + '岁</span></span>';
  }
  h += '</div></div>';
  h += '</div></div>'; // /info-panel + /info-grid

  // 人生阶段指示器
  if (d.life_stage){
    var stageLabels = {中学:'中学时期',大学:'大学时期',深造:'深造时期',职场:'职场时期',晚年:'晚年时期'};
    var stageLabel = stageLabels[d.life_stage] || d.life_stage;
    var isStudent = d.life_stage === '中学' || d.life_stage === '大学' || d.life_stage === '深造';
    var canToggle = true;
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
      var allStages2 = ['中学','大学','深造','职场','晚年'];
      var curStage2 = sessionStorage.getItem('bazi-life-stage') || d.life_stage;
      var curIdx2 = allStages2.indexOf(curStage2);
      if (curIdx2 < 0) curIdx2 = 2;
      var prevIdx2 = curIdx2 - 1; if (prevIdx2 < 0) prevIdx2 = allStages2.length - 1;
      var nextIdx2 = curIdx2 + 1; if (nextIdx2 >= allStages2.length) nextIdx2 = 0;
      h += '<span style="font-size:11px;color:var(--text-tertiary);margin-right:6px">引擎判定: ' + stageLabel + '</span>';
      h += '<button class="stage-toggle-btn" onclick="toggleLifeStage(\'' + curStage2 + '\', -1)" style="margin-right:4px">◀</button>';
      h += '<button class="stage-toggle-btn" onclick="toggleLifeStage(\'' + curStage2 + '\', 1)">▶</button>';
    }
    h += '</div>';
  }

  // 格局/喜忌指示条
  if (d.pattern && d.yongshen){
    var fav = d.yongshen.favorable || [];
    var harm = d.yongshen.harmful || [];
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
  var fusionReady = d.personality && d.personality._fusion_ready;
  if (d.personality){
    h += '<div class=section-title>' + (fusionReady ? '性格与家境' : '性格') + ' <span class=ask-ai-btn onclick="event.stopPropagation();openChat(\'性格\')">问AI</span></div>';
    h += '<div class=info-panel><div class=personality-text>';
    if (!fusionReady){
      h += d.personality.profile;
    }
    h += '</div>';
    // 六维度网格：仅非融合模式显示
    if (!fusionReady){
      h += '<div class=traits-grid style="margin-top:14px;display:grid;grid-template-columns:1fr 1fr;gap:8px 20px">';
      var traitLabels = {社交:'社交',感情:'感情',决策:'决策',内心:'内心',事业:'事业',财富观:'财富观'};
      for (var tk in traitLabels){
        if (d.personality.traits && d.personality.traits[tk]){
          h += '<div><span style="font-size:11px;color:var(--text-tertiary)">' + tk + '</span><br><span style="font-size:13px;color:var(--text)">' + d.personality.traits[tk] + '</span></div>';
        }
      }
      h += '</div>';
    }
    h += '</div></div>';
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

  // Store day_master data for modal
  var dmData = {
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

  // Flow years
  if (d.annual_scans && d.annual_scans.length){
    h += '<div class=section-title>流年</div>';

    // Collect unique categories for filter
    var allCats = {};
    for (var si = 0; si < d.annual_scans.length; si++){
      var scan = d.annual_scans[si];
      for (var ei = 0; ei < scan.events.length; ei++){
        if (scan.events[ei].strength >= 2) allCats[scan.events[ei].category] = true;
      }
    }
    var cats = Object.keys(allCats);
    if (cats.length > 1){
      h += '<div class=filter-bar>';
      h += '<span class="filter-pill active" data-filter="all">全部</span>';
      for (var ci = 0; ci < cats.length; ci++){
        h += '<span class="filter-pill" data-filter="' + cats[ci] + '">' + cats[ci] + '</span>';
      }
      h += '</div>';
    }

    h += '<div class=events-section>';
    var hasAny = false;
    for (var s = 0; s < d.annual_scans.length; s++){
      var scan = d.annual_scans[s];
      var significant = scan.events.filter(function(e){return e.strength >= 2});
      if (!significant.length) continue;
      hasAny = true;

      var cats2 = significant.map(function(e){return e.category});
      var dirs2 = significant.map(function(e){return e.direction});
      var summary = [];
      // 获取当前人生阶段（优先用用户手动切换的）
      var curStage = sessionStorage.getItem('bazi-life-stage') || d.life_stage || '职场';
      var isStudent = curStage === '中学' || curStage === '大学' || curStage === '深造';
      if (cats2.indexOf('桃花') !== -1) summary.push(dirs2[cats2.indexOf('桃花')] === '负面' ? '感情波动' : '感情运升');
      if (cats2.indexOf('事业') !== -1) summary.push(dirs2[cats2.indexOf('事业')] === '负面' ? (isStudent ? '学业压力' : '事业有压') : (isStudent ? '校园活跃' : '事业有进'));
      if (cats2.indexOf('学业') !== -1) summary.push(dirs2[cats2.indexOf('学业')] === '负面' ? '学业压力' : '校园活跃');
      if (cats2.indexOf('财运') !== -1) summary.push(dirs2[cats2.indexOf('财运')] === '负面' ? (isStudent ? '手头偏紧' : '注意财务') : (isStudent ? '经济宽松' : '财运关注'));
      if (cats2.indexOf('健康') !== -1) summary.push('留意健康');
      if (cats2.indexOf('升学') !== -1) summary.push(isStudent ? '学业运佳' : '进修运佳');
      if (cats2.indexOf('进修') !== -1) summary.push('进修运佳');
      if (cats2.indexOf('搬迁') !== -1) summary.push('可能搬迁');
      if (cats2.indexOf('状态') !== -1) summary.push(dirs2[cats2.indexOf('状态')] === '负面' ? '状态低迷' : '状态良好');
      if (cats2.indexOf('人际') !== -1) summary.push(dirs2[cats2.indexOf('人际')] === '负面' ? '人际有摩擦' : '人际和谐');
      if (!summary.length) summary.push('运势平稳');

      // 构建顶栏标签: 类别 + 方向
      var tagBadges = [];
      for (var e = 0; e < significant.length; e++){
        var ev = significant[e];
        var dirSymbol = ev.direction === '正面' ? '↑' : ev.direction === '负面' ? '↓' : '·';
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
      // 可展开详情: 每个事件独立一行，小提示归类到各自事件下
      h += '<div class=event-body>';
      for (var e = 0; e < significant.length; e++){
        var ev2 = significant[e];
        var cls2 = ev2.direction === '负面' ? 'direction-bad' : ev2.direction === '正面' ? 'direction-good' : '';
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
          var trigFull = ev2.triggers[0];
          trigFull = trigFull.replace(/\[忌\]/g, '<span class=tag-ji>忌</span>');
          trigFull = trigFull.replace(/\[喜\]/g, '<span class=tag-xi>喜</span>');
          h += '<div class=event-trigger>' + trigFull + '</div>';
        }
        // 小提示: 性格联动 + 引擎备注
        var hints = [];
        if (ev2.personality_note) hints.push(ev2.personality_note);
        if (ev2.notes) hints = hints.concat(ev2.notes);
        if (hints.length) {
          h += '<div class=event-hints>';
          for (var hi = 0; hi < hints.length; hi++) {
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
  }

  // 时辰未确认警告
  if (d.warnings && d.warnings.length){
    h += '<div style="background:var(--error-bg);border:1px solid var(--gold);border-radius:8px;padding:12px 16px;margin-bottom:16px;font-size:13px;color:var(--gold);line-height:1.7">';
    for (var wi = 0; wi < d.warnings.length; wi++){
      h += esc(d.warnings[wi]) + '<br>';
    }
    h += '</div>';
  }

  document.getElementById('result').innerHTML = h;
  document.getElementById('copyBtn').style.display = 'inline-block';

  // 如果用户填写了家境信息，自动提交反馈
  var fl = document.getElementById('familyLevel').value;
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
  var target = e.target;

  // Toggle event card collapse
  var header = target.closest('.event-header');
  if (header) {
    var card = header.parentElement;
    card.classList.toggle('open');
    return;
  }

  // Category filter
  if (target.classList.contains('filter-pill')) {
    var filter = target.dataset.filter;
    var pills = document.querySelectorAll('.filter-pill');
    for (var i = 0; i < pills.length; i++) pills[i].classList.remove('active');
    target.classList.add('active');
    // Clear old placeholders
    var oldMsgs = document.querySelectorAll('.no-signal-msg');
    for (var m = 0; m < oldMsgs.length; m++) oldMsgs[m].remove();
    applyEventFilter(filter);
    return;
  }

  // Day pillar modal
  var p = target.closest('.pillar[data-daymaster]');
  if (p && !target.closest('.event-header')){
    var dm = JSON.parse(document.getElementById('result').dataset.dm || '{}');
    if (!dm.stem) return;
    var mc = document.getElementById('modalContent');
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

/* ── 流式排盘: 局部刷新流年区域（LLM结果到达时）── */
function refreshFlowSection(d){
  if (!d || !d.annual_scans) return;
  var el = document.querySelector('.events-section');
  if (!el) return;
  var h = '';
  var hasAny = false;
  for (var s = 0; s < d.annual_scans.length; s++){
    var scan = d.annual_scans[s];
    var significant = scan.events.filter(function(e){return e.strength >= 2});
    if (!significant.length) continue;
    hasAny = true;
    var cats2 = significant.map(function(e){return e.category});
    var dirs2 = significant.map(function(e){return e.direction});
    var curStage = sessionStorage.getItem('bazi-life-stage') || d.life_stage || '职场';
    var isStudent = curStage === '中学' || curStage === '大学' || curStage === '深造';
    var summary = [];
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
    var tagBadges = [];
    for (var e = 0; e < significant.length; e++){
      var ev = significant[e];
      var dirSymbol = ev.direction === '正面' ? '↑' : ev.direction === '负面' ? '↓' : '·';
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
    for (var e = 0; e < significant.length; e++){
      var ev2 = significant[e];
      var cls2 = ev2.direction === '负面' ? 'direction-bad' : ev2.direction === '正面' ? 'direction-good' : '';
      h += '<div class=event-item data-category="' + ev2.category + '">';
      h += '<div class=event-main>';
      h += '<span class=stars>' + '★'.repeat(ev2.strength) + '</span>';
      h += '<span class=tag>' + ev2.category + '</span>';
      h += '<span class="' + cls2 + '">' + ev2.direction + '</span>';
      if (ev2.prediction) h += '<span class=prediction-text>' + ev2.prediction + '</span>';
      h += '</div>';
      if (ev2.triggers[0]){
        var trigFull = ev2.triggers[0];
        trigFull = trigFull.replace(/\[忌\]/g, '<span class=tag-ji>忌</span>');
        trigFull = trigFull.replace(/\[喜\]/g, '<span class=tag-xi>喜</span>');
        h += '<div class=event-trigger>' + trigFull + '</div>';
      }
      var hints = [];
      if (ev2.personality_note) hints.push(ev2.personality_note);
      if (ev2.notes) hints = hints.concat(ev2.notes);
      if (hints.length){
        h += '<div class=event-hints>';
        for (var hi = 0; hi < hints.length; hi++){
          h += '<div class=event-hint><span class=hint-dot></span>' + hints[hi] + '</div>';
        }
        h += '</div>';
      }
      h += '</div>';
    }
    h += '</div></div>';
  }
  if (!hasAny) h += '<div class=empty-state>该年份范围无显著信号</div>';
  // 保留筛选栏，只替换事件列表
  var filterBar = el.querySelector('.filter-bar');
  el.innerHTML = (filterBar ? filterBar.outerHTML : '') + h;
  // 恢复筛选状态
  var activeFilter = document.querySelector('.filter-pill.active');
  if (activeFilter){
    var cat = activeFilter.dataset.filter;
    if (cat && cat !== 'all') applyEventFilter(cat);
  }
}

function applyEventFilter(cat){
  var items = document.querySelectorAll('.event-item');
  for (var j = 0; j < items.length; j++){
    items[j].style.display = (cat === 'all' || items[j].dataset.category === cat) ? '' : 'none';
  }
  var cards = document.querySelectorAll('.event-card');
  for (var c = 0; c < cards.length; c++){
    var bodyItems = cards[c].querySelectorAll('.event-item');
    var anyVisible = false;
    for (var k = 0; k < bodyItems.length; k++){
      if (bodyItems[k].style.display !== 'none'){ anyVisible = true; break; }
    }
    if (cat === 'all'){
      cards[c].classList.remove('open');
    } else if (anyVisible){
      cards[c].classList.add('open');
    } else {
      cards[c].classList.add('open');
      var msg = document.createElement('div');
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
  var result = document.getElementById('result');
  var text = result.innerText.trim();
  if (!text) return;
  navigator.clipboard.writeText(text).then(function(){
    var btn = document.getElementById('copyBtn');
    var orig = btn.textContent;
    btn.textContent = '✓ 已复制';
    setTimeout(function(){ btn.textContent = orig; }, 1800);
  }).catch(function(){
    // Fallback for older browsers
    var ta = document.createElement('textarea');
    ta.value = text; ta.style.position = 'fixed'; ta.style.opacity = '0';
    document.body.appendChild(ta); ta.select();
    document.execCommand('copy');
    document.body.removeChild(ta);
    var btn = document.getElementById('copyBtn');
    var orig2 = btn.textContent;
    btn.textContent = '✓ 已复制';
    setTimeout(function(){ btn.textContent = orig2; }, 1800);
  });
});

/* ==========================================
   Back to top visibility
   ========================================== */
(function(){
  var btn = document.getElementById('backTop');
  var ticking = false;
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
    var m = document.getElementById('modal');
    if (m) m.classList.remove('open');
    var p = document.getElementById('payModal');
    if (p){ p.classList.remove('active'); p.style.display = ''; }
    var d = document.getElementById('disclaimerModal');
    if (d) d.classList.remove('active');
    document.body.style.overflow = '';
  }
});


/* ═══════════════════════════════════════════════════════════════
   AI 聊天系统
   ═══════════════════════════════════════════════════════════════ */
var CHAT = {
  visible: false, chartData: null,
  history: [], activationCode: '',
  isStreaming: false, enabled: false
};

/* ── 字符串相似度（简单 Jaccard，用于重复问题检测）── */
function strSim(a, b){
  if (a === b) return 1;
  var setA = {}, setB = {};
  for (var i = 0; i < a.length - 1; i++){ var bg = a.substring(i, i+2); setA[bg] = (setA[bg]||0) + 1; }
  for (var j = 0; j < b.length - 1; j++){ var bg2 = b.substring(j, j+2); setB[bg2] = (setB[bg2]||0) + 1; }
  var intersection = 0, union = 0;
  var allKeys = {}; for (var k in setA) allKeys[k] = 1; for (var k in setB) allKeys[k] = 1;
  for (var k in allKeys){ var va = setA[k]||0, vb = setB[k]||0; intersection += Math.min(va, vb); union += Math.max(va, vb); }
  return union === 0 ? 0 : intersection / union;
}

/* ── 简易 Markdown → HTML ── */
function md2html(t){
  // 先跑 Markdown → HTML，再统一保护标签后转义纯文本
  t = t.replace(/^### (.+)/gm, '<h3>$1</h3>');
  t = t.replace(/^## (.+)/gm, '<h2>$1</h2>');
  t = t.replace(/^# (.+)/gm, '<h1>$1</h1>');
  t = t.replace(/^> (.+)/gm, '<blockquote>$1</blockquote>');
  t = t.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
  t = t.replace(/\*(.+?)\*/g, '<em>$1</em>');
  t = t.replace(/`([^`]+)`/g, '<code>$1</code>');
  t = t.replace(/^- (.+)/gm, '<li>$1</li>');
  t = t.replace(/(<li>.*<\/li>\s*)+/g, '<ul>$&</ul>');
  t = t.replace(/^---+/gm, '<hr>');
  t = t.replace(/^\|(.+)\|\n\|[-| ]+\|\n((?:\|.+\|\n?)+)/gm, function(m,hdr,rows){
    var h = '<tr>' + hdr.split('|').filter(Boolean).map(function(c){return '<th>'+c.trim()+'</th>'}).join('') + '</tr>';
    var r = rows.trim().split('\n').map(function(rw){
      return '<tr>' + rw.split('|').filter(Boolean).map(function(c){return '<td>'+c.trim()+'</td>'}).join('') + '</tr>';
    }).join('');
    return '<table>'+h+r+'</table>';
  });
  // 保护所有已生成的 HTML 标签（markdown 输出的 + 原文中的）
  var safe = [];
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
  var bubble = btn.closest('.chat-bubble');
  var text = bubble.textContent || bubble.innerText || '';
  navigator.clipboard.writeText(text).then(function(){
    btn.textContent = '已复制';
    setTimeout(function(){ btn.textContent = '复制'; }, 1500);
  }).catch(function(){});
}

/* ── LLM 融合引擎流式加载 ── */
async function streamFusionReport(personality, family, lifeStage, dayMaster){
  var el = document.querySelector('.personality-text');
  if (!el) return;
  var initialText = el.textContent;
  el.innerHTML = '<span class=fusion-placeholder>正在生成融合报告</span><span class=fusion-cursor>|</span>';
  var text = '';

  try{
    var resp = await fetch('/api/personality/fusion/stream', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({personality: personality, family: family || null, life_stage: lifeStage, age_info: dayMaster || null})
    });
    var reader = resp.body.getReader();
    var decoder = new TextDecoder();
    var buf = '';

    while(true){
      var r = await reader.read();
      if (r.done) break;
      buf += decoder.decode(r.value, {stream:true});
      var lines = buf.split('\n');
      buf = lines.pop() || '';
      for (var i = 0; i < lines.length; i++){
        var line = lines[i].trim();
        if (!line.startsWith('data: ')) continue;
        var data = line.slice(6);
        if (data === '[DONE]'){
          el.innerHTML = md2html(text) || initialText;
          return;
        }
        try{
          var chunk = JSON.parse(data);
          if (chunk.token){
            text += chunk.token;
            el.innerHTML = md2html(text) + '<span class=fusion-cursor>|</span>';
          } else if (chunk.done){
            el.innerHTML = md2html(text) || initialText;
            return;
          } else if (chunk.error){
            el.textContent = initialText;
            return;
          }
        }catch(e){}
      }
    }
    el.innerHTML = md2html(text) || initialText;
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
    var msgs = document.getElementById('chatMessages');
    msgs.innerHTML = '<div class=chat-empty><div>AI 功能暂未开放<br><span style=font-size:11px>敬请期待</span></div><div style=margin-top:10px;padding:10px 14px;background:var(--tag-bg);border-radius:8px;font-size:11px;line-height:1.7;text-align:left>💬 <b>收费标准</b><br>· 每日免费 3 次<br>· ⚡体验版 ¥6.9 / 20次<br>· ⭐推荐版 ¥12.9 / 60次<br>· 👑尊享版 ¥19.9 / 永久<br>· 点击 <b>解锁</b> 获取激活码</div></div>';
    return;
  }
  if (!localStorage.getItem('bazi-disclaimer')){
    document.getElementById('disclaimerModal').classList.add('active');
    return;
  }
  if (!CHAT.chartData){ showMsg('请先排盘');return; }
  CHAT.visible = true;
  document.getElementById('chatPanel').classList.add('open');
  document.getElementById('chatOverlay').classList.add('active');
  if (contextLabel) setChatContext(contextLabel);
  loadQuota();
  setTimeout(function(){
    var msgs = document.getElementById('chatMessages');
    msgs.scrollTop = msgs.scrollHeight;
  }, 100);
}
function closeChat(){
  CHAT.visible = false;
  document.getElementById('chatPanel').classList.remove('open');
  document.getElementById('chatOverlay').classList.remove('active');
}
function toggleChat(){ CHAT.visible ? closeChat() : openChat(); }

function setChatContext(label){
  var input = document.getElementById('chatInput');
  input.placeholder = '追问' + label + '…';
  input.dataset.context = label;
}

/* ── 发送消息 ── */
async function sendChat(){
  var input = document.getElementById('chatInput');
  var q = input.value.trim();
  if (!q || CHAT.isStreaming) return;
  // 检查是否与历史问题重复（相似度 > 80% 则提示）
  var dup = null;
  for (var i = 0; i < CHAT.history.length; i++){
    if (CHAT.history[i].role === 'user'){
      var similarity = strSim(q, CHAT.history[i].content);
      if (similarity > 0.8){ dup = CHAT.history[i].content; break; }
    }
  }
  if (dup){
    var confirmed = confirm('⚠ 你之前问过类似问题：「' + dup.substring(0,40) + '…」\n\n是否仍要发送？本次仍会消耗追问次数。');
    if (!confirmed){ input.focus(); return; }
  }
  input.value = ''; input.focus();
  appendBubble(q, 'user');
  appendTyping();

  CHAT.isStreaming = true;
  document.getElementById('chatSendBtn').disabled = true;

  var ctx = input.dataset.context || '';
  var fullQ = ctx ? '【关于' + ctx + '】' + q : q;

  try{
    var resp = await fetch('/api/chat', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({
        question: fullQ,
        chart_data: CHAT.chartData,
        activation_code: CHAT.activationCode,
        history: CHAT.history
      })
    });
    removeTyping();
    var bubble = appendBubble('', 'ai');
    var text = '';
    var reader = resp.body.getReader();
    var decoder = new TextDecoder();
    var buf = '';

    while(true){
      var r = await reader.read();
      if (r.done) break;
      buf += decoder.decode(r.value, {stream:true});
      var lines = buf.split('\n');
      buf = lines.pop() || '';
      for (var i = 0; i < lines.length; i++){
        var line = lines[i].trim();
        if (!line.startsWith('data: ')) continue;
        var data = line.slice(6);
        if (data === '[DONE]'){
          break;
        }
        if (data.startsWith('[ERROR]')){
          text += data.slice(7);
          bubble.innerHTML = md2html(text);
          break;
        }
        try{
          var chunk = JSON.parse(data);
          if (chunk.token){
            text += chunk.token;
            bubble.innerHTML = md2html(text);
            var msgs = document.getElementById('chatMessages');
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
  var msgs = document.getElementById('chatMessages');
  var div = document.createElement('div');
  div.className = 'chat-bubble ' + role;
  var inner = role === 'ai' ? (text ? md2html(text) : '') : esc(text);
  div.innerHTML = inner;
  if (role === 'ai' && text){
    var actions = document.createElement('div');
    actions.className = 'bubble-actions';
    actions.innerHTML = '<button onclick=copyBubble(this)>复制</button>';
    div.appendChild(actions);
  }
  msgs.appendChild(div);
  msgs.scrollTop = msgs.scrollHeight;
  return div;
}
function appendTyping(){
  var msgs = document.getElementById('chatMessages');
  var div = document.createElement('div');
  div.className = 'typing-indicator';
  div.innerHTML = '<span></span><span></span><span></span>';
  div.id = 'typingIndicator';
  msgs.appendChild(div);
  msgs.scrollTop = msgs.scrollHeight;
}
function removeTyping(){
  var el = document.getElementById('typingIndicator');
  if (el) el.remove();
}
function showMsg(msg){
  var msgs = document.getElementById('chatMessages');
  var div = document.createElement('div');
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
  var badge = document.getElementById('quotaBadge');
  try{
    var url = '/api/chat/quota';
    if (CHAT.activationCode) url += '?code=' + CHAT.activationCode;
    var r = await fetch(url);
    var d = await r.json();
    if (d.has_code){
      badge.textContent = '激活码剩余' + d.remaining + '次';
    } else {
      badge.textContent = '今日免费' + d.remaining + '次';
    }
  }catch(e){ badge.textContent = ''; }
}

/* ── 激活码 ── */
function openPayModal(){
  var m = document.getElementById('payModal');
  m.classList.add('active');
  m.style.display = 'flex';
}
function closePayModal(){
  var m = document.getElementById('payModal');
  m.classList.remove('active');
  m.style.display = '';
}
function submitActivationCode(){
  var code = document.getElementById('actCodeInput').value.trim().toUpperCase();
  var status = document.getElementById('actCodeStatus');
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
  var autoUrl = location.protocol + '//' + location.host;
  document.getElementById('apiUrl').value = autoUrl;
  var saved = localStorage.getItem('bazi-act-code');
  if (saved){ CHAT.activationCode = saved; }
  // 检测 AI 功能可用性
  fetch(autoUrl + '/api/health').then(function(r){return r.json()}).then(function(d){
    CHAT.enabled = d.ai_enabled === true;
  }).catch(function(){});
});
