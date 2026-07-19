"""Frontend personality report behavior tests."""

from __future__ import annotations

import json
import re
import subprocess
import textwrap
from html.parser import HTMLParser
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
APP_JS = ROOT / "frontend" / "app.js"
INDEX_HTML = ROOT / "frontend" / "index.html"


def extract_css_block(css: str, selector: str) -> str:
    selector_start = css.index(selector)
    opening_brace = css.index("{", selector_start + len(selector))
    depth = 0
    for index in range(opening_brace, len(css)):
        if css[index] == "{":
            depth += 1
        elif css[index] == "}":
            depth -= 1
            if depth == 0:
                return css[opening_brace + 1 : index]
    raise AssertionError(f"unclosed CSS block for {selector}")


def css_rule_bodies(css: str, selector: str) -> list[str]:
    pattern = re.compile(
        rf"(?m)^[ \t]*{re.escape(selector)}[ \t]*\{{([^{{}}]*)\}}"
    )
    return ["".join(match.group(1).split()) for match in pattern.finditer(css)]


def css_rule_body(css: str, selector: str) -> str:
    bodies = css_rule_bodies(css, selector)
    assert len(bodies) == 1, f"expected one {selector} rule, found {len(bodies)}"
    return bodies[0]


class GenderLuckPanelParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.panel_count = 0
        self.nested_card_classes: list[str] = []
        self.panel_depth = 0
        self.open_tags: list[tuple[str, bool]] = []
        self.structure_errors: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        classes = next(
            (value or "" for name, value in attrs if name == "class"), ""
        ).split()
        inside_panel = self.panel_depth > 0
        is_panel = "gender-luck-panel" in classes
        if is_panel:
            self.panel_count += 1
            self.panel_depth += 1
        elif inside_panel:
            self.nested_card_classes.extend(
                class_name
                for class_name in classes
                if class_name == "card" or class_name.endswith("-card")
            )
        self.open_tags.append((tag, is_panel))

    def handle_startendtag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_endtag(self, tag: str) -> None:
        if not self.open_tags:
            self.structure_errors.append(f"unexpected closing tag: {tag}")
            return
        opening_tag, is_panel = self.open_tags.pop()
        if opening_tag != tag:
            self.structure_errors.append(
                f"mismatched tags: opened {opening_tag}, closed {tag}"
            )
        if is_panel:
            self.panel_depth -= 1

    def assert_balanced(self) -> None:
        assert self.structure_errors == []
        assert self.open_tags == []
        assert self.panel_depth == 0


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
            },
            "xiaoyun": {
                "periods": [{"stem": "辛", "branch": "亥", "age": "1岁"}],
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
    assert '<span class=gender-luck-chip>1岁 · 辛亥</span>' in female_html


def test_gender_luck_section_uses_xiaoyun_direction_fallback():
    html = render_gender_luck_section(
        {
            "gender": "女",
            "xiaoyun": {
                "direction": "顺排",
                "periods": [{"stem": "辛", "branch": "亥", "age": "1岁"}],
            },
        }
    )

    assert "女命 · 顺排" in html
    assert "<span>排运方向</span><b>顺排</b>" in html
    assert '<span class=gender-luck-chip>1岁 · 辛亥</span>' in html


def test_gender_luck_section_normalizes_xiaoyun_chip_text():
    age_only_html = render_gender_luck_section(
        {
            "gender": "女",
            "xiaoyun": {"periods": [{"age": 0}]},
        }
    )

    assert age_only_html == ""

    html = render_gender_luck_section(
        {
            "gender": "女",
            "xiaoyun": {"periods": [{}, {"age": 0}]},
            "kinship": {
                "spouse": {"label": "夫星", "stars": ["正官", "七杀"]},
            },
        }
    )

    assert "gender-luck-xiaoyun" not in html
    assert "gender-luck-chip" not in html
    assert "class=gender-luck-summary>" not in html

    valid_html = render_gender_luck_section(
        {
            "gender": "女",
            "xiaoyun": {
                "periods": [{"stem": "辛", "branch": "亥", "age": "1岁"}],
            },
        }
    )

    assert '<span class=gender-luck-chip>1岁 · 辛亥</span>' in valid_html


def test_gender_luck_xiaoyun_list_is_keyboard_focusable():
    html = render_gender_luck_section(
        {
            "xiaoyun": {
                "periods": [{"stem": "辛", "branch": "亥", "age": "1岁"}],
            },
        }
    )

    assert (
        '<div class=gender-luck-chips tabindex="0" aria-label="小运列表">'
        in html
    )


def test_gender_luck_section_distinguishes_missing_and_zero_jiaoyun_age():
    reference_only_html = render_gender_luck_section(
        {
            "gender": "男",
            "dayun": {"jiao_yun": {"reference": "上一节"}},
        }
    )

    assert "上一节" in reference_only_html
    assert "不足一月" not in reference_only_html

    zero_age_html = render_gender_luck_section(
        {
            "gender": "男",
            "dayun": {
                "jiao_yun": {
                    "years": 0,
                    "months": 0,
                    "days": 0,
                    "hours": 0,
                }
            },
        }
    )

    assert "不足一月" in zero_age_html


def test_gender_luck_section_normalizes_jiaoyun_text_and_escapes_formula():
    whitespace_html = render_gender_luck_section(
        {
            "gender": "女",
            "dayun": {"jiao_yun": {"reference": "  ", "formula": " \t "}},
            "kinship": {
                "spouse": {"label": "夫星", "stars": ["正官"]},
            },
        }
    )

    assert "<span>交运时间</span>" not in whitespace_html

    formula_html = render_gender_luck_section(
        {
            "gender": "男",
            "dayun": {
                "jiao_yun": {
                    "reference": "上一节",
                    "formula": '三天"折一岁',
                }
            },
        }
    )

    assert 'data-tip="三天&quot;折一岁"' in formula_html
    assert "<p>三天&quot;折一岁</p>" in formula_html
    assert '三天"折一岁' not in formula_html


def test_gender_luck_section_omits_whitespace_dayun_and_formula_only_empty_main():
    html = render_gender_luck_section(
        {
            "gender": "女",
            "dayun": {
                "direction": "  ",
                "periods": [{"stem": " ", "branch": "\t", "age": "  "}],
                "jiao_yun": {"formula": '三天"折一岁'},
            },
        }
    )

    assert "<h2>女命</h2>" in html
    assert "女命 ·" not in html
    assert "<span>排运方向</span>" not in html
    assert "<span>首步大运</span>" not in html
    assert "<b" not in html
    assert "三天&quot;折一岁" in html
    assert '三天"折一岁' not in html


def test_gender_luck_section_normalizes_kinship_and_shows_zero_spirit_score():
    html = render_gender_luck_section(
        {
            "gender": "男",
            "kinship": {
                "spouse": {
                    "label": " 妻星 ",
                    "stars": ["", "  ", " 正财 ", None, ""],
                },
            },
            "spirits": [{"name": "孤辰", "category": "凶神"}],
            "spirit_score": {"unfavorable": 0},
        }
    )

    assert "<span>妻星</span><b>正财</b>" in html
    assert " / 正财 / " not in html
    assert "后端不利神煞分：0。" in html


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


def test_personality_fusion_error_discards_partial_report_and_locks_raw_mode():
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
          personalityText: new Element('personalityText'),
        }};
        elements.personalityRaw.style.display = 'none';
        elements.personalityBody.style.display = 'block';
        elements.personalityText.innerHTML = '<p>partial unsafe token</p>';

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
              if (selector === '.personality-text') return elements.personalityText;
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
        if (elements.personalityText.innerHTML !== '' || elements.personalityText.textContent !== '') {{
          throw new Error('partial fusion content was not discarded');
        }}
        if (!elements.toggleBtn.disabled || elements.toggleBtn.style.display !== 'none') {{
          throw new Error('failed fusion toggle was not disabled');
        }}

        sandbox.togglePersonalityMode();
        if (elements.personalityRaw.style.display !== 'block') {{
          throw new Error('raw panel was hidden after failed fusion toggle');
        }}
        if (elements.personalityBody.style.display !== 'none') {{
          throw new Error('failed fusion panel was restored');
        }}
        """
    )

    result = run_node(script)

    assert result.returncode == 0, result.stderr or result.stdout


def test_personality_evidence_renderer_handles_empty_scores_labels_and_escaping():
    script = textwrap.dedent(
        f"""
        const fs = require('fs');
        const vm = require('vm');

        class Element {{
          constructor() {{
            this.style = {{}};
            this.dataset = {{}};
            this.classList = {{ add() {{}}, remove() {{}}, toggle() {{}}, contains() {{ return false; }} }};
            this.textContent = '';
            this.value = '';
          }}
          addEventListener() {{}}
        }}

        const generic = new Element();
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
            documentElement: generic,
            addEventListener() {{}},
            getElementById() {{ return generic; }},
            querySelector() {{ return null; }},
            querySelectorAll() {{ return []; }},
          }},
          navigator: {{ clipboard: {{ writeText() {{ return Promise.resolve(); }} }} }},
        }};
        sandbox.globalThis = sandbox;
        vm.createContext(sandbox);
        vm.runInContext(fs.readFileSync({str(APP_JS)!r}, 'utf8'), sandbox);

        const empty = sandbox._buildPersonalityEvidence({{
          evidence_view: {{}},
          weighted_shishen: {{scores: {{}}}},
        }});
        if (empty !== '') throw new Error('empty legacy scores rendered a false evidence panel');

        const rendered = sandbox._buildPersonalityEvidence({{
          evidence_view: {{
            status: {{strength: '偏强（5.5分）'}},
            score_scale: {{
              thresholds: {{medium: 2, high: 5}},
              relationship_policy: 'candidates_do_not_change_weight',
              parameter_snapshot: {{tougan_weight: 3}},
            }},
            dimension_scale: {{threshold_policy: 'base_thresholds_scaled_by_component_count'}},
            dimensions: {{
              感情: {{signals: [{{
                label: '责任感_官杀',
                display_label: '关系责任',
                kind: 'weighted_score',
                value: 6,
                level: '中等',
                component_count: 2,
              }}]}},
              事业: {{signals: [{{
                label: '技术_创意',
                display_label: '<危险标签>',
                kind: 'relative_score',
                value: 8,
              }}]}},
            }},
          }},
        }});
        if (!rendered.includes('计分口径')) throw new Error('score scale was not rendered');
        if (!rendered.includes('2项合计 6.0')) throw new Error('composite score width was hidden');
        if (!rendered.includes('合、会关系仅作候选')) throw new Error('relationship policy was hidden');
        if (!rendered.includes('本盘相对值 8.0')) throw new Error('relative score scope was missing');
        if (!rendered.includes('&lt;危险标签&gt;')) throw new Error('display label was not escaped');
        if (rendered.includes('<危险标签>')) throw new Error('raw display label reached HTML');
        """
    )

    result = run_node(script)

    assert result.returncode == 0, result.stderr or result.stdout


def test_annual_ai_review_matrix_summary_and_visibility():
    script = textwrap.dedent(
        f"""
        const fs = require('fs');
        const vm = require('vm');
        const source = fs.readFileSync({str(APP_JS)!r}, 'utf8');
        const start = source.indexOf('function _annualAiReviewMeta');
        const end = source.indexOf('function setDayunInterpretations');
        const sandbox = {{ esc(value) {{ return String(value); }} }};
        vm.createContext(sandbox);
        vm.runInContext(source.slice(start, end), sandbox);

        const reviews = [
          {{category: '婚嫁', review_status: '无明显信号', direction: '中性'}},
          {{category: '桃花', review_status: '有信号', direction: '正面', prediction: '关系机会增加'}},
          {{category: '事业', review_status: '无明显信号', direction: '中性'}},
          {{category: '财运', review_status: '无明显信号', direction: '中性'}},
          {{category: '健康', review_status: '未完成', direction: '中性'}},
          {{category: '搬迁', review_status: '无明显信号', direction: '中性'}},
        ];
        const meta = sandbox._annualAiReviewMeta(reviews);
        if (meta.categoryCount !== 6 || meta.completedCount !== 5) throw new Error('matrix counts are wrong');
        if (meta.signalCategories.join(',') !== '桃花') throw new Error('signal categories are wrong');

        const summary = sandbox._renderAnnualAiSummary(meta);
        if (!summary.includes('AI审阅 5/6类') || !summary.includes('有提示：桃花')) throw new Error('visible summary is incomplete');
        const header = sandbox._renderAnnualAiHeaderTag(meta);
        if (!header.includes('AI 桃花↑')) throw new Error('AI header category is missing');
        const details = sandbox._renderAnnualAiReviews(reviews);
        if (!details.includes('无明显信号') || !details.includes('未完成')) throw new Error('matrix states are not rendered');
        """
    )

    result = run_node(script)

    assert result.returncode == 0, result.stderr or result.stdout
    source = APP_JS.read_text(encoding="utf-8")
    assert source.count("if (!significant.length && !aiMeta.signalReviews.length) continue;") == 2


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
          name: '测试用户',
          gender: '男',
          birth: '1990-06-15 08:00',
          day_master: {{ stem: '甲', wuxing: '木', yinyang: '阳' }},
          pattern: '正官格',
          yongshen: {{ strength: '身弱', favorable_wuxing: ['水', '木'] }},
          life_stage: '职场',
          four_pillars: {{
            year: {{stem: '庚', branch: '午', hidden_stems: [], ten_god: '七杀'}},
            month: {{stem: '壬', branch: '午', hidden_stems: [], ten_god: '偏印'}},
            day: {{stem: '甲', branch: '寅', hidden_stems: [], ten_god: ''}},
            hour: {{stem: '戊', branch: '辰', hidden_stems: [], ten_god: '偏财'}}
          }},
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
        if (!html.includes('overview-pillars')) throw new Error('pillar masthead missing');
        if (!html.includes('庚午') || !html.includes('甲寅')) throw new Error('pillar values missing');
        if (!html.includes('data-daymaster')) throw new Error('day-master interaction missing');
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


def test_editorial_shell_uses_wide_task_first_layout_and_svg_tools():
    html = INDEX_HTML.read_text(encoding="utf-8")
    css = (ROOT / "frontend" / "style.css").read_text(encoding="utf-8")
    compact_css = "".join(css.split())

    for class_name in (
        'class="brand"',
        'class="entry-shell"',
        'class="entry-intro"',
        'class="entry-visual"',
        'class="entry-pillars"',
        'class="form-heading"',
        'class="result-zone"',
    ):
        assert class_name in html

    assert "💬" not in html
    assert "<svg" in html
    assert "body.container{max-width:1180px" in compact_css
    assert "body.entry-shell{display:grid" in compact_css
    assert "grid-template-columns:190pxminmax(0,1fr)" in compact_css
    assert "body.report-overview{display:grid" in compact_css


def test_mobile_report_action_bar_contains_primary_reader_actions():
    html = INDEX_HTML.read_text(encoding="utf-8")
    css = (ROOT / "frontend" / "style.css").read_text(encoding="utf-8")

    assert 'id="reportActions"' in html
    assert "openChat('报告')" in html
    assert "copyBtn" in html
    assert "scrollTo({top:0" in html
    assert html.index('id="result"') < html.index('id="reportActions"')
    assert "display:none" in css_rule_body(css, ".report-mobile-actions")


def test_frontend_asset_cache_versions():
    html = INDEX_HTML.read_text(encoding="utf-8")
    assert 'href="style.css?v=20260719-editorial1"' in html
    assert 'src="app.js?v=20260719-editorial1"' in html
    assert 'href="chat.css?v=20260719-editorial1"' in html


def test_frontend_exposes_city_search_and_true_solar_time_contract():
    html = INDEX_HTML.read_text(encoding="utf-8")
    app = (ROOT / "frontend" / "app.js").read_text(encoding="utf-8")
    css = (ROOT / "frontend" / "style.css").read_text(encoding="utf-8")

    assert 'id="citySearch"' in html
    assert 'id="cityOptions"' in html
    assert "出生城市/区县（默认未知）" in html
    assert "搜索城市或区县" in html
    assert 'id="longitude"' in html
    assert 'id="timezoneOffset"' in html
    assert 'id="timeAccuracy"' in html
    assert "/api/locations" in app
    assert "/api/time/preview" in app
    assert "requested_time_mode" in app
    assert "city.label || city.name" in app
    assert "text-overflow:ellipsis" in css


def test_birth_datetime_fields_share_one_aligned_grid_row():
    html = INDEX_HTML.read_text(encoding="utf-8")
    css = (ROOT / "frontend" / "style.css").read_text(encoding="utf-8")

    assert 'class="form-row birth-datetime-grid"' in html
    assert "出生日期（公历/阳历）" in html
    assert "出生时间（24小时制）" in html
    assert html.index('id="year"') < html.index('id="minute"')

    grid_rules = css_rule_bodies(css, ".birth-datetime-grid")
    grid_rule = next(rule for rule in grid_rules if "display:grid" in rule)
    assert "display:grid" in grid_rule
    assert "grid-template-columns:minmax(0,1.3fr)repeat(4,minmax(0,1fr))" in grid_rule
    assert "align-items:end" in grid_rule
    label_rule = css_rule_body(css, ".birth-datetime-grid label")
    assert "grid-row:2" in label_rule
    assert "min-width:0" in label_rule


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
          dayun: {{
            jiao_yun: {{ reference: '上一节', years: 6 }},
          }},
          kinship: {{
            spouse: {{ label: '妻星', stars: ['正财', '偏财'] }},
          }},
          annual_scans: [{{ year: 2026, events: [{{ category: '事业', strength: 3 }}] }}]
        }});
        if (!html.includes('href="#section-personality"')) throw new Error('personality nav missing');
        if (!html.includes('href="#section-focus"')) throw new Error('focus nav missing');
        if (!html.includes('href="#section-dayun"')) throw new Error('dayun nav missing');
        if (!html.includes('href="#section-gender-luck"')) throw new Error('gender luck nav missing');
        if (!html.includes('href="#section-flow"')) throw new Error('flow nav missing');
        if (!html.includes('href="#section-foundation"')) throw new Error('foundation nav missing');
        if (!html.includes('原始依据')) throw new Error('foundation label missing');
        if (!html.includes('报告导航')) throw new Error('nav label missing');

        const dayunIndex = html.indexOf('href="#section-dayun"');
        const genderLuckIndex = html.indexOf('href="#section-gender-luck"');
        const flowIndex = html.indexOf('href="#section-flow"');
        if (!(dayunIndex < genderLuckIndex && genderLuckIndex < flowIndex)) {{
          throw new Error('gender luck nav is not between dayun and flow');
        }}

        const emptyHtml = sandbox._buildReportNav({{
          personality: {{ profile: 'x' }},
          dayun: {{}},
          xiaoyun: {{}},
          kinship: {{}},
          annual_scans: [{{ year: 2026, events: [] }}]
        }});
        if (emptyHtml.includes('href="#section-gender-luck"')) {{
          throw new Error('gender luck nav should be hidden without displayable data');
        }}
        """
    )

    result = run_node(script)

    assert result.returncode == 0, result.stderr or result.stdout


