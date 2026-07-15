# Gender Differences Frontend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a report section that presents backend-computed gender-specific luck direction, jiaoyun, xiaoyun, kinship, and sensitive spirit weighting.

**Architecture:** Keep all Bazi calculations in the backend. Add one guarded HTML builder in the existing frontend report pipeline, reuse it for conditional navigation, and style it as a single un-nested report panel that follows the current responsive design.

**Tech Stack:** Vanilla JavaScript, CSS, Python pytest with Node VM tests, FastAPI/Uvicorn, temporary Playwright browser QA.

---

## File Map

- Modify `frontend/app.js`: add the gender-luck data guard, formatter, section builder, report navigation entry, and render integration.
- Modify `frontend/style.css`: add section order and responsive styles using existing CSS variables.
- Modify `frontend/index.html`: update the `app.js` cache-busting query.
- Modify `scripts/tests/test_frontend_personality_ui.py`: cover male/female rendering, escaping, missing-data fallback, navigation, styles, and cache busting.
- Do not modify `frontend/js/display.js` or `frontend/app.js.bak`; `frontend/index.html` loads `frontend/app.js` directly.

### Task 1: Build the guarded gender-luck renderer

**Files:**
- Modify: `scripts/tests/test_frontend_personality_ui.py`
- Modify: `frontend/app.js`

- [ ] **Step 1: Add a focused Node VM rendering helper to the test module**

Add `import json` and this helper after `run_node()`:

```python
def render_gender_luck_section(chart: dict) -> str:
    payload = json.dumps(chart, ensure_ascii=False)
    script = textwrap.dedent(
        f"""
        const fs = require('fs');
        const vm = require('vm');

        class Element {{
          constructor(id) {{
            this.id = id;
            this.style = {{}};
            this.dataset = {{}};
            this.classList = {{ add() {{}}, remove() {{}}, toggle() {{}}, contains() {{ return false; }} }};
            this.textContent = '';
            this.value = '';
          }}
          addEventListener() {{}}
          insertAdjacentHTML() {{}}
          scrollIntoView() {{}}
        }}

        const elements = {{
          themeToggle: new Element('themeToggle'),
          apiUrl: new Element('apiUrl'),
          formCard: new Element('formCard'),
          submitBtn: new Element('submitBtn'),
        }};
        const sandbox = {{
          console,
          Date,
          setTimeout,
          clearTimeout,
          localStorage: {{ getItem() {{ return null; }}, setItem() {{}} }},
          sessionStorage: {{ getItem() {{ return null; }}, setItem() {{}} }},
          window: {{ matchMedia() {{ return {{ matches: false }}; }}, location: {{ origin: 'http://example.test' }}, addEventListener() {{}} }},
          document: {{
            documentElement: elements.themeToggle,
            addEventListener() {{}},
            getElementById(id) {{ return elements[id] || new Element(id); }},
            querySelector() {{ return null; }},
            querySelectorAll() {{ return []; }},
          }},
          navigator: {{ clipboard: {{ writeText() {{ return Promise.resolve(); }} }} }},
        }};
        sandbox.globalThis = sandbox;
        vm.createContext(sandbox);
        vm.runInContext(fs.readFileSync({str(APP_JS)!r}, 'utf8'), sandbox);
        process.stdout.write(sandbox._buildGenderLuckSection({payload}));
        """
    )
    result = run_node(script)
    assert result.returncode == 0, result.stderr or result.stdout
    return result.stdout
```

- [ ] **Step 2: Add failing male/female, escaping, and missing-data tests**

