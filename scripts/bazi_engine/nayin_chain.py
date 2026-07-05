"""纳音生克链分析 — 年柱纳音为君，月日时纳音为臣

规则来源: advanced-techniques.md §五 纳音实战
验证: WebSearch 2026-05-26
"""

from dataclasses import dataclass

from .enums import Wuxing


def nayin_to_wuxing(nayin_name: str) -> Wuxing | None:
    """从纳音名称提取五行。纳音名末字恒为五行（金/木/水/火/土）。

    Examples:
        "海中金" → Wuxing.金, "炉中火" → Wuxing.火
    """
    if not nayin_name:
        return None
    last = nayin_name[-1]
    mapping = {"金": Wuxing.金, "木": Wuxing.木, "水": Wuxing.水, "火": Wuxing.火, "土": Wuxing.土}
    return mapping.get(last)


from .ten_gods import wuxing_relation as _wx_relation


@dataclass
class NayinRelation:
    relation_type: str       # "年纳音被生" | "年纳音被克" | "年纳音生" | "年纳音克" | "同类比和" | "顺克链" | "逆克链" | "顺生链" | "逆生链"
    from_pillar: str         # 源柱位
    to_pillar: str           # 目标柱位
    from_nayin: str
    to_nayin: str
    chain_order: str = ""    # 全链顺序 如 "年→月→日→时"
    interpretation: str = ""
    auspiciousness: str = ""  # "大吉" | "吉" | "中平" | "凶" | "大凶"

    def to_dict(self) -> dict:
        return {
            "relation_type": self.relation_type,
            "from_pillar": self.from_pillar,
            "to_pillar": self.to_pillar,
            "from_nayin": self.from_nayin,
            "to_nayin": self.to_nayin,
            "chain_order": self.chain_order,
            "interpretation": self.interpretation,
            "auspiciousness": self.auspiciousness,
        }


def detect_nayin_pillar_relations(year_nayin: str, month_nayin: str,
                                   day_nayin: str, hour_nayin: str) -> list[NayinRelation]:
    """检测月/日/时柱纳音与年柱纳音的生克关系。

    规则:
    - 他柱生年柱 → 大吉
    - 他柱克年柱 → 大凶
    - 年柱克他柱 → 中平
    - 年柱生他柱 → 中平偏凶（泄气）
    - 同类比和 → 吉
    """
    year_wx = nayin_to_wuxing(year_nayin)
    if year_wx is None:
        return []

    results: list[NayinRelation] = []
    pillars = [
        ("月柱", month_nayin),
        ("日柱", day_nayin),
        ("时柱", hour_nayin),
    ]

    for pillar_name, p_nayin in pillars:
        p_wx = nayin_to_wuxing(p_nayin)
        if p_wx is None:
            continue

        rel = _wx_relation(p_wx, year_wx)
        # rel is 他柱 → 年柱
        if rel == "生":
            rtype = "他柱生年纳音"
            aup = "大吉"
            interp = f"{pillar_name}纳音({p_nayin})生年柱纳音({year_nayin})——祖业受生，先贫后富，主贵"
        elif rel == "克":
            rtype = "他柱克年纳音"
            aup = "大凶"
            interp = f"{pillar_name}纳音({p_nayin})克年柱纳音({year_nayin})——根基受损，祖业破败"
        elif rel == "被生":
            rtype = "年纳音生他柱"
            aup = "中平偏凶"
            interp = f"年柱纳音({year_nayin})生{pillar_name}纳音({p_nayin})——泄身劳碌，付出多"
        elif rel == "被克":
            rtype = "年纳音克他柱"
            aup = "中平"
            interp = f"年柱纳音({year_nayin})克{pillar_name}纳音({p_nayin})——得财掌控，但压力大"
        else:  # 比和
            rtype = "同类比和"
            aup = "吉"
            interp = f"{pillar_name}纳音({p_nayin})与年柱纳音({year_nayin})同类比和——同心助力，运势顺畅"

        results.append(NayinRelation(
            relation_type=rtype,
            from_pillar=pillar_name,
            to_pillar="年柱",
            from_nayin=p_nayin,
            to_nayin=year_nayin,
            interpretation=interp,
            auspiciousness=aup,
        ))

    return results


