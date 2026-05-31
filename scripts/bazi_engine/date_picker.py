"""择日功能 — 在指定日期范围内筛选吉日（v2: 完整评分体系）

调用方式:
    from .date_picker import pick_good_dates
    results = pick_good_dates(chart, start_date, end_date, yongshen_data=None)

评分维度:
  +2 日支六合日柱  +1~3 天干五合四柱  +1 三合命局  +1 贵人日
  +2 用神日  +1 建除吉日
  -2 日支冲日柱/年柱/命宫  -1 相害  -2 三刑  -2 空亡日
  -2 忌神日  -1 建除凶日

Returns:
    list[{date, score, good_tags, bad_tags, reasons}], sorted by score desc
"""
from datetime import date, timedelta

from ._constants import (
    DIZHI_LIUHE, DIZHI_LIUCHONG, DIZHI_XIANGHAI, DIZHI_XIANGXING,
    DIZHI_SANHE, TIANGAN_WUHE_PAIRS, KONGWANG,
    TIANYI_GUIREN, tianyi_guiren_by_stem,
    WENCHANG, YIMA, FUXING_GUIREN, TAIJI_GUIREN,
    HONGLUAN, HUAGAI, STEM_TO_WUXING,
)
from .day_pillar_db import lookup_day_pillar
from .enums import Tiangan, Dizhi


# ═══════════════════════════════════════════════════════════════
# 十二建除 — 以月支定建日，推算每日建除
# 口诀: 正月建寅, 二月建卯... 建日之后依次为: 建-除-满-平-定-执-破-危-成-收-开-闭
# ═══════════════════════════════════════════════════════════════

_JIANCHU_NAMES = ["建", "除", "满", "平", "定", "执", "破", "危", "成", "收", "开", "闭"]

# 建除吉凶: 开日大吉, 成日小吉; 闭日百事不宜, 破日大凶
_JIANCHU_JIXIONG: dict[str, int] = {
    "开": 2, "成": 1, "除": 1,
    "建": 0, "满": 0, "平": 0, "定": 0, "执": 0, "危": 0, "收": 0,
    "闭": -2, "破": -3,
}

# 地支→序号 (子=1...亥=12)
_DZ_INDEX = {
    Dizhi.子: 1, Dizhi.丑: 2, Dizhi.寅: 3, Dizhi.卯: 4,
    Dizhi.辰: 5, Dizhi.巳: 6, Dizhi.午: 7, Dizhi.未: 8,
    Dizhi.申: 9, Dizhi.酉: 10, Dizhi.戌: 11, Dizhi.亥: 12,
}
_DZ_BY_INDEX = {v: k for k, v in _DZ_INDEX.items()}


def _day_ganzhi(d: date) -> tuple[Tiangan, Dizhi]:
    """查表获取任意日期的干支"""
    tg_str, dz_str = lookup_day_pillar(d.year, d.month, d.day)
    return Tiangan(tg_str), Dizhi(dz_str)


def _month_dz(month: int) -> Dizhi:
    """月支：寅=1月...丑=12月"""
    return _DZ_BY_INDEX[((month - 1) % 12) + 1]


def _jianchu(day_dz: Dizhi, month_dz: Dizhi) -> str:
    """计算当日建除"""
    day_idx = _DZ_INDEX[day_dz]
    month_idx = _DZ_INDEX[month_dz]
    offset = (day_idx - month_idx) % 12
    return _JIANCHU_NAMES[offset]


def _xun_index(day_tg: Tiangan, day_dz: Dizhi) -> int:
    """计算旬序号 (0-5)，用于查空亡"""
    tg_idx = list(Tiangan).index(day_tg)
    dz_idx = list(Dizhi).index(day_dz)
    # 旬序 = floor(tg_idx / 2) but adjusted for 甲子旬=0
    # 甲子旬: 甲子→0, 甲戌旬: 甲戌→1, ... 甲寅旬: 甲寅→5
    return ((tg_idx - dz_idx) % 10) // 2