```python
def test_gender_luck_section_renders_backend_facts_for_male_and_female():
    shared = {
        "dayun": {
            "jiao_yun": {
                "years": 6, "months": 4, "days": 0, "hours": 8,
                "formula": "三天折一岁，余一天折四个月",
            },
            "periods": [{"stem": "丁", "branch": "未", "age": "6-15岁"}],
        },
        "xiaoyun": {"periods": [{"stem": "己", "branch": "酉", "age": "1岁"}]},
        "spirit_score": {"unfavorable": -2},
    }

    male = dict(shared)
    male.update({
        "gender": "男",
        "dayun": {**shared["dayun"], "direction": "逆排", "jiao_yun": {**shared["dayun"]["jiao_yun"], "reference": "上一节"}},
        "kinship": {"spouse": {"label": "妻星", "stars": ["正财", "偏财"]}},
        "spirits": [{"name": "孤辰"}],
    })
    female = dict(shared)
    female.update({
        "gender": "女",
        "dayun": {**shared["dayun"], "direction": "顺排", "jiao_yun": {**shared["dayun"]["jiao_yun"], "reference": "下一节"}},
        "xiaoyun": {"periods": [{"stem": "辛", "branch": "亥", "age": "1岁"}]},
        "kinship": {"spouse": {"label": "夫星", "stars": ["正官", "七杀"]}},
        "spirits": [{"name": "寡宿"}],
    })

    male_html = render_gender_luck_section(male)
    female_html = render_gender_luck_section(female)

    assert "男命 · 逆排" in male_html
    assert "上一节 · 6岁4个月8小时" in male_html
    assert "丁未" in male_html and "己酉" in male_html
    assert "妻星" in male_html and "正财 / 偏财" in male_html
    assert "孤辰" in male_html

    assert "女命 · 顺排" in female_html
    assert "下一节 · 6岁4个月8小时" in female_html
    assert "辛亥" in female_html
    assert "夫星" in female_html and "正官 / 七杀" in female_html
    assert "寡宿" in female_html


def test_gender_luck_section_escapes_dynamic_text_and_hides_without_data():
    html = render_gender_luck_section({
        "gender": "女",
        "kinship": {"spouse": {"label": "<夫星>", "stars": ["正官", "七杀"]}},
    })

    assert "<夫星>" not in html
    assert "&lt;夫星&gt;" in html
    assert render_gender_luck_section({"gender": "女"}) == ""
```

- [ ] **Step 3: Run the new tests and confirm they fail because the builder is absent**

Run:

```powershell
$env:PYTHONPATH='scripts'
python -m pytest scripts/tests/test_frontend_personality_ui.py -k gender_luck_section -q
```

Expected: failure containing `_buildGenderLuckSection is not a function`.

- [ ] **Step 4: Add the minimal data guard, age formatter, and section builder before `_buildReportFocusSections()`**