def detect_nayin_chain(year_nayin: str, month_nayin: str,
                        day_nayin: str, hour_nayin: str) -> list[NayinRelation]:
    """检测四柱纳音之间的顺序链（顺克/逆克/顺生/逆生）。

    规则:
    - 顺克（年→月→日→时依次相克）：富贵之命
    - 逆克（时→日→月→年依次相克）：破败之命，三起三落
    - 顺生（年→月→日→时依次相生）：泄气劳碌
    - 逆生（时→日→月→年依次相生）：大贵之命

    至少需3个连续柱位参与同向关系才构成链。
    """
    year_wx = nayin_to_wuxing(year_nayin)
    month_wx = nayin_to_wuxing(month_nayin)
    day_wx = nayin_to_wuxing(day_nayin)
    hour_wx = nayin_to_wuxing(hour_nayin)

    if any(w is None for w in [year_wx, month_wx, day_wx, hour_wx]):
        return []

    pillars = [
        ("年柱", year_nayin, year_wx),
        ("月柱", month_nayin, month_wx),
        ("日柱", day_nayin, day_wx),
        ("时柱", hour_nayin, hour_wx),
    ]

    results: list[NayinRelation] = []

    # 检查相邻柱位的关系方向
    def chain_check(pairs: list[tuple[str, str, str, str, Wuxing, Wuxing]]) -> list[NayinRelation]:
        """检查连续关系是否构成链。pairs: [(from_label, to_label, from_nayin, to_nayin, from_wx, to_wx)]"""
        chain_results: list[NayinRelation] = []
        rel_types = []
        for from_lbl, to_lbl, f_nay, t_nay, f_wx, t_wx in pairs:
            rel = _wx_relation(f_wx, t_wx)
            rel_types.append(rel)

        # 全克 → 顺克链
        if all(r == "克" for r in rel_types):
            order = "年→月→日→时"
            chain_results.append(NayinRelation(
                relation_type="顺克链",
                from_pillar="年柱",
                to_pillar="时柱",
                from_nayin=year_nayin,
                to_nayin=hour_nayin,
                chain_order=order,
                interpretation="四柱纳音顺次相克（年→月→日→时），为顺克格——多主富贵之命，自上而下掌控得力",
                auspiciousness="大吉",
            ))
        # 全被克（即逆克：时克日→日克月→月克年）
        if all(r == "被克" for r in rel_types):
            order = "时→日→月→年"
            chain_results.append(NayinRelation(
                relation_type="逆克链",
                from_pillar="时柱",
                to_pillar="年柱",
                from_nayin=hour_nayin,
                to_nayin=year_nayin,
                chain_order=order,
                interpretation="四柱纳音逆次相克（时→日→月→年），为逆克格——多主破败之命，三起三落，伤克长辈",
                auspiciousness="大凶",
            ))
        # 全生 → 顺生链
        if all(r == "生" for r in rel_types):
            order = "年→月→日→时"
            chain_results.append(NayinRelation(
                relation_type="顺生链",
                from_pillar="年柱",
                to_pillar="时柱",
                from_nayin=year_nayin,
                to_nayin=hour_nayin,
                chain_order=order,
                interpretation="四柱纳音顺次相生（年→月→日→时），为顺生格——表面流通但年命被层层盗泄，一生劳碌难成",
                auspiciousness="中平偏凶",
            ))
        # 全被生（即逆生：时生→日生→月生→年）
        if all(r == "被生" for r in rel_types):
            order = "时→日→月→年"
            chain_results.append(NayinRelation(
                relation_type="逆生链",
                from_pillar="时柱",
                to_pillar="年柱",
                from_nayin=hour_nayin,
                to_nayin=year_nayin,
                chain_order=order,
                interpretation="四柱纳音逆次相生（时→日→月→年），为逆生格——多主贵气，有名望，得晚辈助力",
                auspiciousness="大吉",
            ))

        return chain_results

    # 年→月→日
    ym_pairs = [("年柱", "月柱", year_nayin, month_nayin, year_wx, month_wx),
                 ("月柱", "日柱", month_nayin, day_nayin, month_wx, day_wx)]
    results.extend(chain_check(ym_pairs))

    # 月→日→时
    mh_pairs = [("月柱", "日柱", month_nayin, day_nayin, month_wx, day_wx),
                 ("日柱", "时柱", day_nayin, hour_nayin, day_wx, hour_wx)]
    results.extend(chain_check(mh_pairs))

    # 年→月→日→时 (full)
    full_pairs = [("年柱", "月柱", year_nayin, month_nayin, year_wx, month_wx),
                  ("月柱", "日柱", month_nayin, day_nayin, month_wx, day_wx),
                  ("日柱", "时柱", day_nayin, hour_nayin, day_wx, hour_wx)]
    results.extend(chain_check(full_pairs))

    return results


def find_all_nayin_relations(year_nayin: str, month_nayin: str,
                              day_nayin: str, hour_nayin: str) -> list[NayinRelation]:
    """收集器: 检测所有纳音关系"""
    results: list[NayinRelation] = []
    results.extend(detect_nayin_pillar_relations(year_nayin, month_nayin, day_nayin, hour_nayin))
    results.extend(detect_nayin_chain(year_nayin, month_nayin, day_nayin, hour_nayin))
    return results
