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
  if (!CHAT.chartData){ showMsg('请先排盘');return; }
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

function setChatContext(label){
  let input = document.getElementById('chatInput');
  input.placeholder = '追问' + label + '…';
  input.dataset.context = label;
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
        chart_data: CHAT.chartData,
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