```javascript
function _hasGenderLuckData(d){
  if (!d) return false;
  let dayun = d.dayun || {};
  let jiaoyun = dayun.jiao_yun || {};
  return !!(
    Object.keys(jiaoyun).length ||
    (d.xiaoyun && d.xiaoyun.periods && d.xiaoyun.periods.length) ||
    (d.kinship && Object.keys(d.kinship).length)
  );
}

function _formatJiaoyunAge(detail){
  let units = [
    ['years', '岁'],
    ['months', '个月'],
    ['days', '天'],
    ['hours', '小时']
  ];
  let parts = [];
  for (let i = 0; i < units.length; i++){
    let value = Number(detail && detail[units[i][0]] || 0);
    if (value > 0) parts.push(value + units[i][1]);
  }
  return parts.length ? parts.join('') : '不足一月';
}

function _buildGenderLuckSection(d){
  if (!_hasGenderLuckData(d)) return '';

  let dayun = d.dayun || {};
  let jiaoyun = dayun.jiao_yun || {};
  let xiaoyun = d.xiaoyun && d.xiaoyun.periods ? d.xiaoyun.periods : [];
  let kinship = d.kinship || {};
  let firstDayun = dayun.periods && dayun.periods.length ? dayun.periods[0] : null;
  let genderLabel = d.gender === '男' ? '男命' : d.gender === '女' ? '女命' : '命盘';
  let headline = [genderLabel, dayun.direction || (d.xiaoyun && d.xiaoyun.direction) || ''].filter(Boolean).join(' · ');
  let firstLabel = firstDayun ? (firstDayun.stem || '') + (firstDayun.branch || '') : '';
  let h = '<section class="report-section gender-luck-section" id=section-gender-luck>';
  h += '<div class=report-section-head><div><span>运势起点与六亲</span><h2>' + esc(headline) + '</h2></div><p>顺逆、交运和六亲均来自排盘规则，前端不重复计算。</p></div>';
  h += '<div class=gender-luck-panel>';
  h += '<div class=gender-luck-summary>';
  h += '<div><span>排运方向</span><b>' + esc(dayun.direction || '待判断') + '</b></div>';
  if (firstLabel) h += '<div><span>首步大运</span><b>' + esc(firstLabel) + '</b></div>';
  if (Object.keys(jiaoyun).length){
    let jiaoyunText = [jiaoyun.reference || '', _formatJiaoyunAge(jiaoyun)].filter(Boolean).join(' · ');
    h += '<div><span>交运</span><b>' + esc(jiaoyunText) + '</b>';
    if (jiaoyun.formula) h += '<small data-tip="' + esc(jiaoyun.formula) + '">' + esc(jiaoyun.formula) + '</small>';
    h += '</div>';
  }
  h += '</div>';

  if (xiaoyun.length){
    h += '<div class=gender-luck-block><span class=gender-luck-label>未交大运前的小运</span><div class=xiaoyun-strip>';
    for (let i = 0; i < xiaoyun.length; i++){
      let item = xiaoyun[i];
      h += '<span class=xiaoyun-chip><b>' + esc((item.stem || '') + (item.branch || '')) + '</b><small>' + esc(item.age || '') + '</small></span>';
    }
    h += '</div></div>';
  }

  let kinshipOrder = ['spouse', 'child', 'father_in_law', 'mother_in_law'];
  let kinshipRows = [];
  for (let i = 0; i < kinshipOrder.length; i++){
    let relation = kinship[kinshipOrder[i]];
    if (relation && relation.label){
      kinshipRows.push('<div class=kinship-row><span>' + esc(relation.label) + '</span><b>' + esc((relation.stars || []).join(' / ')) + '</b></div>');
    }
  }
  if (kinshipRows.length){
    h += '<div class=gender-luck-block><span class=gender-luck-label>六亲十神映射</span><div class=kinship-list>' + kinshipRows.join('') + '</div></div>';
  }

  let spiritNames = (d.spirits || []).map(function(item){return item.name;});
  let sensitiveSpirit = d.gender === '男' ? '孤辰' : d.gender === '女' ? '寡宿' : '';
  if (sensitiveSpirit && spiritNames.indexOf(sensitiveSpirit) !== -1){
    let unfavorable = d.spirit_score && d.spirit_score.unfavorable !== undefined ? ' · 当前负面分 ' + d.spirit_score.unfavorable : '';
    h += '<div class=spirit-gender-note><b>' + esc(sensitiveSpirit) + '</b>：传统规则对此命别的婚姻提示更敏感' + esc(unfavorable) + '</div>';
  }
  h += '</div></section>';
  return h;
}
```

- [ ] **Step 5: Run the focused tests and confirm they pass**

Run:

```powershell
$env:PYTHONPATH='scripts'
python -m pytest scripts/tests/test_frontend_personality_ui.py -k gender_luck_section -q
```

Expected: `2 passed`.

- [ ] **Step 6: Commit the renderer and tests**

```powershell
git add frontend/app.js scripts/tests/test_frontend_personality_ui.py
git commit -m "feat: render gender-specific luck facts"
```

### Task 2: Integrate navigation, report order, and responsive styling

**Files:**
- Modify: `scripts/tests/test_frontend_personality_ui.py`
- Modify: `frontend/app.js`
- Modify: `frontend/style.css`

- [ ] **Step 1: Extend the existing navigation test fixture and assertions**

Add gender-luck data to the chart passed to `_buildReportNav()`:

```javascript
dayun: { jiao_yun: { reference: '下一节', years: 6 } },
kinship: { spouse: { label: '夫星', stars: ['正官', '七杀'] } },
```

Add this assertion next to the existing dayun assertion:

```javascript
if (!html.includes('href="#section-gender-luck"')) throw new Error('gender luck nav missing');
```

- [ ] **Step 2: Add a failing static integration/style test**

```python
def test_gender_luck_section_is_integrated_and_mobile_safe():
    js = APP_JS.read_text(encoding="utf-8")
    css = (ROOT / "frontend" / "style.css").read_text(encoding="utf-8")

    assert "h += _buildGenderLuckSection(d);" in js
    assert "#section-gender-luck{order:6}" in css
    assert ".xiaoyun-strip" in css
    assert "overflow-x:auto" in css
    assert ".kinship-row" in css
    assert ".spirit-gender-note" in css
```

- [ ] **Step 3: Run the navigation and integration tests and confirm failure**

Run:

```powershell
$env:PYTHONPATH='scripts'
python -m pytest scripts/tests/test_frontend_personality_ui.py -k "report_navigation or gender_luck_section_is_integrated" -q
```

Expected: failures for the missing navigation link, render call, and styles.

- [ ] **Step 4: Wire the section into navigation and the report render order**

In `_buildReportNav(d)`, after the current-dayun item:

```javascript
if (_hasGenderLuckData(d)) items.push({id:'section-gender-luck', label:'运势起点'});
```

In `render(d)`, immediately after `_buildReportFocusSections(d)`:

```javascript
h += _buildGenderLuckSection(d);
```

- [ ] **Step 5: Add section order and component styles using existing variables**

Replace the section order block with:

```css
#section-personality{order:3}
#section-focus{order:4}
#section-dayun{order:5}
#section-gender-luck{order:6}
#section-flow{order:7}
#section-calendar{order:8}
#section-foundation{order:9}
.report-warning{order:10}
```

Add these styles after `.dayun-focus-card .dayun-interpretations`:

```css
.gender-luck-panel{
  background:var(--surface);
  border:1px solid var(--border);
  border-left:3px solid var(--gold);
  border-radius:var(--radius);
  box-shadow:var(--shadow-card);
  overflow:hidden;
}
.gender-luck-summary{
  display:grid;
  grid-template-columns:repeat(3,minmax(0,1fr));
}
.gender-luck-summary > div{
  min-width:0;
  padding:14px 16px;
  border-right:1px solid var(--border);
}
.gender-luck-summary > div:last-child{border-right:0}
.gender-luck-summary span,
.gender-luck-label{
  display:block;
  font-size:10px;
  color:var(--text-tertiary);
  margin-bottom:5px;
}
.gender-luck-summary b{
  display:block;
  color:var(--text);
  font-size:14px;
  line-height:1.5;
  overflow-wrap:anywhere;
}
.gender-luck-summary small{
  display:block;
  margin-top:4px;
  color:var(--text-tertiary);
  font-size:10px;
  line-height:1.5;
}
.gender-luck-block{
  padding:13px 16px;
  border-top:1px solid var(--border);
}
.xiaoyun-strip{
  display:flex;
  gap:6px;
  overflow-x:auto;
  padding-bottom:3px;
  scrollbar-width:thin;
}
.xiaoyun-chip{
  flex:0 0 auto;
  display:flex;
  align-items:baseline;
  gap:5px;
  padding:7px 9px;
  background:var(--tag-bg);
  border:1px solid var(--border);
  border-radius:var(--radius-sm);
}
.xiaoyun-chip b{font-size:13px;color:var(--text)}
.xiaoyun-chip small{font-size:10px;color:var(--text-tertiary)}
.kinship-list{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));column-gap:22px}
.kinship-row{
  display:flex;
  justify-content:space-between;
  gap:12px;
  padding:8px 0;
  border-bottom:1px solid color-mix(in srgb,var(--border) 70%,transparent);
}
.kinship-row span{font-size:12px;color:var(--text-secondary)}
.kinship-row b{font-size:12px;color:var(--text);text-align:right;overflow-wrap:anywhere}
.spirit-gender-note{
  margin:0 16px 14px;
  padding:9px 11px;
  border-left:3px solid var(--bad);
  background:color-mix(in srgb,var(--bad) 7%,var(--surface));
  color:var(--text-secondary);
  font-size:12px;
  line-height:1.6;
}
.spirit-gender-note b{color:var(--text)}
```