def _check_spirit(day_dz: Dizhi, day_tg: Tiangan, chart_tg_zhi: list[tuple[Tiangan, Dizhi]]) -> list[str]:
    """检查当日是否命中命主神煞"""
    hits = []
    day_dz_val = day_dz

    # 天乙贵人 — 按日干查
    guiren = tianyi_guiren_by_stem(chart_tg_zhi[2][0])  # 日干
    if guiren and day_dz_val in guiren:
        hits.append("天乙贵人日")

    # 文昌 — 按日干查
    wc = WENCHANG.get(chart_tg_zhi[2][0])
    if wc and day_dz_val == wc:
        hits.append("文昌日")

    # 驿马 — 按年支/日支查
    ym = YIMA.get(chart_tg_zhi[2][1])  # 日支
    if ym and day_dz_val == ym:
        hits.append("驿马日")

    # 红鸾 — 按日支查
    hl = HONGLUAN.get(chart_tg_zhi[2][1])
    if hl and day_dz_val == hl:
        hits.append("红鸾日")

    # 福星贵人 — 按日干查
    fu = FUXING_GUIREN.get(chart_tg_zhi[2][0])
    if fu and day_dz_val in fu:
        hits.append("福星贵人日")

    return hits


def _day_wuxing(day_tg: Tiangan) -> str:
    """日干五行（字符串）"""
    return STEM_TO_WUXING.get(day_tg.value, "土")


