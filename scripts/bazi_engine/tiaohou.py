"""调候独立分析维度

来源: 陆致极《八字命理学进阶教程》"调候为先"原则 + 《穷通宝鉴》十天干调候
核心: 调候不是用神的附属品，是独立于格局/强弱的第一优先维度。
      缺调候的命局为"废局"——格局再美也难以发挥。

v0.8.0: +假生陷阱检测（水冷木冻/燥土脆金）
"""

from dataclasses import dataclass, field
from .enums import Tiangan, Dizhi, Wuxing
from .ten_gods import wuxing_sheng, wuxing_ke


@dataclass
class TiaohouResult:
    """调候分析结果"""
    season: str                # "春"/"夏"/"秋"/"冬"
    climate: str               # "中和"/"偏燥"/"偏寒"/"大燥"/"大寒"
    is_fei_ju: bool            # 是否为废局（缺调候=格局难以发挥）
    tiaohou_wuxing: list[str]  # 调候所需五行
    reason: str                # 解释
    priority_note: str         # 优先级提示

    def to_dict(self) -> dict:
        return {
            "season": self.season,
            "climate": self.climate,
            "is_fei_ju": self.is_fei_ju,
            "tiaohou_wuxing": self.tiaohou_wuxing,
            "reason": self.reason,
            "priority_note": self.priority_note,
        }


def analyze_tiaohou(day_master: Tiangan, month_branch: Dizhi,
                    day_branch: Dizhi, all_branches: list[Dizhi],
                    all_stems: list[Tiangan] | None = None) -> TiaohouResult:
    """独立的调候分析——陆致极"调候为先"原则。

    优先级: 调候 > 格局 > 强弱
    """
    dm_wx = day_master.wuxing.value
    month_idx = month_branch.index

    # 季节划分: 0=子(冬11), 1=丑(冬12), 2=寅(春1), 3=卯(春2), 4=辰(春3)
    #           5=巳(夏4), 6=午(夏5), 7=未(夏6), 8=申(秋7), 9=酉(秋8)
    #           10=戌(秋9), 11=亥(冬10)
    if month_idx in (2, 3, 4):
        season = "春"
    elif month_idx in (5, 6, 7):
        season = "夏"
    elif month_idx in (8, 9, 10):
        season = "秋"
    else:
        season = "冬"

    # 统计全局五行分布来判断燥寒
    wx_counts = {"木": 0, "火": 0, "土": 0, "金": 0, "水": 0}
    for dz in all_branches:
        wx = dz.wuxing.value
        wx_counts[wx] = wx_counts.get(wx, 0) + 1
    # v0.13.0: 天干也参与气候计数（权重0.5，天干为表，地支为根）
    if all_stems:
        for tg in all_stems:
            wx = tg.wuxing.value
            wx_counts[wx] = wx_counts.get(wx, 0) + 0.5

    fire_count = wx_counts["火"]
    water_count = wx_counts["水"]
    metal_count = wx_counts["金"]

    # ── 调候规则（《穷通宝鉴》核心，陆致极系统化）──
    tiaohou_map = {
        # 金日主
        ("金", "夏"): (["水"], "夏金遇火熔，急需水来调候降温，无水则为废局"),
        ("金", "冬"): (["火"], "冬金水冷金寒，急需火来暖局调候，无火则寒金不锐"),
        # 木日主
        ("木", "冬"): (["火"], "冬木水冷根寒，急需火来暖局解冻，无火则生机不展"),
        ("木", "秋"): (["水"], "秋木凋零，需水滋润，金旺克木需水通关"),
        # 水日主
        ("水", "夏"): (["金", "水"], "夏水被火蒸涸，急需金来发源、水来助势"),
        ("水", "冬"): (["火"], "冬水冰寒凝结，急需火来暖局解冻，无火则死水一潭"),
        # 火日主
        ("火", "冬"): (["木"], "冬火微弱近灭，急需木来为薪续燃，无木则火灭"),
        ("火", "秋"): (["木"], "秋火金多火弱，需木为燃料续燃"),
        # 土日主
        ("土", "夏"): (["水"], "夏土火旺土燥，急需水来润泽调候，无水则土裂不生"),
        ("土", "冬"): (["火"], "冬土水冷土冻，急需火来暖局调候，无火则冻土无用"),
        ("土", "春"): (["火"], "春土木旺克土，需火化木生土"),
    }

    key = (dm_wx, season)
    tiaohou_info = tiaohou_map.get(key)
    need_wx = tiaohou_info[0] if tiaohou_info else []
    tiaohou_reason = tiaohou_info[1] if tiaohou_info else ""

    # 判断废局: 调候五行在四柱中完全缺失
    has_tiaohou = False
    for wx in need_wx:
        if wx_counts.get(wx, 0) >= 1:
            has_tiaohou = True
            break

    # 也检查藏干（通过纳音间接）
    # 简化: 如果调候需要的五行在地支中完全没有，则为废局

    is_fei_ju = bool(need_wx) and not has_tiaohou

    # 气候判定（v0.13.0: 含天干0.5权重，零值容忍<0.5）
    if fire_count >= 3 and water_count < 0.5:
        climate = "大燥"
    elif water_count >= 3 and fire_count < 0.5:
        climate = "大寒"
    elif fire_count >= 2 and water_count <= 1:
        climate = "偏燥"
    elif water_count >= 2 and fire_count <= 1:
        climate = "偏寒"
    else:
        climate = "中和"

    # 优先级提示
    if is_fei_ju:
        priority_note = (
            f"⚠ 废局：命局缺调候用神{'/'.join(need_wx)}。"
            f"陆致极《进阶教程》：「失去调候要素的命局为废局，格局再美也难发挥」。"
            f"建议优先看大运是否补足调候，原局分析须降低格局层次预期。"
        )
    elif need_wx:
        priority_note = (
            f"调候需求：{'/'.join(need_wx)}。原局有调候基础，格局可正常发挥。"
        )
    else:
        priority_note = "原局寒暖燥湿适中，调候无忧。"

    return TiaohouResult(
        season=season,
        climate=climate,
        is_fei_ju=is_fei_ju,
        tiaohou_wuxing=need_wx,
        reason=tiaohou_reason,
        priority_note=priority_note,
    )


