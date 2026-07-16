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
