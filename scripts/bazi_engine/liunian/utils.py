"""Helper functions for liunian event detection."""
from .._constants import (
    DIZHI_BANHE,
    DIZHI_CANGGAN,
    DIZHI_LIUCHONG,
    DIZHI_LIUHE,
    DIZHI_SANHE,
    DIZHI_XIANGHAI,
    DIZHI_XIANGXING,
    DIZHI_ZIXING,
    SHIER_CHANGSHENG,
    TIANGAN_WUHE,
)
from ..enums import Dizhi, Shishen, Tiangan, Wuxing
from ..ten_gods import wuxing_ke, wuxing_sheng

# 天干五合配对: 天干 → 其合配天干
HEAVENLY_HE = {}
for (a, b) in [(Tiangan.甲, Tiangan.己), (Tiangan.乙, Tiangan.庚),
               (Tiangan.丙, Tiangan.辛), (Tiangan.丁, Tiangan.壬),
               (Tiangan.戊, Tiangan.癸)]:
    HEAVENLY_HE[a] = b
    HEAVENLY_HE[b] = a
del a, b



def compute_liunian_pillar(year: int) -> tuple[Tiangan, Dizhi]:
    """流年干支: (year - 4) % 60"""
    from ..enums import dizhi_by_index, tiangan_by_index
    idx = (year - 4) % 60
    return tiangan_by_index(idx), dizhi_by_index(idx)

def classify_sb_relation(stem: Tiangan, branch: Dizhi) -> tuple[str, float, float]:
    """分类流年干支关系，返回权重分配。

    规则:
    - 干支一气（五行相同）→ 天地同心 (0.50, 0.50)
    - 天干生地支 → 侧重地支 (0.45, 0.55)
    - 地支生天干 → 侧重天干 (0.55, 0.45)
    - 盖头（天干克地支）→ 天干主导 (0.60, 0.40)
    - 截脚（地支克天干）→ 地支主导 (0.40, 0.60)

    Returns:
        (relation_name, stem_weight, branch_weight)
    """
    from ..enums import DIZHI_WUXING, TIANGAN_WUXING

    s_wx = TIANGAN_WUXING.get(stem)
    b_wx = DIZHI_WUXING.get(branch)

    if s_wx is None or b_wx is None:
        return ("干支平衡", 0.50, 0.50)

    # 干支一气
    if s_wx == b_wx:
        return ("干支一气", 0.50, 0.50)

    # 生克判定
    if wuxing_sheng(s_wx) == b_wx:
        return ("天干生地支", 0.45, 0.55)
    elif wuxing_sheng(b_wx) == s_wx:
        return ("地支生天干", 0.55, 0.45)
    elif wuxing_ke(s_wx) == b_wx:
        return ("盖头", 0.60, 0.40)
    elif wuxing_ke(b_wx) == s_wx:
        return ("截脚", 0.40, 0.60)

    return ("干支平衡", 0.50, 0.50)

def is_favorable(
    ten_god: Shishen,
    favorable_set: set[str] | None,
    harmful_set: set[str] | None = None,
) -> bool | None:
    """判断十神喜忌；提供忌神集合时保留非喜非忌的中性状态。"""
    if favorable_set is None:
        if harmful_set is None:
            return None
        return False if ten_god.value in harmful_set else None
    if ten_god.value in favorable_set:
        return True
    if harmful_set is None:
        # 兼容只提供喜神集合的旧调用：未列入喜神即按忌神处理。
        return False
    if ten_god.value in harmful_set:
        return False
    return None

def is_harmful(ten_god: Shishen, harmful_set: set[str] | None) -> bool | None:
    """判断十神是否为忌神。harmful_set 为 None 时返回 None（不判断）。"""
    if harmful_set is None:
        return None
    return ten_god.value in harmful_set

def _fav_note(ten_god: Shishen, fav: bool | None, label: str) -> str:
    """生成喜用/忌神注释。fav=None 时返回空字符串。"""
    if fav is True:
        return f"{label}为喜，吉增"
    if fav is False:
        return f"{label}为忌，吉减或反凶"
    return ""

