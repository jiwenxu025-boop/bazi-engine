"""轻量 RAG 知识检索层 — 第一阶段：本地关键词检索

不打 embedding、不引向量库。从 references/*.md 和 calibration_store.json
按关键词+类别打分检索相关规则/校准片段，供 LLM prompt 注入。

设计原则:
- 检索失败静默降级为空列表
- 单次检索注入总量 ≤ 2200 中文字符
- chunk 保留 source 来源，方便排查 LLM 判断依据
- v0.18.0: 按 section（chat/liunian_review/dayun/personality）过滤 chunk
"""

import json
import os
import re
from pathlib import Path
from typing import Any

# ── 路径：rag.py → bazi_engine → scripts → bazi（根目录）──
_ROOT = Path(__file__).resolve().parent.parent.parent
_REFERENCES_DIR = _ROOT / "references"
_CALIBRATION_FILE = Path(__file__).resolve().parent.parent / "data" / "calibration_store.json"

# ── 进程缓存 ──
_chunks: list[dict[str, Any]] = []
_loaded: bool = False

# ── source → sections 映射：每个知识源服务于哪些生成板块 ──
_SOURCE_SECTIONS: dict[str, list[str]] = {
    "dayun-rules.md":           ["dayun", "liunian_review", "chat"],
    "personality-rules.md":     ["personality"],
    "family-background.md":     ["personality"],
    "calibration-notes.md":     ["liunian_review", "chat"],
    "calibration_store.json":   ["liunian_review", "chat"],
    "advanced-techniques.md":   ["dayun", "personality"],
    "wuxing-tables.md":         ["chat", "liunian_review", "dayun", "personality"],
    "classical-texts.md":       ["chat", "liunian_review", "dayun", "personality"],
    "shichen-table.md":         ["chat", "liunian_review", "dayun"],
    "modern-vs-engine.md":      ["dayun", "liunian_review"],
}
_DEFAULT_SECTIONS = ["chat", "liunian_review"]


def _sections_for_source(source: str) -> list[str]:
    return _SOURCE_SECTIONS.get(source, _DEFAULT_SECTIONS)


# ── 同义词映射：任一词命中即可展开全组 ──
_SYNONYM_GROUPS: list[set[str]] = [
    {"岁运交战", "天克地冲", "反吟", "伏吟", "天战", "地战", "岁运相冲", "征太岁"},
    {"婚嫁", "婚姻", "结婚", "订婚", "同居", "感情"},
    {"桃花", "恋爱", "恋情", "脱单", "分手", "感情"},
    {"财运", "破财", "发财", "得财", "财富", "收入"},
    {"事业", "工作", "职场", "晋升", "跳槽", "创业"},
    {"健康", "疾病", "伤病", "手术", "身体"},
    {"搬迁", "搬家", "迁移", "换城市", "留学"},
    {"升学", "考试", "高考", "考研", "学业"},
    {"红鸾", "天喜", "桃花", "感情机遇"},
    {"卯辰穿", "穿害", "相害", "夫妻宫"},
    {"六冲", "相冲", "地支冲"},
    {"三合", "半合", "六合", "地支合"},
    {"食神", "伤官", "食伤"},
    {"正财", "偏财", "财星"},
    {"正官", "偏官", "七杀", "官杀"},
    {"正印", "偏印", "枭神", "印星"},
    {"比肩", "劫财", "比劫"},
    {"身强", "身旺", "旺相"},
    {"身弱", "衰弱"},
    {"调候", "寒暖", "燥湿"},
    {"贪生忘克", "假生陷阱"},
]


def _expand_synonyms(terms: set[str]) -> set[str]:
    result = set(terms)
    for group in _SYNONYM_GROUPS:
        if group & result:
            result |= group
    return result


def _extract_ngrams(text: str, min_len: int = 2, max_len: int = 6) -> list[str]:
    cleaned = re.sub(r'[^\u4e00-\u9fff\w]', '', text)
    ngrams = set()
    for n in range(min_len, min(max_len + 1, len(cleaned) + 1)):
        for i in range(len(cleaned) - n + 1):
            ngrams.add(cleaned[i:i + n])
    return list(ngrams)