def test_gender_luck_section_is_integrated_and_responsive():
    js = APP_JS.read_text(encoding="utf-8")
    css = (ROOT / "frontend" / "style.css").read_text(encoding="utf-8")
    compact_css = "".join(css.split())
    media_selector = "@media(max-width:480px)"
    desktop_css = css[: css.index(media_selector)]
    mobile_css = extract_css_block(css, media_selector)

    render_start = js.index("function render(d){")
    render_body = js[render_start:]
    assert (
        "h += _buildReportFocusSections(d);\n"
        "  h += _buildGenderLuckSection(d);"
    ) in render_body

    renderer_source = js[
        js.index("function _buildGenderLuckSection(d){") :
        js.index("function _buildReportFocusSections(d){")
    ]
    assert renderer_source.count("class=gender-luck-panel") == 1
    panel_source = renderer_source.split("class=gender-luck-panel", 1)[1]
    panel_source = panel_source.split("h += '</div></section>';", 1)[0]
    assert "report-mini-card" not in panel_source
    assert "class=card" not in panel_source
    panel_html = render_gender_luck_section(
        {
            "dayun": {
                "direction": "顺排",
                "jiao_yun": {"reference": "下一节", "years": 6},
            },
            "kinship": {
                "spouse": {"label": "夫星", "stars": ["正官", "七杀"]},
            },
        }
    )
    parser = GenderLuckPanelParser()
    parser.feed(panel_html)
    parser.close()
    parser.assert_balanced()
    assert parser.panel_count == 1
    assert parser.nested_card_classes == []
    assert parser.open_tags == []
    assert parser.panel_depth == 0

    for order_rule in (
        "#section-personality{order:3}",
        "#section-focus{order:4}",
        "#section-dayun{order:5}",
        "#section-gender-luck{order:6}",
        "#section-flow{order:7}",
        "#section-calendar{order:8}",
        "#section-foundation{order:9}",
        ".report-warning{order:10}",
    ):
        assert order_rule in compact_css

    summary_rule = css_rule_body(desktop_css, ".gender-luck-summary")
    assert "display:grid" in summary_rule
    assert "grid-template-columns:repeat(3,minmax(0,1fr))" in summary_rule

    summary_row_rule = css_rule_body(desktop_css, ".gender-luck-summary-row")
    assert "min-width:0" in summary_row_rule
    assert "border-right:1pxsolidvar(--border)" in summary_row_rule
    assert "border-right:0" in css_rule_body(
        desktop_css, ".gender-luck-summary-row:last-child"
    )

    chips_rule = css_rule_body(desktop_css, ".gender-luck-chips")
    assert "display:flex" in chips_rule
    assert "overflow-x:auto" in chips_rule
    chips_focus_rule = css_rule_body(
        desktop_css, ".gender-luck-chips:focus-visible"
    )
    assert "outline:2pxsolidvar(--accent)" in chips_focus_rule
    assert "outline-offset:2px" in chips_focus_rule

    kinship_rule = ";".join(css_rule_bodies(desktop_css, ".gender-luck-kinship"))
    assert "display:grid" in kinship_rule
    assert "grid-template-columns:repeat(2,minmax(0,1fr))" in kinship_rule

    kinship_label_rule = css_rule_body(
        desktop_css, ".gender-luck-kinship-row span"
    )
    assert "flex:01auto" in kinship_label_rule
    assert "min-width:0" in kinship_label_rule
    assert "overflow-wrap:anywhere" in kinship_label_rule

    kinship_value_rule = css_rule_body(
        desktop_css, ".gender-luck-kinship-row b"
    )
    assert "flex:11auto" in kinship_value_rule
    assert "min-width:0" in kinship_value_rule
    assert "overflow-wrap:anywhere" in kinship_value_rule
    assert "text-align:right" in kinship_value_rule

    sensitive_note_rule = css_rule_body(desktop_css, ".gender-luck-sensitive-note")
    assert (
        "border-left:2pxsolidcolor-mix(insrgb,var(--bad)42%,var(--border))"
        in sensitive_note_rule
    )
    assert (
        "background:color-mix(insrgb,var(--bad)6%,var(--surface))"
        in sensitive_note_rule
    )

    assert "grid-template-columns:1fr" in css_rule_body(
        mobile_css, ".gender-luck-summary"
    )
    mobile_kinship_rules = ";".join(
        css_rule_bodies(mobile_css, ".gender-luck-kinship")
    )
    assert "grid-template-columns:1fr" in mobile_kinship_rules
    mobile_gender_luck_bodies = [
        "".join(body.split())
        for selectors, body in re.findall(r"([^{}]+)\{([^{}]*)\}", mobile_css)
        if ".gender-luck-" in selectors
    ]
    assert mobile_gender_luck_bodies
    assert all("70px" not in body for body in mobile_gender_luck_bodies)
    assert "margin:013px13px" in css_rule_body(
        mobile_css, ".gender-luck-sensitive-note"
    )