# 财库映射: 日主五行 → 财库地支
_CAIKU_MAP: dict[str, Dizhi] = {
    "木": Dizhi.戌,   # 土财，戌为火土之库(戌=火库=土库→财库)
    "火": Dizhi.辰,   # 金财，辰为水库→金之库?
    "土": Dizhi.辰,   # 水财，辰为水库
    "金": Dizhi.未,   # 木财，未为木库
    "水": Dizhi.戌,   # 火财，戌为火库
}
# 更正：财库按「我克者为财，财之墓库」严格定义
# 甲乙木克土 → 土财 → 辰为土库
# 丙丁火克金 → 金财 → 丑为金库
# 戊己土克水 → 水财 → 辰为水库
# 庚辛金克木 → 木财 → 未为木库
# 壬癸水克火 → 火财 → 戌为火库
_CAIKU_BY_DAY_WUXING: dict[str, Dizhi] = {
    "木": Dizhi.辰,  # 木克土，辰=土库
    "火": Dizhi.丑,  # 火克金，丑=金库
    "土": Dizhi.辰,  # 土克水，辰=水库
    "金": Dizhi.未,  # 金克木，未=木库
    "水": Dizhi.戌,  # 水克火，戌=火库
}


def get_caiku_branch(day_master: Tiangan) -> Dizhi:
    """返回日主的财库地支"""
    return _CAIKU_BY_DAY_WUXING[day_master.wuxing.value]

def _has_branch_interaction(target: Dizhi, ref_branch: Dizhi, interaction_type: str) -> bool:
    """检查两个地支的特定关系"""
    if interaction_type == "六合":
        return (target, ref_branch) in DIZHI_LIUHE
    if interaction_type == "六冲":
        return (target, ref_branch) in DIZHI_LIUCHONG
    if interaction_type == "相害":
        return (target, ref_branch) in DIZHI_XIANGHAI
    if interaction_type == "自刑":
        return target == ref_branch and target in DIZHI_ZIXING
    if interaction_type == "相刑":
        return (target, ref_branch) in DIZHI_XIANGXING
    if interaction_type == "三合":
        # 事件层的二支关系只表示标准半合；不能把同一三合组中
        # 的任意两支（如申辰、寅戌）都当成半合。
        return frozenset({target, ref_branch}) in DIZHI_BANHE
    return False

def _has_sanhe_with_dizhi(target: Dizhi, year_branch: Dizhi,
                          all_branches: list[Dizhi]) -> bool:
    """检查年支与目标地支是否形成标准半合或完整三合。"""
    pair = frozenset({target, year_branch})
    if pair in DIZHI_BANHE:
        return True
    available = set(all_branches) | {target, year_branch}
    return any(trio <= available for trio in DIZHI_SANHE)

def _has_tiangan_wuhe(a: Tiangan, b: Tiangan) -> bool:
    """检查两个天干是否组成五合"""
    return (a, b) in TIANGAN_WUHE

def _changsheng_status(day_master: Tiangan, branch: Dizhi) -> str:
    """返回日主在地支的十二长生阶段名"""
    return SHIER_CHANGSHENG.get(day_master, {}).get(branch, "")

def _is_in_same_sanhe(a: Dizhi, b: Dizhi) -> bool:
    """检查两个地支是否组成标准半合。"""
    return frozenset({a, b}) in DIZHI_BANHE

def _life_stage(age: int,
                dayun_ten_god: str | None = None,
                pattern: str = "",
                has_xuesheng_signal: bool = False) -> str:
    """智能判断人生阶段。

    四重判断：
    1. 年龄打底（硬指标）
    2. 升学信号确认（检测到升学→在学）
    3. 大运十神修正（印/食伤→深造，财/官→职场）
    4. 格局修正（印格/食伤格→学历偏高，财格/建禄→实干）

    返回: "中学" | "大学" | "深造" | "职场" | "晚年"
    - 大学: 18-21 本科阶段
    - 深造: 22-28 读研/读博/进修（与职场区分）
    """

    # ── 第一层：年龄打底 ──
    if age >= 56:
        base = "晚年"
    elif age >= 29 or age >= 26:
        base = "职场"
    elif age >= 22:
        base = "职场"  # 22-25 多数人已工作，深造是少数
    elif age >= 18:
        base = "大学"
    else:
        base = "中学"

    # ── 第二层：升学信号确认 ──
    if has_xuesheng_signal:
        if age <= 28 and base == "职场":
            return "深造"
        return base

    # ── 第三层：大运十神修正 ──
    if dayun_ten_god and dayun_ten_god in ("正印", "偏印", "食神", "伤官") and base == "职场" and age <= 25:
        # 印星/食伤大运 + 年龄≤25 → 倾向深造
        base = "深造"

    # ── 第四层：格局修正 ──
    if ("印" in pattern or "食神" in pattern or "伤官" in pattern) and base == "职场" and age <= 25 and not dayun_ten_god:
        base = "深造"  # 印/食伤格+年轻+无明确工作信号→深造

    return base