# ── 本地向量基元（零依赖，确定性）──


def _build_ngram_freq(text: str, min_len: int = 2, max_len: int = 4) -> dict[str, int]:
    """构建 n-gram 频次字典（字符级 2-4 gram）。"""
    freq: dict[str, int] = {}
    for ng in _extract_ngrams(text, min_len, max_len):
        freq[ng] = freq.get(ng, 0) + 1
    return freq


def _ngram_cosine_from_freq(freq_a: dict[str, int], freq_b: dict[str, int]) -> float:
    """从两个频次字典计算余弦相似度。"""
    if not freq_a or not freq_b:
        return 0.0
    keys = set(freq_a.keys()) | set(freq_b.keys())
    dot = sum(freq_a.get(k, 0) * freq_b.get(k, 0) for k in keys)
    mag_a = sum(v * v for v in freq_a.values()) ** 0.5
    mag_b = sum(v * v for v in freq_b.values()) ** 0.5
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)


def _build_personality_query_text(data_package: dict) -> str:
    """从性格融合数据包构造向量查询文本。"""
    parts: list[str] = ["性格分析"]
    for key in ["日主画像", "格局状态", "全局最高指令", "关键组合",
                "粒度性格特质", "十神强度排行", "六维度信号", "家境背景"]:
        val = data_package.get(key)
        if val is None:
            continue
        if val == "" or val == [] or val == {}:
            continue
        if isinstance(val, (dict, list)):
            s = json.dumps(val, ensure_ascii=False, separators=(",", ":"))
            if len(s) > 400:
                s = s[:400]
        else:
            s = str(val)[:200]
        if not s:
            continue
        parts.append(f"{key}:{s}")
    if len(parts) == 1:
        return ""
    return " ".join(parts)[:2000]


# ── 个性向量预计算缓存 ──
_PERSONALITY_VEC_READY: bool = False


def _ensure_personality_vectors():
    """为所有 personality chunk 预计算 n-gram 频次向量。"""
    global _PERSONALITY_VEC_READY
    if _PERSONALITY_VEC_READY:
        return
    for c in _chunks:
        if "personality" in c.get("sections", []) and "ngram_freq" not in c:
            text = c["heading"] + " " + c["text"]
            c["ngram_freq"] = _build_ngram_freq(text)
    _PERSONALITY_VEC_READY = True


def _load_all():
    global _chunks, _loaded, _PERSONALITY_VEC_READY
    if _loaded:
        return
    _loaded = True
    _PERSONALITY_VEC_READY = False
    _chunks.clear()
    _load_references()
    _load_calibration()
    _ensure_personality_vectors()


def _chunk_markdown_section(source: str, heading: str, body: str, sections: list[str],
                             min_chars: int = 100, max_chars: int = 800):
    paragraphs = re.split(r'\n{2,}', body)
    current_text = ""
    current_paras = []

    def flush():
        nonlocal current_text, current_paras
        if current_text.strip():
            text = "\n\n".join(current_paras).strip()
            if len(text) < min_chars and len(text) < 50:
                pass
            elif len(text) > max_chars:
                sub_parts = re.split(r'(?<=[。])\s*', text)
                sub_text = ""
                for part in sub_parts:
                    if len(sub_text) + len(part) > max_chars and sub_text:
                        _chunks.append({
                            "source": source, "heading": heading,
                            "text": sub_text.strip(), "kind": "reference",
                            "sections": sections,
                        })
                        sub_text = part
                    else:
                        sub_text += part
                if sub_text.strip():
                    _chunks.append({
                        "source": source, "heading": heading,
                        "text": sub_text.strip(), "kind": "reference",
                        "sections": sections,
                    })
            else:
                _chunks.append({
                    "source": source, "heading": heading,
                    "text": text, "kind": "reference",
                    "sections": sections,
                })
        current_text = ""
        current_paras = []

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        is_list = re.match(r'^[\d\-\*\•]', para)
        combined_len = len(current_text) + len(para) + 2
        if is_list or combined_len <= max_chars:
            current_paras.append(para)
            current_text = "\n\n".join(current_paras)
            if len(current_text) >= max_chars:
                flush()
        else:
            flush()
            current_paras = [para]
            current_text = para
    flush()