Inside `@media(max-width:480px)`, add:

```css
  .gender-luck-summary{grid-template-columns:1fr}
  .gender-luck-summary > div{border-right:0;border-bottom:1px solid var(--border);padding:12px 14px}
  .gender-luck-summary > div:last-child{border-bottom:0}
  .gender-luck-block{padding:12px 14px}
  .kinship-list{grid-template-columns:1fr}
  .spirit-gender-note{margin:0 14px 12px}
```

- [ ] **Step 6: Run all frontend behavior tests**

Run:

```powershell
$env:PYTHONPATH='scripts'
python -m pytest scripts/tests/test_frontend_personality_ui.py -q
```

Expected: all tests in the file pass.

- [ ] **Step 7: Commit integration and styles**

```powershell
git add frontend/app.js frontend/style.css scripts/tests/test_frontend_personality_ui.py
git commit -m "feat: integrate gender luck report section"
```

### Task 3: Bust the frontend cache

**Files:**
- Modify: `scripts/tests/test_frontend_personality_ui.py`
- Modify: `frontend/index.html`

- [ ] **Step 1: Add a failing cache-version test**

```python
def test_gender_luck_release_updates_app_cache_version():
    html = INDEX_HTML.read_text(encoding="utf-8")
    assert 'src="app.js?v=20260715"' in html
```

- [ ] **Step 2: Run the test and confirm it fails on the old version**

Run:

```powershell
$env:PYTHONPATH='scripts'
python -m pytest scripts/tests/test_frontend_personality_ui.py -k cache_version -q
```

Expected: failure showing `app.js?v=20260713` is still present.

- [ ] **Step 3: Update the script query in `frontend/index.html`**

```html
<script src="app.js?v=20260715"></script>
```

- [ ] **Step 4: Run the cache-version test and commit**

Run:

```powershell
$env:PYTHONPATH='scripts'
python -m pytest scripts/tests/test_frontend_personality_ui.py -k cache_version -q
git add frontend/index.html scripts/tests/test_frontend_personality_ui.py
git commit -m "chore: refresh frontend asset version"
```

Expected: the test passes and the commit contains only the index and test changes.

### Task 4: Browser verification with real chart requests

**Files:**
- Create temporarily outside the repository: `%TEMP%\bazi-gender-frontend-smoke.cjs`
- Output screenshots outside the repository: `%TEMP%\bazi-gender-frontend-*.png`

- [ ] **Step 1: Start the real API/UI server with AI features disabled**

```powershell
$env:PYTHONPATH='C:\Users\21469\bazi-engine\scripts'
$env:BAZI_LLM_REVIEW='0'
$env:BAZI_AI_ENABLED='0'
$env:BAZI_FUSION_ENGINE='0'
$server = Start-Process -FilePath python -ArgumentList @('-m','uvicorn','bazi_engine.api:app','--host','127.0.0.1','--port','7860') -WorkingDirectory 'C:\Users\21469\bazi-engine\scripts' -WindowStyle Hidden -PassThru
```

Expected: `http://127.0.0.1:7860/api/health` returns `status: ok`.

- [ ] **Step 2: Install Playwright only in a temporary directory**

```powershell
$pw = Join-Path $env:TEMP 'bazi-playwright-runtime'
npm.cmd install --prefix $pw playwright@1.55.0
& "$pw\node_modules\.bin\playwright.cmd" install chromium
$env:PLAYWRIGHT_MODULE = "$pw\node_modules\playwright"
```

Expected: no `package.json`, lockfile, or `node_modules` is created in the repository.

- [ ] **Step 3: Create the temporary smoke script with this complete content**