def test_mobile_report_action_bar_is_static_end_of_report_toolbar():
    css = (ROOT / "frontend" / "style.css").read_text(encoding="utf-8")
    mobile_css = extract_css_block(css, "@media(max-width:480px)")
    container_rule = css_rule_body(mobile_css, ".container")
    action_rule = css_rule_body(mobile_css, ".report-mobile-actions.active")

    assert "padding:16px12px24px" in container_rule
    assert "position:fixed" not in action_rule
    assert "bottom:" not in action_rule
    assert "z-index:900" not in action_rule
    assert "display:grid" in action_rule
    assert "grid-template-columns:1fr1fr1fr" in action_rule
    assert "width:calc(100%-108px)" in action_rule
    assert "max-width:512px" in action_rule
    assert "margin:24px84px24px12px" in action_rule
    assert "#section-gender-luck{margin-bottom:36px}" not in "".join(
        mobile_css.split()
    )


def test_gender_luck_panel_parser_rejects_unclosed_panel():
    parser = GenderLuckPanelParser()
    parser.feed('<section><div class="gender-luck-panel"><span>未闭合')
    parser.close()

    with pytest.raises(AssertionError):
        parser.assert_balanced()


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
          annual_scans: [{{ year: 2026, events: [
            {{ category: 'base', strength: 2 }}
          ], ai_reviews: [
            {{ category: 'stream', direction: 'positive', strength: 3, prediction: 'same', triggers: ['trigger'], notes: ['note'], source: 'llm' }}
          ] }}],
          dayun: {{ interpretations: [] }}
        }};

        sandbox.setChartData(chart);
        if (sandbox.getChartData() !== chart) throw new Error('getChartData did not return the active chart');
        if (sandbox.getCurrentContext() !== chart.current_context) throw new Error('current_context was not cached');
        if (!vm.runInContext('CHAT.chartData === getChartData()', sandbox)) throw new Error('legacy chat chart was not synchronized');
        if (sandbox.window._calChart !== chart) throw new Error('legacy calendar chart was not synchronized');

        sandbox.mergeAnnualAiReviews(2026, [{{ category: 'stream', direction: 'positive', strength: 3, prediction: 'same', triggers: ['trigger'], notes: ['note'], source: 'llm' }}]);
        if (chart.current_context.current_dayun.ganzhi !== 'bingwu') throw new Error('current_context changed during annual merge');
        if (chart.annual_scans[0].events.length !== 1) throw new Error('LLM review changed rule signals');
        if (chart.annual_scans[0].ai_reviews.length !== 1) throw new Error('duplicate LLM review was appended');
        sandbox.mergeAnnualAiReviews(2026, [{{ category: 'stream', direction: 'positive', strength: 3, prediction: 'different', triggers: ['trigger'], notes: ['note'], source: 'llm' }}]);
        if (chart.annual_scans[0].ai_reviews.length !== 2) throw new Error('distinct LLM review was not merged');

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


