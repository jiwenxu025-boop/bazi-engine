"""粒度性格特质计算"""
from ..enums import Tiangan, Dizhi, Shishen


def _compute_shishen_sub_traits(weighted_scores,
                                min_score: float = 2.0) -> list[dict]:
    """十神分数达标时激活对应子特质"""
    results: list[dict] = []
    for shishen, score in sorted(weighted_scores.items(), key=lambda x: x[1], reverse=True):
        if score < min_score:
            continue
        sub_traits_list = SHISHEN_SUB_TRAITS.get(shishen, [])
        for st in sub_traits_list:
            if score >= st["trigger_score"]:
                results.append({
                    "shishen": shishen,
                    "score": round(score, 1),
                    "trait_name": st["name"],
                    "description": st["description"],
                    "source": st["source"],
                })
    return results

def _compute_shishen_combo_traits(weighted_scores) -> list[dict]:
    """十神配对均达标时激活组合特质"""
    results: list[dict] = []
    for entry in SHISHEN_COMBINATION_TRAITS:
        combo = entry["combo"]
        threshold = entry["min_each_score"]
        all_met = True
        combo_scores = {}
        for shishen in combo:
            s = weighted_scores.get(shishen, 0)
            combo_scores[shishen] = round(s, 1)
            if s < threshold:
                all_met = False
                break
        if all_met:
            results.append({
                "combo": " + ".join(combo),
                "trait": entry["trait"],
                "description": entry["description"],
                "source": entry["source"],
                "scores": combo_scores,
            })
    return results

def _compute_dizhi_traits(interactions: dict,
                          pillars_data: list[dict] | None = None) -> list[dict]:
    """从地支关系提取性格倾向"""
    results: list[dict] = []
    dizhi_list = interactions.get("dizhi", []) if interactions else []

    # 收集命局所有地支
    all_branches = set()
    if pillars_data:
        for p in pillars_data:
            b = p.get("branch", "")
            if b:
                all_branches.add(b)

    for item in dizhi_list:
        rel_type = item.get("type", "")
        branches = item.get("branches", [])
        if isinstance(branches, list):
            branch_str = "".join(branches)
        else:
            branch_str = str(branches)

        # 六冲
        if rel_type == "六冲":
            key = f"{branch_str}_冲"
            d = DIZHI_RELATION_PERSONALITY.get(key)
            if not d:
                # try checking specific combos
                for k in ["辰戌_冲", "丑未_冲", "子午_冲", "卯酉_冲", "寅申_冲", "巳亥_冲"]:
                    if all(b in branch_str for b in k.split("_")[0]):
                        d = DIZHI_RELATION_PERSONALITY.get(k)
                        break
            if d:
                results.append({
                    "relation": f"{branch_str}六冲",
                    "trait": d["trait"],
                    "description": d["description"],
                    "source": d["source"],
                    "involved_pillars": item.get("pillars", []),
                })

        # 自刑
        if rel_type == "自刑":
            branches_list = item.get("branches", [])
            if isinstance(branches_list, list) and branches_list:
                b = branches_list[0]
                key = f"{b}_自刑"
                d = DIZHI_RELATION_PERSONALITY.get(key)
                if d:
                    results.append({
                        "relation": f"{b}自刑",
                        "trait": d["trait"],
                        "description": d["description"],
                        "source": d["source"],
                        "involved_pillars": item.get("pillars", []),
                    })

        # 三刑
        if rel_type in ("三刑", "相刑"):
            branches_sorted = sorted(item.get("branches", []))
            key = "_".join(branches_sorted) + "_刑"
            d = DIZHI_RELATION_PERSONALITY.get(key)
            if d:
                results.append({
                    "relation": f"{''.join(branches_sorted)}相刑",
                    "trait": d["trait"],
                    "description": d["description"],
                    "source": d["source"],
                    "involved_pillars": item.get("pillars", []),
                })

    # 命局自刑统计（>1个自刑时触发）
    total_self_punish = sum(1 for b in all_branches if b in ("辰", "午", "酉", "亥"))
    if total_self_punish >= 2:
        d = DIZHI_RELATION_PERSONALITY.get("辰_午_酉_亥_自刑")
        if d:
            already = any(r["trait"] == d["trait"] for r in results)
            if not already:
                results.append({
                    "relation": "多自刑",
                    "trait": d["trait"],
                    "description": d["description"],
                    "source": d["source"],
                    "involved_pillars": [],
                })

    return results

def _compute_hidden_stem_personality(pillars_data: list[dict]) -> list[dict]:
    """四柱藏干十神→性格特质

    每个地支的藏干都是性格拼图的一部分：
    - 年支藏干 → 家族底色、童年形成的性格倾向
    - 月支藏干 → 父母影响、青年期形成的思维模式
    - 日支藏干 → 核心自我、婚姻观（内在性格的底层驱动力）
    - 时支藏干 → 晚年倾向、对子女的态度、深层追求

    阈值比十神加权低 0.5——藏干是隐性力量，不需要全局強勢就能影响性格。"""
    pillar_labels = {"年柱": "年支", "月柱": "月支", "日柱": "日支", "时柱": "时支"}
    results: list[dict] = []

    for p in pillars_data:
        pillar_type = p.get("pillar_type", "")
        branch = p.get("branch", "")
        pillar_tag = pillar_labels.get(pillar_type, pillar_type)
        hidden_ten_gods = p.get("hidden_ten_gods", [])
        hidden_stems = p.get("hidden_stems", [])

        for i, tg_name in enumerate(hidden_ten_gods):
            hs_entry = hidden_stems[i] if i < len(hidden_stems) else {}
            hs_stem = hs_entry.get("stem", "") if isinstance(hs_entry, dict) else str(hs_entry)
            depth = "本气" if i == 0 else ("中气" if i == 1 else "余气")
            sub_traits_list = SHISHEN_SUB_TRAITS.get(tg_name, [])

            depth_score = 2.5 if depth == "本气" else (2.0 if depth == "中气" else 1.5)

            for st in sub_traits_list:
                adjusted_trigger = max(1.0, st["trigger_score"] - 0.5)
                if depth_score >= adjusted_trigger:
                    results.append({
                        "source_type": f"{pillar_tag}{branch}藏{hs_stem}{tg_name}({depth})",
                        "pillar_type": pillar_type,
                        "shishen": tg_name,
                        "trait_name": st["name"],
                        "description": st["description"],
                        "source": st["source"],
                        "depth": depth,
                    })

    return results

