"""RAG 知识检索层测试 — v0.18.0 含 section 分区 + retrieve_for_generation"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import bazi_engine.rag as rag


def _reload():
    rag._loaded = False
    rag._chunks.clear()
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
    assert "底层数据输入" in prompt, "应包含数据区"
    assert "参考规则/校准" in prompt, "应包含 RAG 参考块"
    assert "personality-rules" in prompt, "应命中 personality-rules 知识源"
    # 顺序：数据 → RAG → 结尾
    assert prompt.find("底层数据输入") < prompt.find("参考规则/校准"), "数据应在 RAG 前"


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
