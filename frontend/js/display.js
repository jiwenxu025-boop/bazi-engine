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

function togglePersonalityMode(){
  let body = document.getElementById('personalityBody');
  let raw = document.getElementById('personalityRaw');
  let btn = document.querySelector('.toggle-btn');
  if (!body || !raw) return;
  if (raw.style.display === 'none'){
    raw.style.display = 'block';
    body.style.display = 'none';
    btn.textContent = '返回融合报告';
  } else {
    raw.style.display = 'none';
    body.style.display = 'block';
    btn.textContent = '查看原始数据';
  }
}

/* ==========================================
   Render
   ========================================== */
function render(d){
  // 存储命盘数据供 AI 追问用
  CHAT.chartData = d;
  let ym = d.four_pillars;
  let labels = {year:'年', month:'月', day:'日', hour:'时'};
  let h = '';

  // Four pillars
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
    h += '<span class=dayun-tag>' + p.stem + p.branch + ' <span style="color:var(--text-tertiary)">' + p.age + '岁</span></span>';
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
  let fusionReady = d.personality && d.personality._fusion_ready;
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

    // ── 融合/原始切换 ──
    if (fusionReady){
      h += '<div class=personality-toggle><button class=toggle-btn onclick="togglePersonalityMode()" title="查看规则引擎原始数据">查看原始数据</button></div>';
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
  h += _buildCalendar(d);

  // Flow years
  if (d.annual_scans && d.annual_scans.length){
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

      let cats2 = significant.map(function(e){return e.category});
      let dirs2 = significant.map(function(e){return e.direction});
      let summary = [];
      // 获取当前人生阶段（优先用用户手动切换的）
      let curStage = sessionStorage.getItem('bazi-life-stage') || d.life_stage || '职场';
      let isStudent = curStage === '中学' || curStage === '大学' || curStage === '深造';
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
  }

  // 时辰未确认警告
  if (d.warnings && d.warnings.length){
    h += '<div style="background:var(--error-bg);border:1px solid var(--gold);border-radius:8px;padding:12px 16px;margin-bottom:16px;font-size:13px;color:var(--gold);line-height:1.7">';
    for (let wi = 0; wi < d.warnings.length; wi++){
      h += esc(d.warnings[wi]) + '<br>';
    }
    h += '</div>';
  }

  document.getElementById('result').innerHTML = h;
  document.getElementById('copyBtn').style.display = 'inline-block';

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
