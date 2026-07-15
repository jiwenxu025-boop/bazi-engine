"""Frontend personality report behavior tests."""

from __future__ import annotations

import json
import subprocess
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
APP_JS = ROOT / "frontend" / "app.js"
INDEX_HTML = ROOT / "frontend" / "index.html"


def run_node(script: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["node", "-e", script],
        cwd=ROOT,
        text=True,
        capture_output=True,
        encoding="utf-8",
        check=False,
    )


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
        }}

        const elements = {{
          themeToggle: new Element('themeToggle'),
          apiUrl: new Element('apiUrl'),
          formCard: new Element('formCard'),
          submitBtn: new Element('submitBtn'),
        }};
        const sandbox = {{
          console,
          setTimeout,
          clearTimeout,
          localStorage: {{ getItem() {{ return null; }}, setItem() {{}} }},
          sessionStorage: {{ getItem() {{ return null; }}, setItem() {{}} }},
          window: {{
            matchMedia() {{ return {{ matches: false }}; }},
            location: {{ origin: 'http://example.test' }},
            addEventListener() {{}},
          }},
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

        const payload = {payload};
        process.stdout.write(sandbox._buildGenderLuckSection(payload));
        """
    )

    result = run_node(script)

    assert result.returncode == 0, result.stderr or result.stdout
    return result.stdout


def test_gender_luck_section_renders_backend_facts_for_male_and_female():
    male_html = render_gender_luck_section(
        {
            "gender": "男",
            "dayun": {
                "direction": "逆排",
                "jiao_yun": {
                    "reference": "上一节",
                    "years": 6,
                    "months": 4,
                    "days": 0,
                    "hours": 8,
                    "formula": "三天折一岁，余一天折四个月",
                },
                "periods": [{"stem": "丁", "branch": "未", "age": "6-15岁"}],
            },
            "xiaoyun": {
                "periods": [{"stem": "己", "branch": "酉", "age": "1岁"}],
            },
            "kinship": {
                "spouse": {"label": "妻星", "stars": ["正财", "偏财"]},
                "child": {"label": "子女星", "stars": ["正官", "七杀"]},
            },
            "spirits": [{"name": "孤辰", "category": "凶神"}],
            "spirit_score": {"unfavorable": -2},
        }
    )

    for expected in (
        "男命 · 逆排",
        "上一节 · 6岁4个月8小时",
        "丁未",
        "己酉",
        "妻星",
        "正财 / 偏财",
        "孤辰",
    ):
        assert expected in male_html

    female_html = render_gender_luck_section(
        {
            "gender": "女",
            "dayun": {
                "direction": "顺排",
                "jiao_yun": {
                    "reference": "下一节",
                    "years": 6,
                    "months": 4,
                    "days": 0,
                    "hours": 8,
                    "formula": "三天折一岁，余一天折四个月",
                },
                "periods": [{"stem": "辛", "branch": "亥", "age": "6-15岁"}],
            },
            "xiaoyun": {
                "periods": [{"stem": "壬", "branch": "子", "age": "1岁"}],
            },
            "kinship": {
                "spouse": {"label": "夫星", "stars": ["正官", "七杀"]},
                "child": {"label": "子女星", "stars": ["食神", "伤官"]},
            },
            "spirits": [{"name": "寡宿", "category": "凶神"}],
            "spirit_score": {"unfavorable": -3},
        }
    )

    for expected in (
        "女命 · 顺排",
        "下一节 · 6岁4个月8小时",
        "辛亥",
        "夫星",
        "正官 / 七杀",
        "寡宿",
    ):
        assert expected in female_html


def test_gender_luck_section_escapes_dynamic_text_and_hides_without_data():
    escaped_html = render_gender_luck_section(
        {
            "gender": "女",
            "kinship": {
                "spouse": {"label": "<夫星>", "stars": ["正官", "七杀"]},
            },
        }
    )

    assert "&lt;夫星&gt;" in escaped_html
    assert "<夫星>" not in escaped_html
    assert render_gender_luck_section({"gender": "男"}) == ""


def test_personality_fusion_error_switches_to_raw_and_toggle_can_return():
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
            this.title = '';
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
          personalityBody: new Element('personalityBody'),
          personalityRaw: new Element('personalityRaw'),
          toggleBtn: new Element('toggleBtn'),
        }};
        elements.personalityRaw.style.display = 'none';
        elements.personalityBody.style.display = 'block';

        const sandbox = {{
          console,
          setTimeout,
          clearTimeout,
          localStorage: {{ getItem() {{ return null; }}, setItem() {{}} }},
          sessionStorage: {{ getItem() {{ return null; }}, setItem() {{}} }},
          window: {{
            matchMedia() {{ return {{ matches: false }}; }},
            location: {{ origin: 'http://example.test' }},
            addEventListener() {{}},
          }},
          document: {{
            documentElement: elements.themeToggle,
            addEventListener() {{}},
            getElementById(id) {{ return elements[id] || new Element(id); }},
            querySelector(selector) {{
              if (selector === '.toggle-btn') return elements.toggleBtn;
              if (selector === '.personality-text') return new Element('personalityText');
              return null;
            }},
            querySelectorAll() {{ return []; }},
          }},
          navigator: {{ clipboard: {{ writeText() {{ return Promise.resolve(); }} }} }},
        }};
        sandbox.globalThis = sandbox;

        vm.createContext(sandbox);
        vm.runInContext(fs.readFileSync({str(APP_JS)!r}, 'utf8'), sandbox);

        sandbox.showPersonalityRawFallback('api failed');
        if (elements.personalityRaw.style.display !== 'block') {{
          throw new Error('raw panel was not shown after fusion failure');
        }}
        if (elements.personalityBody.style.display !== 'none') {{
          throw new Error('fusion panel was not hidden after fusion failure');
        }}
        if (elements.toggleBtn.dataset.personalityMode !== 'raw') {{
          throw new Error('toggle mode was not marked raw after fusion failure');
        }}

        sandbox.togglePersonalityMode();
        if (elements.personalityRaw.style.display !== 'none') {{
          throw new Error('raw panel was not hidden after manual toggle');
        }}
        if (elements.personalityBody.style.display !== 'block') {{
          throw new Error('fusion panel was not restored after manual toggle');
        }}
        if (elements.toggleBtn.dataset.personalityMode !== 'fusion') {{
          throw new Error('toggle mode was not marked fusion after manual toggle');
        }}
        """
    )

    result = run_node(script)

    assert result.returncode == 0, result.stderr or result.stdout


def test_report_overview_summarizes_chart_for_reading_first_result_page():
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
            this.title = '';
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
          setTimeout,
          clearTimeout,
          localStorage: {{ getItem() {{ return null; }}, setItem() {{}} }},
          sessionStorage: {{ getItem() {{ return null; }}, setItem() {{}} }},
          window: {{
            matchMedia() {{ return {{ matches: false }}; }},
            location: {{ origin: 'http://example.test' }},
            addEventListener() {{}},
          }},
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

        const html = sandbox._buildReportOverview({{
          day_master: {{ stem: '甲', wuxing: '木', yinyang: '阳' }},
          pattern: '正官格',
          yongshen: {{ strength: '身弱', favorable_wuxing: ['水', '木'] }},
          life_stage: '职场',
          annual_scans: [
            {{ year: 2026, events: [{{ category: '事业', strength: 3 }}, {{ category: '财运', strength: 2 }}] }},
            {{ year: 2027, events: [{{ category: '感情', strength: 3 }}] }}
          ]
        }});

        if (!html.includes('命盘总览')) throw new Error('overview title missing');
        if (!html.includes('甲木')) throw new Error('day master summary missing');
        if (!html.includes('正官格')) throw new Error('pattern summary missing');
        if (!html.includes('身弱')) throw new Error('strength summary missing');
        if (!html.includes('职场')) throw new Error('life stage summary missing');
        if (!html.includes('事业')) throw new Error('future focus summary missing');
        """
    )

    result = run_node(script)

    assert result.returncode == 0, result.stderr or result.stdout


def test_home_form_keeps_advanced_options_collapsed_and_uses_report_cta():
    html = INDEX_HTML.read_text(encoding="utf-8")

    assert "<title>八字解读</title>" in html
    assert "<h1>八字解读</h1>" in html
    assert "填写出生信息" in html
    assert "生成命盘" in html
    assert "阅读报告" in html
    assert 'class="advanced-options"' in html
    assert "流年范围" in html
    assert html.index('class="advanced-options"') < html.index("流年范围")
    assert 'id="submitBtn">生成解读</button>' in html


def test_mobile_report_action_bar_contains_primary_reader_actions():
    html = INDEX_HTML.read_text(encoding="utf-8")

    assert 'id="reportActions"' in html
    assert "openChat('报告')" in html
    assert "copyBtn" in html
    assert "scrollTo({top:0" in html


def test_chart_params_use_default_flow_range_without_empty_optional_numbers():
    script = textwrap.dedent(
        f"""
        const fs = require('fs');
        const vm = require('vm');

        class Element {{
          constructor(id, value) {{
            this.id = id;
            this.value = value || '';
            this.checked = false;
            this.style = {{}};
            this.dataset = {{}};
            this.classList = {{ add() {{}}, remove() {{}}, toggle() {{}}, contains() {{ return false; }} }};
            this.textContent = '';
            this.title = '';
          }}
          addEventListener() {{}}
          insertAdjacentHTML() {{}}
        }}

        const elements = {{
          themeToggle: new Element('themeToggle'),
          apiUrl: new Element('apiUrl'),
          formCard: new Element('formCard'),
          submitBtn: new Element('submitBtn'),
          name: new Element('name', ''),
          gender: new Element('gender', '男'),
          year: new Element('year', '2000'),
          month: new Element('month', '1'),
          day: new Element('day', '1'),
          hour: new Element('hour', ''),
          lnFrom: new Element('lnFrom', ''),
          lnTo: new Element('lnTo', ''),
          hourConfirmed: new Element('hourConfirmed'),
          familyLevel: new Element('familyLevel', ''),
          fatherJob: new Element('fatherJob', ''),
          motherJob: new Element('motherJob', ''),
        }};
        const sandbox = {{
          console,
          URLSearchParams,
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

        const params = sandbox._buildChartParams();
        const currentYear = String(new Date().getFullYear());
        if (params.get('liunian_from') !== currentYear) throw new Error('default liunian_from missing');
        if (params.get('liunian_to') !== String(Number(currentYear) + 5)) throw new Error('default liunian_to missing');
        if (params.get('hour') !== '12') throw new Error('blank hour should fall back to 12');
        if (params.get('name') !== '未知') throw new Error('blank name should use default');
        """
    )

    result = run_node(script)

    assert result.returncode == 0, result.stderr or result.stdout


def test_report_navigation_exposes_main_reading_sections():
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
            this.title = '';
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

        const html = sandbox._buildReportNav({{
          personality: {{ profile: 'x' }},
          annual_scans: [{{ year: 2026, events: [{{ category: '事业', strength: 3 }}] }}]
        }});
        if (!html.includes('href="#section-personality"')) throw new Error('personality nav missing');
        if (!html.includes('href="#section-focus"')) throw new Error('focus nav missing');
        if (!html.includes('href="#section-dayun"')) throw new Error('dayun nav missing');
        if (!html.includes('href="#section-flow"')) throw new Error('flow nav missing');
        if (!html.includes('href="#section-foundation"')) throw new Error('foundation nav missing');
        if (!html.includes('原始依据')) throw new Error('foundation label missing');
        if (!html.includes('报告导航')) throw new Error('nav label missing');
        """
    )

    result = run_node(script)

    assert result.returncode == 0, result.stderr or result.stdout


def test_foundation_rules_are_rendered_as_expandable_evidence():
    js = APP_JS.read_text(encoding="utf-8")

    assert "class=evidence-details" in js
    assert "查看原始命盘与规则依据" in js


def test_report_text_marks_rule_facts_and_ai_explanations_boundary():
    js = APP_JS.read_text(encoding="utf-8")

    assert "规则事实" in js
    assert "AI 解读" in js
    assert "若冲突以规则事实为准" in js


def test_chat_context_fact_hint_has_visible_active_style():
    css = (ROOT / "frontend" / "style.css").read_text(encoding="utf-8")

    assert ".chat-context-hint.active" in css
    assert "overflow-wrap:anywhere" in css


def test_report_focus_sections_reuse_existing_signals_without_new_rules():
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
            this.title = '';
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
          setTimeout,
          clearTimeout,
          Date,
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

        const chart = {{
          life_stage: '职场',
          annual_scans: [
            {{ year: new Date().getFullYear(), liunian: '丙午', age: 26, dayun: '丁未', events: [
              {{ category: '事业', direction: '正面', strength: 3 }},
              {{ category: '财运', direction: '负面', strength: 2 }},
              {{ category: '人际', direction: '正面', strength: 2 }}
            ] }}
          ],
          dayun: {{
            periods: [{{ stem: '丁', branch: '未', age: '26-35岁' }}],
            modulations: [{{ dayun_stem: '丁', dayun_branch: '未', age_range: '26-35岁', theme: '财运', baseline_offset: 1, branch_interactions: ['与原局亥半合木'] }}],
            interpretations: []
          }}
        }};
        const html = sandbox._buildReportFocusSections(chart);
        if (!html.includes('id=section-focus')) throw new Error('focus section missing');
        if (!html.includes('事业、财运')) throw new Error('work signals missing');
        if (!html.includes('人际')) throw new Error('relation signals missing');
        if (!html.includes('id=section-dayun')) throw new Error('dayun section missing');
        if (!html.includes('丁未')) throw new Error('current dayun missing');
        if (!html.includes('基调偏顺')) throw new Error('dayun offset missing');

        const summary = sandbox._summarizeAnnualScan(chart.annual_scans[0], chart).join('、');
        if (!summary.includes('事业有进')) throw new Error('annual summary missing career line');
        if (!summary.includes('注意财务')) throw new Error('annual summary missing wealth line');
        """
    )

    result = run_node(script)

    assert result.returncode == 0, result.stderr or result.stdout


def test_report_focus_sections_prefer_backend_current_context():
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
            this.title = '';
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
          setTimeout,
          clearTimeout,
          Date,
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

        const chart = {{
          life_stage: '大学',
          current_context: {{
            current_date: '2026-07-14',
            solar_age: 18,
            liunian_age: 19,
            life_stage: '大学',
            current_dayun: {{ ganzhi: '丙午', age_range: '16-25岁' }},
            current_liunian: {{
              year: 2026,
              age: 19,
              ganzhi: '丙午',
              dayun: '丙午',
              key_events: [
                {{ category: '学业', direction: '正面', strength: 3, marks: '★★★' }},
                {{ category: '财运', direction: '正面', strength: 2, marks: '★★' }}
              ]
            }}
          }},
          annual_scans: [
            {{ year: 2026, liunian: '丙午', age: 19, dayun: '甲辰', events: [
              {{ category: '状态', direction: '负面', strength: 2 }}
            ] }}
          ],
          dayun: {{
            periods: [{{ stem: '甲', branch: '辰', age: '36-45岁' }}],
            modulations: [],
            interpretations: []
          }}
        }};

        const html = sandbox._buildReportFocusSections(chart);
        if (!html.includes('丙午')) throw new Error('backend current dayun missing');
        if (!html.includes('16-25岁')) throw new Error('backend current dayun age range missing');
        if (!html.includes('周岁18')) throw new Error('solar age note missing');
        if (!html.includes('流年19')) throw new Error('liunian age note missing');
        if (!html.includes('2026年 丙午')) throw new Error('backend current liunian missing');
        if (html.includes('甲辰</b>')) throw new Error('frontend used stale dayun instead of current_context');
        """
    )

    result = run_node(script)

    assert result.returncode == 0, result.stderr or result.stdout


def test_module_prompt_chips_fill_chat_with_contextual_question():
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
            this.placeholder = '';
          }}
          addEventListener() {{}}
          focus() {{ this.focused = true; }}
          insertAdjacentHTML() {{}}
        }}

        const elements = {{
          themeToggle: new Element('themeToggle'),
          apiUrl: new Element('apiUrl'),
          formCard: new Element('formCard'),
          submitBtn: new Element('submitBtn'),
          chatInput: new Element('chatInput'),
          chatContextHint: new Element('chatContextHint'),
          chatPanel: new Element('chatPanel'),
          chatOverlay: new Element('chatOverlay'),
          chatMessages: new Element('chatMessages'),
        }};
        const sandbox = {{
          console,
          setTimeout,
          clearTimeout,
          localStorage: {{ getItem() {{ return '1'; }}, setItem() {{}} }},
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

        const chips = sandbox._buildModulePrompts('流年', ['未来三年重点注意哪一年？']);
        if (!chips.includes('module-prompts')) throw new Error('prompt chip wrapper missing');
        if (!chips.includes('askModuleQuestion')) throw new Error('prompt action missing');

        sandbox.setChartData({{
          current_context: {{
            solar_age: 18,
            liunian_age: 19,
            current_dayun: {{ ganzhi: '丙午', age_range: '16-25岁' }},
            current_liunian: {{ year: 2026, ganzhi: '丙午', dayun: '丙午', age: 19 }}
          }}
        }});
        vm.runInContext("CHAT.enabled = true;", sandbox);
        sandbox.askModuleQuestion('流年', '未来三年重点注意哪一年？');
        if (elements.chatInput.value !== '未来三年重点注意哪一年？') throw new Error('question not filled');
        if (!elements.chatInput.focused) throw new Error('input not focused');
        if (!elements.chatContextHint.textContent.includes('当前上下文：流年')) throw new Error('context hint missing');
        if (!elements.chatContextHint.textContent.includes('丙午大运')) throw new Error('current dayun hint missing');
        if (!elements.chatContextHint.textContent.includes('16-25岁')) throw new Error('current dayun age range hint missing');
        if (!elements.chatContextHint.textContent.includes('2026年丙午流年')) throw new Error('current liunian hint missing');
        if (!elements.chatContextHint.textContent.includes('周岁18')) throw new Error('solar age hint missing');
        if (!elements.chatContextHint.textContent.includes('流年19')) throw new Error('liunian age hint missing');

        vm.runInContext("CHAT.enabled = false;", sandbox);
        sandbox.askModuleQuestion('命盘', '这个格局现实里意味着什么？');
        if (!elements.chatContextHint.textContent.includes('当前上下文：命盘')) throw new Error('disabled chat context hint missing');
        """
    )

    result = run_node(script)

    assert result.returncode == 0, result.stderr or result.stdout


def test_app_state_keeps_chart_context_for_chat_calendar_and_stream_merges():
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
            this.title = '';
            this.value = '';
          }}
          addEventListener() {{}}
          appendChild() {{}}
          insertAdjacentHTML() {{}}
          remove() {{}}
        }}

        const elements = {{
          themeToggle: new Element('themeToggle'),
          apiUrl: new Element('apiUrl'),
          formCard: new Element('formCard'),
          submitBtn: new Element('submitBtn'),
        }};
        elements.apiUrl.value = 'http://example.test';

        const fetchBodies = [];
        const sandbox = {{
          console,
          setTimeout,
          clearTimeout,
          Date,
          localStorage: {{ getItem() {{ return null; }}, setItem() {{}} }},
          sessionStorage: {{ getItem() {{ return null; }}, setItem() {{}} }},
          window: {{
            matchMedia() {{ return {{ matches: false }}; }},
            location: {{ origin: 'http://example.test' }},
            addEventListener() {{}},
          }},
          document: {{
            documentElement: elements.themeToggle,
            addEventListener() {{}},
            getElementById(id) {{ return elements[id] || new Element(id); }},
            querySelector() {{ return null; }},
            querySelectorAll() {{ return []; }},
          }},
          navigator: {{ clipboard: {{ writeText() {{ return Promise.resolve(); }} }} }},
          fetch(url, options) {{
            fetchBodies.push(JSON.parse(options.body));
            return Promise.resolve({{ json() {{ return Promise.resolve({{ results: [] }}); }} }});
          }},
        }};
        sandbox.globalThis = sandbox;
        vm.createContext(sandbox);
        vm.runInContext(fs.readFileSync({str(APP_JS)!r}, 'utf8'), sandbox);

        const chart = {{
          id: 'fresh-chart',
          current_context: {{ current_dayun: {{ ganzhi: 'bingwu' }} }},
          annual_scans: [{{ year: 2026, events: [{{ category: 'base', strength: 2 }}] }}],
          dayun: {{ interpretations: [] }}
        }};

        sandbox.setChartData(chart);
        if (sandbox.getChartData() !== chart) throw new Error('getChartData did not return the active chart');
        if (sandbox.getCurrentContext() !== chart.current_context) throw new Error('current_context was not cached');
        if (!vm.runInContext('CHAT.chartData === getChartData()', sandbox)) throw new Error('legacy chat chart was not synchronized');
        if (sandbox.window._calChart !== chart) throw new Error('legacy calendar chart was not synchronized');

        sandbox.mergeAnnualSignals(2026, [{{ category: 'stream', strength: 3 }}]);
        if (chart.current_context.current_dayun.ganzhi !== 'bingwu') throw new Error('current_context changed during annual merge');
        if (chart.annual_scans[0].events.length !== 2) throw new Error('annual stream signal was not merged');

        sandbox.setDayunInterpretations([{{ index: 0, text: 'ok' }}]);
        if (chart.current_context.current_dayun.ganzhi !== 'bingwu') throw new Error('current_context changed during dayun merge');
        if (chart.dayun.interpretations[0].text !== 'ok') throw new Error('dayun interpretations were not stored');

        sandbox.window._calChart = {{ id: 'stale-calendar-chart' }};
        sandbox._loadCalendarMarks(2026, 7);
        await Promise.resolve();
        await Promise.resolve();
        if (fetchBodies[0].chart.id !== 'fresh-chart') throw new Error('calendar did not use AppState chart');
        """
    )

    result = run_node(f"(async () => {{ {script} }})().catch(e => {{ console.error(e.stack || e); process.exit(1); }});")

    assert result.returncode == 0, result.stderr or result.stdout


def test_chat_payload_uses_app_state_chart_instead_of_stale_legacy_field():
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
            this.innerHTML = '';
            this.value = '';
            this.disabled = false;
            this.scrollTop = 0;
            this.scrollHeight = 0;
            this.children = [];
          }}
          addEventListener() {{}}
          appendChild(el) {{ this.children.push(el); }}
          focus() {{ this.focused = true; }}
          insertAdjacentHTML() {{}}
          remove() {{}}
        }}

        const elements = {{
          themeToggle: new Element('themeToggle'),
          apiUrl: new Element('apiUrl'),
          formCard: new Element('formCard'),
          submitBtn: new Element('submitBtn'),
          chatInput: new Element('chatInput'),
          chatMessages: new Element('chatMessages'),
          chatSendBtn: new Element('chatSendBtn'),
          quotaBadge: new Element('quotaBadge'),
          copyBtn: new Element('copyBtn'),
          result: new Element('result'),
          backTop: new Element('backTop'),
        }};
        elements.chatInput.value = 'question';

        const fetchBodies = [];
        const sandbox = {{
          console,
          setTimeout,
          clearTimeout,
          confirm() {{ return true; }},
          localStorage: {{ getItem() {{ return '1'; }}, setItem() {{}} }},
          sessionStorage: {{ getItem() {{ return null; }}, setItem() {{}} }},
          window: {{
            matchMedia() {{ return {{ matches: false }}; }},
            location: {{ origin: 'http://example.test' }},
            addEventListener() {{}},
          }},
          document: {{
            documentElement: elements.themeToggle,
            addEventListener() {{}},
            createElement(id) {{ return new Element(id); }},
            getElementById(id) {{ return elements[id] || new Element(id); }},
            querySelector() {{ return null; }},
            querySelectorAll() {{ return []; }},
          }},
          navigator: {{ clipboard: {{ writeText() {{ return Promise.resolve(); }} }} }},
          fetch(url, options) {{
            if (options && options.body) fetchBodies.push(JSON.parse(options.body));
            return Promise.resolve({{
              json() {{ return Promise.resolve({{ has_code: false, remaining: 3 }}); }},
              body: {{ getReader() {{ return {{ read() {{ return Promise.resolve({{ done: true }}); }} }}; }} }}
            }});
          }},
        }};
        sandbox.globalThis = sandbox;
        vm.createContext(sandbox);
        vm.runInContext(fs.readFileSync({str(APP_JS)!r}, 'utf8'), sandbox);

        sandbox.setChartData({{ id: 'fresh-chart', current_context: {{ solar_age: 18 }} }});
        vm.runInContext("CHAT.chartData = {{id: 'stale-chart'}}; CHAT.enabled = true;", sandbox);
        await sandbox.sendChat();

        if (!fetchBodies.length) throw new Error('chat request was not sent');
        if (fetchBodies[0].chart_data.id !== 'fresh-chart') throw new Error('chat did not use AppState chart');
        if (fetchBodies[0].chart_data.current_context.solar_age !== 18) throw new Error('chat payload lost current_context');
        """
    )

    result = run_node(f"(async () => {{ {script} }})().catch(e => {{ console.error(e.stack || e); process.exit(1); }});")

    assert result.returncode == 0, result.stderr or result.stdout
