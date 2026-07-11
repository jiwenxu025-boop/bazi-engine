"""RAG 知识检索层测试 — v0.18.0 含 section 分区 + retrieve_for_generation"""
import json
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import bazi_engine.rag as rag


def _reload():
    rag._loaded = False
    rag._chunks.clear()
    rag._PERSONALITY_VEC_READY = False
    rag._load_all()


def test_load_all():
    _reload()
    assert len(rag._chunks) > 0
    ref = [c for c in rag._chunks if c["kind"] == "reference"]
    cal = [c for c in rag._chunks if c["kind"] == "calibration"]
    assert len(ref) > 0 and len(cal) > 0
    assert all("sections" in c for c in rag._chunks)


def test_section_partition():
    """每个 chunk 的 sections 字段正确"""
    _reload()
    for c in rag._chunks:
        assert isinstance(c.get("sections", []), list)
        assert len(c["sections"]) >= 1
    # dayun-rules chunks should have "dayun" section
    dy_chunks = [c for c in rag._chunks if c["source"] == "dayun-rules.md"]
    assert all("dayun" in c["sections"] for c in dy_chunks)
    # personality-rules chunks should have "personality"
    pr_chunks = [c for c in rag._chunks if c["source"] == "personality-rules.md"]
    assert all("personality" in c["sections"] for c in pr_chunks)


def test_chunk_contains_late_keywords():
    _reload()
    ref_chunks = [c for c in rag._chunks if c["kind"] == "reference"]
    texts = " ".join(c["text"] for c in ref_chunks)
    assert "天克地冲" in texts


def test_retrieve_suiyun_jiaozhan():
    ctx = {
        "natal": {"day_master": "壬(水·阳)", "pattern": "偏印格", "strength": "强",
                  "favorable": ["土"], "harmful": ["水"], "favorable_wuxing": ["土"], "harmful_wuxing": ["水"],
                  "key_interactions": ["申辰半合水"]},
        "dayun": {"stem": "丙", "branch": "午"},
        "liunian": {"year": 2023, "age": 16, "stem": "癸", "branch": "卯"},
        "year_features": {"岁运交战": "流年癸克大运丙(天战)"},
        "rule_signals": [{"category": "状态", "direction": "负面", "strength": 2, "triggers": ["流年癸克大运丙(天战)"]}],
    }
    results = rag.retrieve_for_review(ctx, top_k=5)
    assert len(results) > 0
    ref_matches = [r for r in results if r["source"] != "calibration_store.json"]
    assert len(ref_matches) > 0


def test_retrieve_hunjia_taohua():
    ctx = {
        "natal": {"day_master": "壬(水·阳)", "pattern": "偏印格", "strength": "强",
                  "favorable": ["土"], "harmful": ["水"], "key_interactions": []},
        "dayun": {"stem": "丙", "branch": "午"},
        "liunian": {"year": 2023, "age": 16, "stem": "癸", "branch": "卯"},
        "year_features": {"红鸾": "流年卯=红鸾入命", "夫妻宫引动": "害夫妻宫"},
        "rule_signals": [{"category": "桃花", "direction": "中性", "strength": 2, "triggers": ["卯辰穿夫妻宫"]}],
    }
    results = rag.retrieve_for_review(ctx, top_k=5)
    assert len(results) > 0


def test_chat_relevant():
    chart = {"day_master": {"stem": "壬"}, "pattern": "偏印格",
             "yongshen": {"favorable": ["伤官"], "harmful": ["偏印"], "favorable_wuxing": ["土"], "harmful_wuxing": ["水"]}}
    results = rag.retrieve_for_chat(chart, "岁运交战天克地冲是什么意思")
    assert len(results) > 0
    assert any(r["source"] != "calibration_store.json" for r in results)