# ═══════════════════════════════════════════════════════════════
# 假生陷阱检测（v0.8.0）
# ═══════════════════════════════════════════════════════════════

@dataclass
class FalseGeneration:
    """假生陷阱：表面相生实则相害的材质变异"""
    subject: str          # 受生方描述
    source: str           # 生方描述
    condition: str        # 触发条件
    effect: str           # 实际效果
    severity: int         # 严重程度: 1=弱假生, 2=强假生
    fix_wuxing: list[str] # 解救五行


def detect_false_generation(day_master: Tiangan, all_stems: list[Tiangan],
                            all_branches: list[Dizhi]) -> list[FalseGeneration]:
    """检测假生陷阱——材质变异导致的生扶失效。

    规则来源:
    - 《穷通宝鉴》："水冷木冻，无火则木不荣"
    - 《滴天髓》："燥土脆金，金见土多则埋"
    - 梁湘润《八字实务》："湿木不生火，寒金不制木"
    """
    results: list[FalseGeneration] = []

    dm_wx = day_master.wuxing
    dm_val = day_master.value

    # 统计全局天干五行
    stem_wx_set = {s.wuxing for s in all_stems}
    has_fire_stem = Wuxing.火 in stem_wx_set
    has_water_stem = Wuxing.水 in stem_wx_set

    # 统计地支藏干五行（通过本气）
    branch_wx_set = {b.wuxing for b in all_branches}
    has_fire_branch = Wuxing.火 in branch_wx_set
    has_water_branch = Wuxing.水 in branch_wx_set

    has_fire_any = has_fire_stem or has_fire_branch
    has_water_any = has_water_stem or has_water_branch

    # 统计地支中的燥土/湿土
    dry_earth = [b for b in all_branches if b in (Dizhi.戌, Dizhi.未)]
    wet_water = [b for b in all_branches if b in (Dizhi.亥, Dizhi.子)]

    # ── 规则1: 水冷木冻 ──
    # 乙木日主 + 原局有亥/子水 + 全局无丙火（含地支） → 水不生木反冻木
    if dm_wx == Wuxing.木 and wet_water:
        if not has_fire_any:
            results.append(FalseGeneration(
                subject=f"{dm_val}木日主",
                source=f"亥/子水",
                condition="全局无火（丙火），水冷木冻",
                effect="水不生木反冻木，印星（水）转化为忌神，木生机受阻",
                severity=2,
                fix_wuxing=["火"],
            ))
        elif has_fire_branch and not has_fire_stem:
            # 地支有火但天干不透 → 部分缓解
            results.append(FalseGeneration(
                subject=f"{dm_val}木日主",
                source=f"亥/子水",
                condition="火藏地支不透，水冷木微冻",
                effect="水生木但生机受限，印星生扶打折",
                severity=1,
                fix_wuxing=["火"],
            ))

    # ── 规则2: 燥土脆金/埋金 ──
    # 庚/辛金日主 + 原局有戌/未土 + 全局无水润 → 土不生金反脆金
    if dm_wx == Wuxing.金 and dry_earth:
        if not has_water_any:
            results.append(FalseGeneration(
                subject=f"{dm_val}金日主",
                source=f"戌/未燥土",
                condition="全局无水润燥，燥土脆金",
                effect="土不生金反脆金，印星（土）转化为忌神，金被燥土所伤",
                severity=2,
                fix_wuxing=["水"],
            ))
        elif has_water_branch and not has_water_stem:
            results.append(FalseGeneration(
                subject=f"{dm_val}金日主",
                source=f"戌/未燥土",
                condition="水藏地支不透，燥土微脆金",
                effect="土生金但力量打折，印星生扶受限",
                severity=1,
                fix_wuxing=["水"],
            ))

    # ── 规则3: 湿木不生火 ──
    # 丙/丁火日主 + 原局有亥子水 + 木多 → 木被水浸湿，生火力弱
    if dm_wx == Wuxing.火 and wet_water:
        wood_count = sum(1 for b in all_branches if b.wuxing == Wuxing.木)
        if wood_count >= 2 and not has_fire_stem:
            results.append(FalseGeneration(
                subject=f"{dm_val}火日主",
                source="木（印星）",
                condition="水多木湿+天干无火，湿木不生火",
                effect="木不生火反晦火，印星生扶无效",
                severity=1,
                fix_wuxing=["火"],
            ))

    # ── 规则4: 火炎土焦 ──
    # 戊/己土日主 + 原局巳午火多 + 全局无水润 → 火不生土反焦土
    if dm_wx == Wuxing.土:
        fire_branches = [b for b in all_branches if b in (Dizhi.巳, Dizhi.午)]
        if len(fire_branches) >= 2 and not has_water_any:
            results.append(FalseGeneration(
                subject=f"{dm_val}土日主",
                source="巳/午火（印星）",
                condition="火炎土焦，全局无水润泽",
                effect="火不生土反焦土，印星转化为忌神，土裂无用",
                severity=2,
                fix_wuxing=["水"],
            ))
        elif len(fire_branches) >= 2 and has_water_branch and not has_water_stem:
            results.append(FalseGeneration(
                subject=f"{dm_val}土日主",
                source="巳/午火（印星）",
                condition="火旺土燥，水藏不透",
                effect="火生土但土质干燥，印星生扶打折",
                severity=1,
                fix_wuxing=["水"],
            ))

    # ── 规则5: 金多水浊 ──
    # 壬/癸水日主 + 原局申酉金多 + 无木火疏通 → 金多反浊水
    if dm_wx == Wuxing.水:
        metal_branches = [b for b in all_branches if b in (Dizhi.申, Dizhi.酉)]
        fire_wood = [b for b in all_branches if b.wuxing in (Wuxing.火, Wuxing.木)]
        if len(metal_branches) >= 2 and not fire_wood:
            results.append(FalseGeneration(
                subject=f"{dm_val}水日主",
                source="申/酉金（印星）",
                condition="金多水浊，全局无木火疏通",
                effect="金不生水反浊水，印星过重反成浑浊，水不清则智不明",
                severity=2,
                fix_wuxing=["木", "火"],
            ))
        elif len(metal_branches) >= 2 and not has_fire_stem:
            results.append(FalseGeneration(
                subject=f"{dm_val}水日主",
                source="申/酉金（印星）",
                condition="金多水微浊，火藏不透",
                effect="金生水但水质受损，印星生扶打折",
                severity=1,
                fix_wuxing=["火"],
            ))

    # ── 规则6: 土重金埋 ──
    # 庚/辛金日主 + 原局辰戌丑未土>=3 → 土多埋金，非生金
    if dm_wx == Wuxing.金:
        all_earth = [b for b in all_branches if b in (Dizhi.辰, Dizhi.戌, Dizhi.丑, Dizhi.未)]
        if len(all_earth) >= 3:
            results.append(FalseGeneration(
                subject=f"{dm_val}金日主",
                source="辰戌丑未土（印星）",
                condition=f"全局{len(all_earth)}重土，土重金埋",
                effect="土不生金反埋金，印星过重压抑日主，金被埋没难出头",
                severity=2,
                fix_wuxing=["木"],
            ))

    return results