```javascript
const { chromium } = require(process.env.PLAYWRIGHT_MODULE);

(async () => {
  const browser = await chromium.launch({ headless: true });
  const cases = [
    { gender: '男', year: '1983', month: '6', day: '15', hour: '12', width: 1440, height: 1000, direction: '逆排', spouse: '妻星', xiaoyun: '己巳', spirit: '孤辰', dark: false },
    { gender: '女', year: '2007', month: '8', day: '26', hour: '20', width: 390, height: 844, direction: '顺排', spouse: '夫星', xiaoyun: '辛亥', spirit: '寡宿', dark: true },
  ];

  for (const item of cases) {
    const page = await browser.newPage({ viewport: { width: item.width, height: item.height } });
    const errors = [];
    page.on('console', msg => { if (msg.type() === 'error') errors.push(msg.text()); });
    page.on('pageerror', error => errors.push(error.message));
    if (item.dark) await page.emulateMedia({ colorScheme: 'dark' });
    await page.goto('http://127.0.0.1:7860', { waitUntil: 'networkidle' });
    await page.fill('#name', 'frontend-smoke');
    await page.selectOption('#gender', { label: item.gender });
    await page.fill('#year', item.year);
    await page.fill('#month', item.month);
    await page.fill('#day', item.day);
    await page.fill('#hour', item.hour);
    await page.check('#hourConfirmed');
    await page.click('#submitBtn');
    await page.waitForSelector('#section-gender-luck', { timeout: 60000 });

    const text = await page.locator('#section-gender-luck').innerText();
    for (const expected of [item.direction, item.spouse, item.xiaoyun, item.spirit]) {
      if (!text.includes(expected)) throw new Error(item.gender + ' missing: ' + expected);
    }
    const sectionBox = await page.locator('#section-gender-luck').boundingBox();
    if (!sectionBox || sectionBox.width < 250 || sectionBox.height < 120) throw new Error(item.gender + ' section is blank or collapsed');
    const bodyOverflow = await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth);
    if (bodyOverflow) throw new Error(item.gender + ' page has horizontal overflow');
    if (errors.length) throw new Error(item.gender + ' console errors: ' + errors.join(' | '));

    const output = require('path').join(require('os').tmpdir(), 'bazi-gender-frontend-' + item.gender + '.png');
    await page.screenshot({ path: output, fullPage: true });
    console.log(JSON.stringify({ gender: item.gender, screenshot: output, sectionBox }));
    await page.close();
  }
  await browser.close();
})().catch(error => {
  console.error(error);
  process.exit(1);
});
```

- [ ] **Step 4: Run the browser smoke and inspect both screenshots**

```powershell
node "$env:TEMP\bazi-gender-frontend-smoke.cjs"
```

Expected:
- Desktop male report contains `逆排`, `妻星`, `己巳`, and `孤辰`.
- Mobile dark-mode female report contains `顺排`, `夫星`, `辛亥`, and `寡宿`.
- No page-level horizontal overflow or browser console errors.
- Both screenshots show the section between “当前大运” and “未来流年”.

- [ ] **Step 5: Stop the local server**

```powershell
Stop-Process -Id $server.Id
```

### Task 5: Final regression checks and release-ready diff

**Files:**
- Verify all changed files from Tasks 1-3.

- [ ] **Step 1: Run focused gender and frontend tests**

```powershell
$env:PYTHONPATH='scripts'
python -m pytest scripts/tests/test_gender_differences.py scripts/tests/test_frontend_personality_ui.py -q
```

Expected: all focused tests pass.

- [ ] **Step 2: Run the complete suite and static checks**

```powershell
$env:PYTHONPATH='scripts'
python -m pytest scripts/tests -q
python -m ruff check scripts --statistics
python -m compileall scripts/bazi_engine -q
git diff --check
```

Expected: all commands exit `0`; only the existing FastAPI `StarletteDeprecationWarning` may remain.

- [ ] **Step 3: Confirm scope and commit state**

```powershell
git status --short --branch
git log -5 --oneline
```

Expected: only the planned frontend, test, and documentation commits are ahead of `origin/main`; no generated screenshots, temporary Playwright files, or runtime data are tracked.
