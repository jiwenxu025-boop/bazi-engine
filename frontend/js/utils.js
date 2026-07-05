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