# ═══════════════════════════════════════════════════════════════
# 调候→健康映射（v0.10.0: 引擎一——气候→慢性病体质筛查）
# ═══════════════════════════════════════════════════════════════

# 古籍依据：《黄帝内经》五行脏腑对应 + 气候偏枯致病机理
WUXING_ORGAN_MAP = {
    "木": {"脏": "肝", "腑": "胆", "体": "筋", "窍": "目",
           "excess": "肝气郁结/易怒/偏头痛/乳腺/胁痛",
           "deficit": "肝血不足/视力减退/筋骨酸软/易抽筋"},
    "火": {"脏": "心", "腑": "小肠", "体": "脉", "窍": "舌",
           "excess": "心火上炎/失眠心悸/口腔溃疡/高血压/躁狂",
           "deficit": "心气不足/畏寒肢冷/语声低微/心律不齐"},
    "土": {"脏": "脾", "腑": "胃", "体": "肌肉", "窍": "口",
           "excess": "脾胃湿热/消化不良/结石/肥胖/代谢综合征",
           "deficit": "脾胃虚弱/食欲不振/消瘦/气血不足/胃下垂"},
    "金": {"脏": "肺", "腑": "大肠", "体": "皮毛", "窍": "鼻",
           "excess": "肺燥咳嗽/便秘/皮肤过敏/哮喘/鼻炎",
           "deficit": "肺气不足/易感冒/自汗/皮肤干燥/嗅觉减退"},
    "水": {"脏": "肾", "腑": "膀胱", "体": "骨", "窍": "耳",
           "excess": "肾水泛滥/水肿/尿频/骨刺/耳鸣眩晕",
           "deficit": "肾精不足/腰膝酸软/脱发/记忆力减退/听力下降"},
}