def test_fusion_stream_prefers_cleaned_full_report_on_completion():
    """独立融合入口完成时必须用服务端清洗全文覆盖原始 token。"""
    from pathlib import Path

    frontend = Path(__file__).resolve().parents[2] / "frontend"
    for script in (frontend / "app.js",):
        source = script.read_text(encoding="utf-8")
        assert "let finalText = chunk.full || text;" in source
        assert "el.innerHTML = md2html(finalText) || initialText;" in source
        assert "showFusionFeedback(finalText" in source


def test_markdown_renderer_escapes_raw_html_before_rendering():
    source = APP_JS.read_text(encoding="utf-8")
    assert "t = esc(_stripScores(String(t || '')));" in source
    assert "保护所有已生成的 HTML 标签" not in source


def test_fusion_feedback_ui_submission_contract():
    """融合报告应提供三档评分、可选偏差板块和独立反馈接口。"""
    frontend = Path(__file__).resolve().parents[2] / "frontend"
    app_source = (frontend / "app.js").read_text(encoding="utf-8")
    css = (frontend / "style.css").read_text(encoding="utf-8")

    for source in (app_source,):
        assert "这份分析像你吗？" in source
        assert "data-rating=very" in source
        assert "data-rating=partial" in source
        assert "data-rating=low" in source
        assert "核心画像" in source
        assert "重点分析" in source
        assert "分类与结构" in source

    for source in (app_source,):
        assert "function selectFusionRating" in source
        assert "function submitFusionFeedback" in source
        assert "'/api/personality/fusion/feedback'" in source
        assert "generation_id:state.generation && state.generation.generation_id" in source
        assert "report_text:state.reportText" not in source

    assert ".fusion-rating-options" in css
    assert "grid-template-columns:repeat(3,minmax(0,1fr))" in css
    assert ".fusion-feedback-thanks" in css