def pick_good_dates(
    chart,
    start_date: date,
    end_date: date,
    yongshen_data: dict | None = None,
) -> list[dict]:
    """完整择日评分。

    chart: 需提供 .year.branch, .month.branch, .day.branch, .day.stem
           以及可选的 .minggong_branch, .shengong_branch, .taiyuan_branch
    yongshen_data: {"favorable_wuxing": ["木","火"], "harmful_wuxing": ["金","水"]} 等

    Returns:
        [{date: "2025-06-15", score: 3, good_tags: [...], bad_tags: [...], reasons: [...]}]
        按 score 降序排列
    """
    # 命主四柱干支列表: [(年干,年支), (月干,月支), (日干,日支), (时干,时支)]
    chart_tg_zhi = [
        (chart.year.stem, chart.year.branch),
        (chart.month.stem, chart.month.branch),
        (chart.day.stem, chart.day.branch),
        (chart.hour.stem, chart.hour.branch),
    ]
    day_master_dz = chart.day.branch  # 命主日支
    year_dz = chart.year.branch       # 命主年支

    # 命宫/身宫/胎元地支（如有）
    extra_dz = []
    for attr in ('minggong_branch', 'shengong_branch', 'taiyuan_branch'):
        v = getattr(chart, attr, None)
        if v:
            extra_dz.append(v)

    # 用神/忌神五行
    fav_wuxing = set()
    harm_wuxing = set()
    if yongshen_data:
        fav_wuxing = set(yongshen_data.get("favorable_wuxing", []))
        harm_wuxing = set(yongshen_data.get("harmful_wuxing", []))

    results = []

    for n in range((end_date - start_date).days + 1):
        d = start_date + timedelta(days=n)
        day_tg, day_dz = _day_ganzhi(d)
        month_dz = _month_dz(d.month)

        score = 0
        good_tags = []
        bad_tags = []
        reasons = []

        # ═══════════ 吉项 ═══════════

        # 1. 地支六合 — 当日支与命主日支
        for a, b in DIZHI_LIUHE:
            if (day_dz == a and day_master_dz == b) or (day_dz == b and day_master_dz == a):
                score += 2
                good_tags.append("六合日柱")
                reasons.append(f"当日{day_dz.value}与命主日支{day_master_dz.value}六合——天时地利人和")
                break

        # 2. 天干五合 — 当日干与命主四柱天干
        for tg, dz in chart_tg_zhi:
            for (a, b) in TIANGAN_WUHE_PAIRS:
                if (day_tg == a and tg == b) or (day_tg == b and tg == a):
                    pillar_label = "日干" if (tg, dz) == chart_tg_zhi[2] else "命局天干"
                    score += 2 if (tg, dz) == chart_tg_zhi[2] else 1
                    good_tags.append(f"天合{pillar_label}")
                    reasons.append(f"当日干{day_tg.value}与{pillar_label}{tg.value}五合——气场相投")
                    break

        # 3. 三合 — 当日支与命局地支
        for sanhe_group in DIZHI_SANHE:
            if day_dz in sanhe_group:
                for tdz in [y for _, y in chart_tg_zhi] + extra_dz:
                    if tdz in sanhe_group and tdz != day_dz:
                        score += 1
                        good_tags.append("三合命局")
                        reasons.append(f"当日{day_dz.value}与命局{tdz.value}三合——能量共振")
                        break
                break

        # 4. 神煞贵人
        spirit_hits = _check_spirit(day_dz, day_tg, chart_tg_zhi)
        spirit_bonus = min(len(spirit_hits), 2)  # cap +2
        if spirit_bonus:
            score += spirit_bonus
            good_tags.extend(spirit_hits[:2])
            reasons.append(f"贵人加持: {'、'.join(spirit_hits[:2])}")

        # 5. 用神日 — 当日干五行是否为命主喜用
        dw = _day_wuxing(day_tg)
        if fav_wuxing and dw in fav_wuxing:
            score += 2
            good_tags.append("用神日")
            reasons.append(f"当日五行{dw}为命主喜用——事半功倍")
        elif harm_wuxing and dw in harm_wuxing:
            score -= 2
            bad_tags.append("忌神日")
            reasons.append(f"当日五行{dw}为命主忌神——事倍功半")

        # 6. 十二建除
        jc = _jianchu(day_dz, month_dz)
        jc_score = _JIANCHU_JIXIONG.get(jc, 0)
        if jc_score > 0:
            score += jc_score
            good_tags.append(f"{jc}日")
            reasons.append(f"建除{jc}日——{'大吉' if jc == '开' else '小吉'}")
        elif jc_score < 0:
            score += jc_score
            bad_tags.append(f"{jc}日")
            reasons.append(f"建除{jc}日——{'百事不宜' if jc == '闭' else '大凶之日'}")

        # ═══════════ 凶项 ═══════════

        # 7. 六冲 — 当日支冲命主日柱/年柱/命宫
        for label, target_dz in [("日柱", day_master_dz), ("年柱", year_dz)] + \
                                 [(f"命宫/{attr}", dz) for attr, dz in
                                  [("命宫", getattr(chart, 'minggong_branch', None)),
                                   ("身宫", getattr(chart, 'shengong_branch', None))] if dz]:
            if (day_dz, target_dz) in DIZHI_LIUCHONG:
                score -= 2
                bad_tags.append(f"冲{label}")
                reasons.append(f"当日{day_dz.value}冲{label}{target_dz.value}——根基动摇")
                break

        # 8. 相害
        if (day_dz, day_master_dz) in DIZHI_XIANGHAI:
            score -= 1
            bad_tags.append("害日柱")
            reasons.append("日柱被害——易有人际摩擦")

        # 9. 三刑
        for a, b in DIZHI_XIANGXING:
            if day_dz == a:
                for _, tdz in chart_tg_zhi:
                    if tdz == b:
                        score -= 2
                        bad_tags.append("三刑")
                        reasons.append(f"当日{day_dz.value}与命局{tdz.value}相刑——口舌是非")
                        break
                if day_master_dz == b or day_dz == b:
                    break

        # 10. 空亡日 — 当日干支所在旬的空亡地支
        xun = _xun_index(day_tg, day_dz)
        kong_dz = KONGWANG.get(xun, ())
        if day_dz in kong_dz:
            score -= 2
            bad_tags.append("空亡日")
            reasons.append(f"当日{day_dz.value}值旬空——诸事虚而不实")

        results.append({
            "date": d.isoformat(),
            "score": score,
            "good_tags": good_tags,
            "bad_tags": bad_tags,
            "reasons": reasons,
            "jianchu": jc,
            "day_ganzhi": f"{day_tg.value}{day_dz.value}",
        })

    # 按评分降序
    results.sort(key=lambda x: x["score"], reverse=True)
    return results