CLIMATE_HEALTH_RISK = {
    "大寒": {
        "label": "寒湿体质（高风险）",
        "risks": [
            "寒湿困脾→消化吸收功能差，易腹胀腹泻",
            "寒凝血脉→末梢循环不良，手脚冰凉，冬季加重",
            "肾阳虚寒→腰膝酸冷，生殖功能偏弱",
            "寒湿下注→关节疼痛，风湿类疾病风险偏高",
        ],
        "advice": "宜温补：艾灸关元/足三里，冬季多食姜枣羊肉，避免生冷寒凉食物，注意腰腹保暖",
    },
    "偏寒": {
        "label": "偏寒体质（亚健康倾向）",
        "risks": [
            "阳气偏弱→精力恢复较慢，易疲劳",
            "寒性体质→对寒冷敏感，冬季注意保暖",
        ],
        "advice": "适度运动升阳，少食冰饮，入秋后提前温补",
    },
    "大燥": {
        "label": "燥热体质（高风险）",
        "risks": [
            "肺燥津伤→呼吸道脆弱，易干咳/咽炎/鼻炎",
            "心火上炎→易烦躁失眠，口腔溃疡反复发作",
            "肝火偏旺→情绪波动大，易怒，血压偏高倾向",
            "燥火伤阴→皮肤干燥/便秘/痔疮，炎症反应偏强",
        ],
        "advice": "宜清润：多食梨藕百合银耳，避免辛辣油炸烧烤，保持充足饮水，适当有氧运动清热",
    },
    "偏燥": {
        "label": "偏燥体质（亚健康倾向）",
        "risks": [
            "津液偏亏→皮肤偏干，易口渴，大便偏干",
            "炎症反应偏强→注意口腔/咽喉/皮肤炎症",
        ],
        "advice": "多喝水，多食滋阴润燥食物（梨、蜂蜜、银耳），减少辛辣",
    },
    "中和": {
        "label": "寒暖适中（基础体质良好）",
        "risks": [],
        "advice": "无特殊偏颇，保持均衡饮食和适度运动即可",
    },
}