def _make_prediction(category: str, direction: str, strength: int,
                     triggers: list[str], notes: list[str],
                     age: int | None = None,
                     life_stage: str = "") -> str:
    """根据信号组合生成自然语言预测。
    当 life_stage 传入时优先使用；否则用 age 推断。
    """
    if life_stage:
        stage = life_stage
    elif age is not None:
        stage = _life_stage(age)
    else:
        stage = "职场"

    if category == "桃花":
        if stage in ("中学",):
            if direction == "正面":
                return "关系互动主题增加，注意平衡学习与社交"
            elif direction == "负面":
                return "同学关系有摩擦，注意情绪管理"
        if stage in ("大学", "深造"):
            if direction == "正面" and strength >= 2:
                return "校园社交与关系机会信号较集中，可结合现实互动观察"
            elif direction == "正面":
                return "关系互动信号偏积极，可留意现实社交变化"
            elif direction == "负面":
                return "校园恋情有波动，注意沟通方式"
        if direction == "正面" and strength >= 3:
            return "关系机会信号较集中，可结合现实互动关注新关系或关系推进"
        elif direction == "正面" and strength >= 2:
            return "关系互动信号偏积极，可关注认识新朋友或推进沟通的机会"
        elif direction == "正面":
            return "社交与关系主题略有增加，可结合现实互动核对"
        elif direction == "负面" and strength >= 3:
            return "关系互动压力信号较集中，宜关注沟通、边界与现实变化"
        elif direction == "负面":
            return "感情有摩擦或情绪内耗，宜坦诚沟通"
        else:
            return "关系主题被引动，具体表现需结合现实关系状态"

    elif category == "升学":
        if stage in ("职场", "晚年"):
            if strength >= 2:
                return "进修与考证主题信号较集中，适合结合计划评估深造或技能提升"
            else:
                return "适合短期培训、考证或自学充电"
        if strength >= 3:
            return "学习与考试主题信号较集中，实际结果取决于准备和报名条件"
        elif strength >= 2:
            return "学习与申请主题偏积极，适合结合实际进度安排备考或深造申请"
        else:
            return "学习状态尚可，适合短期进修或兴趣学习"

    elif category == "婚嫁":
        if direction == "负面":
            return "感情关系有波动，注意沟通" if strength >= 2 else "感情关系需留意"
        if strength >= 3:
            return "关系定型候选信号较强，可结合现实进展关注订婚、结婚或共同生活安排"
        elif strength >= 2:
            return "关系定型候选信号出现，可结合现实进展关注长期关系或共同生活安排"
        else:
            return "感情方面有新动向"

    elif category == "事业":
        if stage in ("中学", "大学", "深造"):
            # 学生阶段 → 学业表现 / 校园活动
            if direction == "正面" and strength >= 3:
                return "学业与校园活动信号较集中，可结合实际准备推进竞赛、项目或升学安排"
            elif direction == "正面":
                return "学业/校园活动有进展，适合参与社团或学术项目"
            elif direction == "负面" and strength >= 3:
                return "学业压力较大，注意考试发挥、与老师的沟通或升学竞争"
            elif direction == "负面":
                return "学业有阻力，可能分心或动力不足，建议与老师同学多交流"
            else:
                return "学业方向可能有调整（转专业/换导师等）"
        else:
            if direction == "正面" and strength >= 3:
                return "工作推进或调整信号较集中，可结合岗位、项目和资源评估下一步"
            elif direction == "正面":
                return "工作主题偏积极，可关注项目推进、岗位调整或合作机会"
            elif direction == "负面" and strength >= 3:
                return "事业变动信号较强，宜留意岗位、团队安排和与上级的沟通"
            elif direction == "负面":
                return "工作有阻力或瓶颈，可能被动调整，宜稳扎稳打"
            else:
                return "工作调整主题被引动，具体表现需结合岗位、团队和个人计划"

    elif category == "财运":
        if stage in ("中学", "大学", "深造"):
            if direction == "正面" and strength >= 3:
                return "财务主题较活跃，可记录奖学金、兼职或家庭支持等实际变化；不作金额预测"
            elif direction == "正面":
                return "可关注预算与资源安排，结合现实收支作判断"
            elif direction == "负面" and strength >= 3:
                return "建议提前核对预算、合同和消费计划，不据此推断具体支出"
            elif direction == "负面":
                return "可复核近期收支与消费计划，避免仅凭命理信号决策"
            else:
                return "财务主题有变化候选，需以实际收支记录为准"
        else:
            if direction == "正面" and strength >= 3:
                return "财务主题信号较强，可核对收入机会、合同与风险承受能力；不推断收益或金额"
            elif direction == "正面":
                return "可关注预算、收入来源和合作安排，以实际信息判断后续行动"
            elif direction == "负面" and strength >= 3:
                return "建议审查预算、借贷和合同风险，不据此推断损失或支出规模"
            elif direction == "负面":
                return "可复核现金流与消费计划，避免仅凭该信号作出财务决定"
            else:
                return "财务主题有变化候选，需结合现实收支和职业情况判断"

    elif category == "健康":
        return "生活节律与安全提醒：留意作息、运动和出行安排；如有不适，请咨询专业人士。"

    elif category == "搬迁":
        if stage in ("中学", "大学", "深造"):
            if strength >= 2:
                return "学习或居住环境变动信号较强，可留意换宿舍、换校区或异地求学安排"
            else:
                return "出行或学习环境调整主题出现，需结合现实安排核对"
        if strength >= 3:
            return "居住或工作环境变动信号较强，可留意搬家、换城市或远行安排"
        elif strength >= 2:
            return "居住或工作环境存在调整候选，需结合现实安排核对"
        else:
            return "出行或环境调整主题出现，需结合现实安排核对"

    elif category == "状态":
        if stage in ("中学", "大学", "深造"):
            if direction == "负面":
                return "学业或情绪压力较大，宜与同学/老师/家长多沟通"
            elif direction == "正面":
                return "状态信号偏积极，可结合实际精力安排学习或活动"
        if direction == "正面" and strength >= 3:
            return "状态信号偏积极，可结合实际精力推进重点事项"
        elif direction == "正面":
            return "状态良好，适合推进重要事项或尝试新突破"
        elif direction == "负面":
            return "压力与疲惫感可能增加，宜调整作息和节奏，必要时寻求专业支持"
        else:
            return "心态有波动，宜稳住节奏，避免冲动决策"

    elif category == "人际":
        if stage in ("中学", "大学", "深造"):
            if direction == "负面":
                return "同学互动存在摩擦候选，宜核对信息与沟通方式"
            elif strength >= 2:
                return "校园社交互动信号偏积极，实际关系仍需结合日常相处判断"
            else:
                return "同学互动主题较弱，暂无显著结论"
        if direction == "负面":
            return "人际摩擦信号出现，宜核对职场或社交中的信息、边界与竞争情况"
        elif strength >= 2:
            return "社交与合作信号偏积极，实际结果取决于互动和合作条件"
        else:
            return "人际主题较弱，暂无显著结论"

    elif category == "官非":
        if strength >= 3:
            return "规则与合规压力信号较强，重要合同、手续和争议应以专业法律意见为准"
        elif strength >= 2:
            return "留意合同、手续与规则边界，发生现实争议时及时咨询专业人士"
        else:
            return "留意潜在的规则风险或口舌是非"

    return ""