def _load_references():
    if not _REFERENCES_DIR.is_dir():
        return
    for fpath in sorted(_REFERENCES_DIR.glob("*.md")):
        try:
            text = fpath.read_text(encoding="utf-8")
        except Exception:
            continue
        source = fpath.name
        sections = _sections_for_source(source)
        for sec in re.split(r"\n(?=## )", text):
            sec = sec.strip()
            if not sec:
                continue
            heading_match = re.match(r"^##?\s+(.+)", sec)
            heading = heading_match.group(1).strip() if heading_match else ""
            body = sec[heading_match.end():].strip() if heading_match else sec
            if not body:
                continue
            _chunk_markdown_section(source, heading, body, sections)


def _load_calibration():
    if not _CALIBRATION_FILE.exists():
        return
    try:
        data = json.loads(_CALIBRATION_FILE.read_text(encoding="utf-8"))
    except Exception:
        return
    sections_cal = _sections_for_source("calibration_store.json")
    for case in data.get("cases", []):
        name = case.get("name", "")
        notes = case.get("notes", "")
        signals_text = []
        for sig in case.get("verified_signals", []):
            year = sig.get("year")
            category = sig.get("category", "")
            actual = sig.get("actual", "")
            matched = sig.get("match", False)
            tag = "✓" if matched else "✗"
            signals_text.append(f"{year}年 {category}: {actual} {tag}")
        heading = f"校准案例 {name}"
        body_parts = [f"案例:{name}"]
        if notes:
            body_parts.append(f"概况: {notes[:150]}")
        if signals_text:
            body_parts.append("事件: " + "; ".join(signals_text))
        _chunks.append({
            "source": "calibration_store.json",
            "heading": heading,
            "text": "\n".join(body_parts),
            "kind": "calibration",
            "categories": list(set(s.get("category", "") for s in case.get("verified_signals", []))),
            "match": all(s.get("match", False) for s in case.get("verified_signals", [])),
            "priority": 1.2,
            "sections": sections_cal,
        })


def _score_chunk(chunk: dict, query_terms: set[str], categories: list[str] | None,
                 year_features: dict | None, rule_signals: list[dict] | None) -> float:
    score = 0.0
    text_full = chunk["heading"] + " " + chunk["text"]
    text_lower = text_full.lower()
    heading_lower = chunk["heading"].lower()

    for term in query_terms:
        t = term.lower()
        if t in heading_lower:
            score += 3.0
        elif t in text_lower:
            score += 2.0

    if categories and chunk.get("categories"):
        overlap = set(categories) & set(chunk["categories"])
        score += len(overlap) * 2.5

    if chunk.get("kind") == "calibration":
        score *= chunk.get("priority", 1.0)

    if year_features:
        feat_text = str(year_features).lower()
        for term in query_terms:
            if term.lower() in feat_text:
                score += 1.0

    if rule_signals:
        for sig in rule_signals:
            cat = sig.get("category", "")
            if cat and cat in text_lower:
                score += 1.0

    return score


def _build_chat_query_terms(chart_data: dict, user_question: str) -> set[str]:
    terms: set[str] = set()
    dm = chart_data.get("day_master", {})
    if dm.get("stem"):
        terms.add(dm["stem"])
    if chart_data.get("pattern"):
        terms.add(chart_data["pattern"])
    ys = chart_data.get("yongshen", {})
    for s in ys.get("favorable", []) + ys.get("harmful", []):
        terms.add(s)
    terms.update(_extract_ngrams(user_question, 2, 6))
    return _expand_synonyms(terms)