def test_personality_prompt_contains_rag():
    """build_fusion_user_prompt 构造出的 prompt 包含 personality-rules 参考"""
    from bazi_engine.personality_fusion import build_fusion_user_prompt
    dp = {"日主": "壬水阳", "格局": "偏印格", "喜用十神": ["伤官"], "忌十神": ["偏印"],
          "六维度信号": {"社交": "", "感情": "", "内心": "", "决策": "", "事业": "", "财富观": ""},
          "病药组合": [], "特殊组合": [], "压力画像": {}, "家境背景": {}}
    prompt = build_fusion_user_prompt(dp)
    assert "【结构化数据】" in prompt, "应包含数据区"
    assert "参考规则/校准" in prompt, "应包含 RAG 参考块"
    assert "personality-rules" in prompt, "应命中 personality-rules 知识源"
    assert "【输出要求】" in prompt, "应包含结尾输出约束"
    # 顺序：数据 → RAG → 输出要求
    assert prompt.find("【结构化数据】") < prompt.find("参考规则/校准"), "数据应在 RAG 前"
    assert prompt.find("参考规则/校准") < prompt.find("【输出要求】"), "RAG 应在输出要求前"


def test_fusion_package_sanitizes_raw_scores_and_prompt_order():
    """性格融合 prompt 使用清洗后的 LLM 数据包，并以输出要求收尾"""
    from bazi_engine.personality_fusion import build_fusion_data_package, build_fusion_user_prompt

    pr_dict = {
        "day_master_core": {"天干": "壬", "阴阳": "阳", "五行": "水"},
        "strength_label": "偏强（7.2分）",
        "pattern_validation": {"status": "成格", "note": "偏印格"},
        "bingyao_combos": [{"combo": "印重身滞", "directive": "多行动少空想"}],
        "weighted_shishen": {
            "scores": {"偏印": 8.0, "比肩": 6.0, "食神": 3.0, "正官": 1.5}
        },
        "sub_traits": [
            {"trait_name": "深度思考", "description": "喜欢想事情", "score": 7.5},
            {
                "trait_name": "不善表达情感",
                "description": "情绪不常外露",
                "score": 8.2,
                "source_type": "hidden",
            },
        ],
        "combo_traits": [],
        "dizhi_traits": [],
        "trait_signals": {
            "社交": {
                "表达欲": 3.0,
                "内敛度": 8.0,
                "拘谨度": 5.0,
                "综合倾向": "内敛",
                "综合分数": -1.2,
            },
            "感情": {"责任感_官杀": 6.0, "欲望_财星": 4.0, "桃花坐日支": False},
            "内心": {"精神世界_偏印": 8.0, "自洽度_食神": 3.0},
            "决策": {
                "果断度_七杀": 7.0,
                "分析度_印星": 8.0,
                "综合倾向": "分析后决策",
                "综合分数": 2.5,
            },
            "事业": {"体制_管理": 6.0, "技术_创意": 8.0, "主导方向": "技术/创意"},
            "财富观": {"欲望_财星": 5.0, "散财_比劫": 3.0},
        },
    }

    dp = build_fusion_data_package(pr_dict)
    prompt = build_fusion_user_prompt(dp)
    pkg_text = json.dumps(dp, ensure_ascii=False)

    assert "综合分数" not in pkg_text
    assert "7.2分" not in pkg_text
    assert dp["日主画像"]["身强弱"] == "偏强"
    assert dp["六维度信号"]["社交"]["表达欲"] == "偏低"
    assert dp["六维度信号"]["社交"]["内敛度"] == "偏高"
    assert dp["六维度信号"]["感情"]["桃花坐日支"] is False
    assert "表达欲偏低" in dp["六维度信号"]["社交"]["_需覆盖信号"]

    for item in dp["十神强度排行"]:
        assert "强度" not in item
        assert "相对强度" in item

    for item in dp["粒度性格特质"]["十神加权特质"]:
        assert "强度" not in item
        assert "强度定性" in item

    assert prompt.find("【结构化数据】") < prompt.find("参考规则/校准")
    assert prompt.find("参考规则/校准") < prompt.find("【输出要求】")