def _kongwang_branches(day_stem: Tiangan, day_branch: Dizhi) -> tuple[Dizhi, Dizhi]:
    """返回日柱旬空的两个地支"""
    from ..enums import dizhi_by_index
    xun_start = (day_branch.index - day_stem.index) % 12
    kw1 = dizhi_by_index((xun_start + 10) % 12)
    kw2 = dizhi_by_index((xun_start + 11) % 12)
    return kw1, kw2

def _is_kongwang(branch: Dizhi, kw: tuple[Dizhi, Dizhi]) -> bool:
    """检查地支是否落空亡"""
    return branch in kw

def _has_root(stem: Tiangan, branch: Dizhi) -> bool:
    """天干在地支是否有根(同五行藏干)。无根=虚浮无力。"""
    wx = stem.wuxing
    return any(hs.stem.wuxing == wx for hs in DIZHI_CANGGAN.get(branch, []))

def _is_ke_wx(a, b) -> bool:
    """a 五行克 b 五行？"""
    ke_map = {
        Wuxing.木: Wuxing.土, Wuxing.土: Wuxing.水,
        Wuxing.水: Wuxing.火, Wuxing.火: Wuxing.金, Wuxing.金: Wuxing.木,
    }
    return ke_map.get(a) == b

def _wealth_magnitude(total: int, triggers: list[str] | None = None,
                     dayun_theme: str = "", is_cong_ge: bool = False) -> str:
    """根据既有工程分数给出财务信号量级。

    候选关系、财库、运势主题和从格都不再额外放大量级，避免把结构标签
    误写成确定的资金结果。保留参数以兼容现有调用方。
    """

    base_level = 0
    if total >= 7:
        base_level = 3
    elif total >= 4:
        base_level = 2
    elif total >= 2:
        base_level = 1
    elif total <= -7:
        base_level = -3
    elif total <= -4:
        base_level = -2
    elif total <= -2:
        base_level = -1

    magnitude_map = {
        1: "弱", 2: "中", 3: "较强",
        -1: "弱", -2: "中", -3: "较强",
    }
    return magnitude_map.get(base_level, "弱")