def _build_dayun_query_terms(natal: dict, modulations: list[dict]) -> set[str]:
    """从大运解读上下文提取查询词"""
    terms: set[str] = set()
    for k in ("day_master", "pattern", "strength"):
        v = natal.get(k, "")
        if v:
            terms.add(str(v))
    for wx in natal.get("favorable_wuxing", []) + natal.get("harmful_wuxing", []):
        terms.add(str(wx))
    for s in natal.get("favorable", []) + natal.get("harmful", []):
        terms.add(str(s))
    for m in modulations:
        terms.add(m.get("dayun_stem", ""))
        terms.add(m.get("dayun_branch", ""))
        terms.add(m.get("theme", ""))
        for inter in m.get("stem_interactions", []) + m.get("branch_interactions", []):
            terms.update(_extract_ngrams(inter[:20], 2, 5))
    # 假生/贪生忘克/调候等高级概念
    th = natal.get("tiaohou", {})
    if th.get("climate"):
        terms.add("调候")
    terms.add("贪生忘克")
    terms.add("假生陷阱")
    return _expand_synonyms({t for t in terms if t and len(t) >= 2})


def _build_personality_query_terms(data_package: dict) -> set[str]:
    """从性格融合数据包提取查询词"""
    terms: set[str] = set()
    dm = data_package.get("日主", "")
    if dm:
        terms.update(_extract_ngrams(dm, 2, 4))
    if data_package.get("格局"):
        terms.add(data_package["格局"])
    for s in data_package.get("喜用十神", []) + data_package.get("忌十神", []):
        terms.add(str(s))
    # 六维度信号
    dims = data_package.get("六维度信号", {})
    for k, v in dims.items():
        terms.add(k)
        terms.update(_extract_ngrams(str(v)[:50], 2, 4))
    # 病药组合
    for combo in data_package.get("病药组合", []):
        terms.add(combo.get("combo", ""))
        terms.update(_extract_ngrams(combo.get("directive", "")[:50], 2, 4))
    # 特殊组合
    for sc in data_package.get("特殊组合", []):
        terms.update(_extract_ngrams(str(sc)[:50], 2, 4))
    # 压力画像
    stress = data_package.get("压力画像", {})
    for v in stress.values():
        terms.update(_extract_ngrams(str(v)[:50], 2, 4))
    # 家庭
    family = data_package.get("家境背景", {})
    for v in family.values():
        terms.update(_extract_ngrams(str(v)[:50], 2, 4))
    return _expand_synonyms({t for t in terms if t and len(t) >= 2})


# ═══════════════════════════════════════════════════════════════
# 公开检索 API
# ═══════════════════════════════════════════════════════════════

def retrieve_for_review(ctx: dict, top_k: int = 5) -> list[dict]:
    """为流年 LLM 审查检索相关规则/校准片段（向后兼容）"""
    _load_all()
    if not _chunks:
        return []
    terms: set[str] = set()
    natal = ctx.get("natal", {})
    for k in ("day_master", "pattern", "strength"):
        v = natal.get(k, "")
        if v:
            terms.add(str(v))
    for sig in ctx.get("rule_signals", []):
        terms.add(sig.get("category", ""))
        for t in sig.get("triggers", [])[:3]:
            terms.update(_extract_ngrams(t[:20], 2, 5))
    yf = ctx.get("year_features", {})
    for k, v in yf.items():
        terms.add(k)
        terms.update(_extract_ngrams(str(v)[:30], 2, 5))
    liunian = ctx.get("liunian", {})
    if liunian.get("stem"):
        terms.add(liunian["stem"])
    if liunian.get("branch"):
        terms.add(liunian["branch"])
    terms = {t for t in terms if t and len(t) >= 2}
    terms = _expand_synonyms(terms)

    categories = list(set(s.get("category", "") for s in ctx.get("rule_signals", [])))
    year_features = ctx.get("year_features", {})
    rule_signals = ctx.get("rule_signals", [])
    # 仅检索 liunian_review 相关 chunk
    candidates = [c for c in _chunks if "liunian_review" in c.get("sections", _DEFAULT_SECTIONS)]
    scored = [(c, _score_chunk(c, terms, categories, year_features, rule_signals)) for c in candidates]
    scored.sort(key=lambda x: x[1], reverse=True)
    return [c for c, s in scored[:top_k] if s > 0.5]