def test_fusion_report_quality_gate_modernizes_terms():
    """最终融合报告应清理术语泄漏、异常符号和过硬断言"""
    from bazi_engine.personality_fusion import (
        fusion_report_quality_issues,
        sanitize_fusion_report,
    )

    raw = (
        "夫妻宫有冲（日支为辰），加上藏偏官和伤官。"
        "华盖星也意味着你对哲学有兴趣。杀印相生让你能扛压力。"
        "问题在于%的时间你在“想通”这个阶段%的时间在执行。"
        "你是一个“被刺激才能启动”的人。你更像个工程兵，不是总设计师。"
        "财破印会让你被短期收益诱惑。"
    )

    cleaned = sanitize_fusion_report(raw)
    assert "夫妻宫" not in cleaned
    assert "日支" not in cleaned
    assert "偏官" not in cleaned
    assert "伤官" not in cleaned
    assert "华盖星" not in cleaned
    assert "杀印相生" not in cleaned
    assert "财破印" not in cleaned
    assert "%" not in cleaned
    assert "被刺激才能启动" not in cleaned
    assert "不是总设计师" not in cleaned
    assert "亲密关系位置" in cleaned
    assert "短期收益和长期积累冲突" in cleaned
    assert fusion_report_quality_issues(cleaned) == []


def test_fusion_prompt_contains_zhihe_style_contract():
    """性格融合 prompt 应包含项目化后的知禾式表达约束"""
    from bazi_engine.personality_fusion import FUSION_SYSTEM_PROMPT

    assert "知禾式表达" in FUSION_SYSTEM_PROMPT
    assert "温和、耐心、清楚" in FUSION_SYSTEM_PROMPT
    assert "保持诚实" in FUSION_SYSTEM_PROMPT
    assert "不要过度安抚" in FUSION_SYSTEM_PROMPT


def test_fusion_prompt_omits_action_section():
    """当前性格融合报告不应输出独立行动建议板块"""
    from bazi_engine.personality_fusion import FUSION_SYSTEM_PROMPT, build_fusion_user_prompt

    assert "## 立刻能做的事" not in FUSION_SYSTEM_PROMPT
    assert "立刻能做的事要求" not in FUSION_SYSTEM_PROMPT
    assert "立刻能做的事" in FUSION_SYSTEM_PROMPT
    assert "独立板块" in FUSION_SYSTEM_PROMPT

    prompt = build_fusion_user_prompt({"六维度信号": {"社交": "内敛"}})
    assert "立刻能做的事" in prompt
    assert "独立板块" in prompt


def test_fusion_report_quality_gate_removes_action_section():
    """即使模型输出建议板块，最终报告也会删除"""
    from bazi_engine.personality_fusion import sanitize_fusion_report

    raw = "全局诊断：这里是分析。\n\n## 社交\n这里是社交分析。\n\n## 立刻能做的事\n1. 马上做某事。"
    cleaned = sanitize_fusion_report(raw)
    assert "全局诊断" in cleaned
    assert "## 社交" in cleaned
    assert "立刻能做的事" not in cleaned
    assert "马上做某事" not in cleaned


def test_chat_irrelevant():
    chart = {"day_master": {"stem": "壬"}, "pattern": "偏印格",
             "yongshen": {"favorable": ["伤官"], "harmful": ["偏印"]}}
    results = rag.retrieve_for_chat(chart, "今天天气怎么样")
    assert len(results) == 0


def test_generation_dayun():
    """retrieve_for_generation dayun 应命中 dayun-rules 等"""
    ctx = {"natal": {"day_master": "壬", "pattern": "偏印格", "strength": "强",
                     "favorable_wuxing": ["土"], "harmful_wuxing": ["水"],
                     "favorable": ["伤官"], "harmful": ["偏印"]},
           "modulations": [{"dayun_stem": "丙", "dayun_branch": "午", "theme": "财运",
                            "stem_interactions": [], "branch_interactions": ["与戌半合火"]}]}
    results = rag.retrieve_for_generation("dayun", ctx)
    assert len(results) > 0
    sources = {r["source"] for r in results}
    assert "dayun-rules.md" in sources, f"Expected dayun-rules.md in {sources}"