def get_tiaohou_health_profile(tiaohou_result: dict | None) -> dict:
    """从调候分析结果生成健康体质画像（v0.10.0）"""
    if not tiaohou_result:
        return {"label": "未知", "risks": [], "advice": ""}

    climate = tiaohou_result.get("climate", "中和")
    is_fei_ju = tiaohou_result.get("is_fei_ju", False)
    return CLIMATE_HEALTH_RISK.get(climate, CLIMATE_HEALTH_RISK["中和"])


def get_wuxing_balance_health(all_branches: list, day_master,
                               all_stems: list = None) -> list[dict]:
    """五行偏枯→脏腑预警（v0.10.0: 引擎二）

    检测规则：
    1. 某五行在地支中占比≥3（过剩）→ 对应脏腑 excess 风险
    2. 某五行完全缺失（偏枯）→ 对应脏腑 deficit 风险
    3. 过剩+无泄（无生克出口）→ 肿瘤/结石风险升级
    """
    from collections import Counter
    wx_list = [b.wuxing.value for b in all_branches]
    wx_count = Counter(wx_list)
    risk_items = []

    for wx in ["木", "火", "土", "金", "水"]:
        cnt = wx_count.get(wx, 0)
        organ = WUXING_ORGAN_MAP[wx]

        if cnt >= 3:
            # 检查是否有宣泄口（其所生五行）
            sheng_map = {"木": "火", "火": "土", "土": "金", "金": "水", "水": "木"}
            outlet = sheng_map[wx]
            has_outlet = wx_count.get(outlet, 0) >= 1

            severity = "中" if has_outlet else "高"
            risk_items.append({
                "wuxing": wx,
                "organ": f"{organ['脏']}/{organ['腑']}",
                "type": "excess",
                "severity": severity,
                "count": cnt,
                "has_outlet": has_outlet,
                "risk": organ["excess"],
                "label": f"{organ['脏']}系负担{'偏重' if has_outlet else '过重（无泄）'}",
                "note": f"{wx}气郁积（{cnt}重），{'有宣泄口尚可控' if has_outlet else '无宣泄→防实质性病变（息肉/结石/肿瘤倾向）'}",
            })
        elif cnt == 0:
            risk_items.append({
                "wuxing": wx,
                "organ": f"{organ['脏']}/{organ['腑']}",
                "type": "deficit",
                "severity": "中",
                "count": 0,
                "has_outlet": False,
                "risk": organ["deficit"],
                "label": f"{organ['脏']}系先天偏弱",
                "note": f"{wx}气完全缺失→{organ['脏']}功能先天不足，宜后天调养",
            })

    return risk_items