def retrieve_for_chat(chart_data: dict, user_question: str, top_k: int = 5) -> list[dict]:
    """为 AI 追问检索相关规则/校准片段（向后兼容）"""
    _load_all()
    if not _chunks or not user_question.strip():
        return []
    user_ngrams = set(_extract_ngrams(user_question, 2, 6))
    if not user_ngrams:
        return []
    query_terms = _build_chat_query_terms(chart_data, user_question)
    candidates = [c for c in _chunks if "chat" in c.get("sections", _DEFAULT_SECTIONS)]
    scored = [(c, _score_chunk(c, query_terms, None, None, None)) for c in candidates]
    scored.sort(key=lambda x: x[1], reverse=True)
    top = [c for c, s in scored[:top_k] if s > 0.5]
    if not top:
        return []
    hits = any(
        any(ng in c.get("text", "") or ng in c.get("heading", "") for ng in user_ngrams)
        for c in top
    )
    if not hits:
        return []
    return top


def retrieve_for_generation(section: str, chart_or_ctx: dict,
                             user_question: str | None = None,
                             top_k: int = 5) -> list[dict]:
    """统一生成前检索入口。按 section 过滤 chunk + 构建查询词。

    Args:
        section: "chat" | "liunian_review" | "dayun" | "personality"
        chart_or_ctx: chat → chart_data dict; liunian_review → ctx dict;
                      dayun → {"natal":..., "modulations":...};
                      personality → data_package dict
        user_question: 仅 chat section 使用
        top_k: 返回条数
    """
    _load_all()
    if not _chunks:
        return []

    # 按 section 过滤候选 chunk
    candidates = [c for c in _chunks if section in c.get("sections", _DEFAULT_SECTIONS)]
    if not candidates:
        return []

    if section == "chat":
        return retrieve_for_chat(chart_or_ctx, user_question or "", top_k)

    if section == "liunian_review":
        return retrieve_for_review(chart_or_ctx, top_k)

    if section == "dayun":
        natal = chart_or_ctx.get("natal", {})
        modulations = chart_or_ctx.get("modulations", [])
        query_terms = _build_dayun_query_terms(natal, modulations)
        scored = [(c, _score_chunk(c, query_terms, None, None, None)) for c in candidates]
        scored.sort(key=lambda x: x[1], reverse=True)
        return [c for c, s in scored[:top_k] if s > 0.5]

    if section == "personality":
        _ensure_personality_vectors()
        query_text = _build_personality_query_text(chart_or_ctx)
        query_freq = _build_ngram_freq(query_text)

        vec_candidates = [c for c in candidates if c.get("ngram_freq")]
        if vec_candidates and query_freq:
            scored = [(c, _ngram_cosine_from_freq(query_freq, c["ngram_freq"])) for c in vec_candidates]
            scored.sort(key=lambda x: x[1], reverse=True)
            VEC_THRESHOLD = 0.01
            vec_hits = [c for c, s in scored if s > VEC_THRESHOLD]
            if vec_hits:
                # 向量为主，关键词为次级 tiebreaker
                kw_terms = _build_personality_query_terms(chart_or_ctx)
                final_scored = []
                for c in vec_hits[:top_k]:
                    kw_score = _score_chunk(c, kw_terms, None, None, None) * 0.001
                    vec_score = _ngram_cosine_from_freq(query_freq, c["ngram_freq"])
                    final_scored.append((c, vec_score + kw_score))
                final_scored.sort(key=lambda x: x[1], reverse=True)
                return [c for c, s in final_scored[:top_k]]

        # fallback: 已有关键词检索
        query_terms = _build_personality_query_terms(chart_or_ctx)
        scored = [(c, _score_chunk(c, query_terms, None, None, None)) for c in candidates]
        scored.sort(key=lambda x: x[1], reverse=True)
        return [c for c, s in scored[:top_k] if s > 0.5]

    return []


def format_snippets(snippets: list[dict], max_chars: int = 1800) -> str:
    if not snippets:
        return ""
    lines = ["## 参考规则/校准"]
    total = 0
    for sn in snippets:
        source = sn.get("source", "?")
        heading = sn.get("heading", "")
        text = sn.get("text", "")
        entry = f"[{source}] {heading}: {text}"
        if total + len(entry) > max_chars:
            entry = entry[:max_chars - total - 3] + "..."
            lines.append(entry)
            break
        lines.append(entry)
        total += len(entry)
    return "\n".join(lines)