def test_generation_personality():
    """retrieve_for_generation personality 应命中 personality-rules"""
    dp = {"日主": "壬水阳", "格局": "偏印格", "喜用十神": ["伤官"], "忌十神": ["偏印"],
          "六维度信号": {"社交": "外向", "感情": "被动", "内心": "孤僻", "决策": "果断", "事业": "进取", "财富观": "务实"},
          "病药组合": [], "特殊组合": [], "压力画像": {}, "家境背景": {}}
    results = rag.retrieve_for_generation("personality", dp)
    assert len(results) > 0
    sources = {r["source"] for r in results}
    assert "personality-rules.md" in sources, f"Expected personality-rules.md in {sources}"


def test_generation_chat_irrelevant():
    """retrieve_for_generation chat 无关问题应返回空"""
    chart = {"day_master": {"stem": "壬"}, "pattern": "偏印格",
             "yongshen": {"favorable": ["伤官"], "harmful": ["偏印"]}}
    results = rag.retrieve_for_generation("chat", chart, "今天天气怎么样")
    assert len(results) == 0


def test_empty_graceful():
    assert isinstance(rag.retrieve_for_review({"natal": {}, "liunian": {}, "rule_signals": []}), list)
    assert rag.retrieve_for_chat({}, "") == []
    assert rag.retrieve_for_generation("dayun", {}) == []


def test_format_snippets():
    sn = [{"source": "t.md", "heading": "规则", "text": "内容"}]
    text = rag.format_snippets(sn)
    assert "[t.md]" in text and "规则" in text
    assert rag.format_snippets([]) == ""

    sn2 = [{"source": "a.md", "heading": "h", "text": "x" * 2000}]
    text2 = rag.format_snippets(sn2, max_chars=100)
    assert len(text2) <= 150 and text2.endswith("...")


def test_extract_ngrams():
    ng = rag._extract_ngrams("天克地冲是什么意思", 2, 4)
    assert any(x in ng for x in ["天克", "天克地", "天克地冲"])


def test_vector_personality_relevant():
    """向量检索路径：使用生产级 data_package 命中 personality-rules.md"""
    from bazi_engine.personality_fusion import build_fusion_data_package
    _reload()
    pr_dict = {
        "day_master_core": {"天干": "壬", "阴阳": "阳", "五行": "水"},
        "strength_label": "偏强（7.2分）",
        "pattern_validation": {"status": "成格", "note": "偏印格"},
        "weighted_shishen": {"scores": {"偏印": 8.0, "比肩": 6.0, "食神": 3.0}},
        "sub_traits": [
            {"trait_name": "深度思考", "description": "喜欢深入分析", "score": 7.5},
            {"trait_name": "不善表达情感", "description": "情绪内敛", "score": 8.2, "source_type": "hidden"},
        ],
        "combo_traits": [{"combo": "印重身滞", "trait": "行动力不足", "description": "思多行少"}],
        "trait_signals": {
            "社交": {"表达欲": 3.0, "内敛度": 8.0, "综合倾向": "内敛"},
            "感情": {"桃花坐日支": False},
            "内心": {"精神世界_偏印": 8.0},
            "决策": {"果断度_七杀": 7.0},
            "事业": {"技术_创意": 8.0},
            "财富观": {"欲望_财星": 5.0},
        },
    }
    dp = build_fusion_data_package(pr_dict)
    results = rag.retrieve_for_generation("personality", dp)
    assert len(results) > 0
    sources = {r["source"] for r in results}
    assert "personality-rules.md" in sources


def test_vector_personality_fallback():
    """空数据包 → 向量低于阈值 → 优雅降级到关键词路径"""
    _reload()
    dp = {"日主": "", "格局": "", "喜用十神": [], "忌十神": [],
          "六维度信号": {}, "病药组合": [], "特殊组合": [],
          "压力画像": {}, "家境背景": {}}
    assert rag._build_personality_query_text(dp) == ""
    results = rag.retrieve_for_generation("personality", dp)
    assert isinstance(results, list)