def test_fusion_heading_styles_keep_section_and_topic_levels_distinct():
    css = (Path(__file__).resolve().parents[2] / "frontend" / "style.css").read_text(encoding="utf-8")

    section_heading = css_rule_body(css, ".personality-text h1,.personality-text h2")
    topic_heading = css_rule_body(css, ".personality-text h3")

    assert "font-size:16px" in section_heading
    assert "font-size:14px" in topic_heading
    assert "border-left:3pxsolidvar(--accent)" in topic_heading


def test_personality_evidence_panel_explains_scores_and_field_semantics():
    app_source = APP_JS.read_text(encoding="utf-8")
    css = (Path(__file__).resolve().parents[2] / "frontend" / "style.css").read_text(encoding="utf-8")
    compact_css = "".join(css.split())

    assert "查看分析依据" in app_source
    assert "查看本次分析采用的规则依据" in app_source
    assert "排序仅本盘内比较" in app_source
    assert "固定工程阈值" in app_source
    assert "不是古籍固定比例、概率、准确率或人群常模" in app_source
    assert "合、会关系仅作候选" in app_source
    assert "2项合计" in app_source
    assert "合局（每个匹配十神一次）" not in app_source
    assert "personality.evidence_view" in app_source
    assert "_buildEvidenceDimensions" in app_source
    assert "_buildEvidenceScale" in app_source
    assert "_buildPersonalityEvidence" in app_source
    assert "signals[j].display_label || signals[j].label" in app_source
    assert "本盘相对值" in app_source
    assert "Object.keys(legacyWeighted).length" in app_source
    assert "行为模式与家庭背景" not in app_source
    assert "性格与家境" not in app_source
    assert "暂无可核对的性格分析依据" in app_source
    assert "待复核规则" in app_source
    assert "entries.filter(function(item){returnitem.val>0;}).slice(0,10)" in "".join(app_source.split())

    assert ".evidence-signals" in css
    assert ".evidence-scale-details" in css
    assert ".evidence-boundaries" in css
    assert "@media(max-width:480px)" in compact_css
    assert ".evidence-scale-content{grid-template-columns:1fr;padding-left:12px}" in compact_css
