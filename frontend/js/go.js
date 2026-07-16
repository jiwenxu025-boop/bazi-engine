async function go(){
  let btn = document.getElementById('submitBtn');
  btn.disabled = true; btn.textContent = '计算中...';
  let r = document.getElementById('result');
  r.className = 'result visible';
  r.innerHTML = '<div class=loading-state><div class=spinner></div><div>计算中&#x2026;</div></div>';
  document.getElementById('copyBtn').style.display = 'none';

  let api = document.getElementById('apiUrl').value.replace(/\/$/, '');
  let params = new URLSearchParams({
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
  let fl = document.getElementById('familyLevel').value;
  if (fl) params.set('family_level', fl);
  let fj = document.getElementById('fatherJob').value.trim();
  if (fj) params.set('father_job', fj);
  let mj = document.getElementById('motherJob').value.trim();
  if (mj) params.set('mother_job', mj);
  let lsOverride = sessionStorage.getItem('bazi-life-stage');
  if (lsOverride) params.set('life_stage', lsOverride);

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
            d = msg.chart;
            render(d);
            setTimeout(function(){
              r.scrollIntoView({behavior: 'smooth', block: 'start'});
            }, 80);
          } else if (msg.phase === 'llm_result'){
            // 2. LLM审查某年完成，合并信号到对应年份
            if (d && d.annual_scans){
              for (let si = 0; si < d.annual_scans.length; si++){
                if (d.annual_scans[si].year === msg.year){
                  for (let sj = 0; sj < msg.signals.length; sj++){
                    d.annual_scans[si].events.push(msg.signals[sj]);
                  }
                  break;
                }
              }
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
            if (personalityEl){
              personalityEl.innerHTML = '<div class=dayun-error>⚠ 性格分析融合失败：' + (msg.message || '未知错误') + '</div>';
            }
          } else if (msg.phase === 'dayun_done'){
            // 5. 大运解读完成——更新DOM
            if (msg.interpretations && msg.interpretations.length){
              d.dayun.interpretations = msg.interpretations;
              let dyEl = document.querySelector('.dayun-interpretations');
              if (dyEl) dyEl.innerHTML = _buildDayunInterpretations(d);
            }
          } else if (msg.phase === 'dayun_error'){
            // 5b. 大运解读失败——显示原因
            let dyEl2 = document.querySelector('.dayun-interpretations');
            if (dyEl2) dyEl2.innerHTML = '<div class=dayun-error>⚠ 大运解读暂不可用：' + (msg.message || '未知错误') + '</div>';
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
  btn.disabled = false; btn.textContent = '排盘';
}

/* ==========================================
   Term definitions
   ========================================== */
