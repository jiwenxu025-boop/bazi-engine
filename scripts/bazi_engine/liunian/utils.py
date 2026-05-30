"""Helper functions for liunian event detection."""
from .._constants import (
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
    _SHENG = {Wuxing.木: Wuxing.火, Wuxing.火: Wuxing.土, Wuxing.土: Wuxing.金,
              Wuxing.金: Wuxing.水, Wuxing.水: Wuxing.木}
    _KE = {Wuxing.木: Wuxing.土, Wuxing.土: Wuxing.水, Wuxing.水: Wuxing.火,
           Wuxing.火: Wuxing.金, Wuxing.金: Wuxing.木}

    if _SHENG.get(s_wx) == b_wx:
        return ("天干生地支", 0.45, 0.55)
    if _SHENG.get(b_wx) == s_wx:
        return ("地支生天干", 0.55, 0.45)
    if _KE.get(s_wx) == b_wx:
        return ("盖头", 0.60, 0.40)
    if _KE.get(b_wx) == s_wx:
        return ("截脚", 0.40, 0.60)

    return ("干支平衡", 0.50, 0.50)

def is_favorable(ten_god: Shishen, favorable_set: set[str] | None) -> bool | None:
    """判断十神是否为喜用。favorable_set 为 None 时返回 None（不判断）。"""
    if favorable_set is None:
        return None
    return ten_god.value in favorable_set

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
        for trio in DIZHI_SANHE:
            trio_dz = list(trio)
            if target in trio_dz and ref_branch in trio_dz:
                return True
        return False
    return False

def _has_sanhe_with_dizhi(target: Dizhi, year_branch: Dizhi,
                          all_branches: list[Dizhi]) -> bool:
    """检查年支与目标地支是否在同一三合局中（半合及以上）"""
    for trio in DIZHI_SANHE:
        trio_dz = list(trio)
        if target in trio_dz and year_branch in trio_dz:
            return True
    return False

def _has_tiangan_wuhe(a: Tiangan, b: Tiangan) -> bool:
    """检查两个天干是否组成五合"""
    return (a, b) in TIANGAN_WUHE

def _changsheng_status(day_master: Tiangan, branch: Dizhi) -> str:
    """返回日主在地支的十二长生阶段名"""
    return SHIER_CHANGSHENG.get(day_master, {}).get(branch, "")

def _is_in_same_sanhe(a: Dizhi, b: Dizhi) -> bool:
    """检查两个地支是否在同一三合局中（含半合）"""
    for trio in DIZHI_SANHE:
        if a in trio and b in trio:
            return True
    return False

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
    elif age >= 29:
        base = "职场"
    elif age >= 26:
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
    if dayun_ten_god:
        # 印星/食伤大运 + 年龄≤25 → 倾向深造
        if dayun_ten_god in ("正印", "偏印", "食神", "伤官"):
            if base == "职场" and age <= 25:
                base = "深造"

    # ── 第四层：格局修正 ──
    if ("印" in pattern or "食神" in pattern or "伤官" in pattern):
        if base == "职场" and age <= 25 and not dayun_ten_god:
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
                return "异性缘上升，注意平衡学业与感情"
            elif direction == "负面":
                return "同学关系有摩擦，注意情绪管理"
        if stage in ("大学", "深造"):
            if direction == "正面" and strength >= 2:
                return "校园恋爱机会多，社团/课堂中可能邂逅"
            elif direction == "正面":
                return "异性缘微增，可留意周围"
            elif direction == "负面":
                return "校园恋情有波动，注意沟通方式"
        if direction == "正面" and strength >= 3:
            return "感情机遇强——可能脱单、恋爱或关系重大升级"
        elif direction == "正面" and strength >= 2:
            return "桃花运上升，有恋爱或约会机会"
        elif direction == "正面":
            return "异性缘微增，可通过社交认识新朋友"
        elif direction == "负面" and strength >= 3:
            return "感情有较大波动——注意分手、冷战或信任危机"
        elif direction == "负面":
            return "感情有摩擦或情绪内耗，宜坦诚沟通"
        else:
            return "感情节点期——可能进入新关系或结束旧关系"

    elif category == "升学":
        if stage in ("职场", "晚年"):
            if strength >= 2:
                return "进修/考证运佳，适合在职深造、MBA或技能提升"
            else:
                return "适合短期培训、考证或自学充电"
        if strength >= 3:
            return "考试运佳，升学/考证/考公希望较大"
        elif strength >= 2:
            return "学业运好，适合备考冲刺或深造申请"
        else:
            return "学习状态尚可，适合短期进修或兴趣学习"

    elif category == "婚嫁":
        if direction == "负面":
            return "感情关系有波动，注意沟通" if strength >= 2 else "感情关系需留意"
        if strength >= 3:
            return "感情重大节点，大概率结婚/订婚或同居"
        elif strength >= 2:
            return "感情有新进展，可能确立关系或同居"
        else:
            return "感情方面有新动向"

    elif category == "事业":
        if stage in ("中学", "大学", "深造"):
            # 学生阶段 → 学业表现 / 校园活动
            if direction == "正面" and strength >= 3:
                return "校园表现突出，有竞赛获奖、担任学生干部或保研机会"
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
                return "晋升/跳槽/创业机会较大，或岗位层级明显提升"
            elif direction == "正面":
                return "工作有新机会或进展，可能加薪、转岗或项目突破"
            elif direction == "负面" and strength >= 3:
                return "事业有较大变动，注意裁员风险、离职冲动或与上级冲突"
            elif direction == "负面":
                return "工作有阻力或瓶颈，可能被动调整，宜稳扎稳打"
            else:
                return "工作有变动——可能是岗位调整、换团队或创业尝试"

    elif category == "财运":
        if stage in ("中学", "大学", "深造"):
            if direction == "正面" and strength >= 3:
                return "奖学金/家庭支持宽裕，可能有兼职收入"
            elif direction == "正面":
                return "经济宽松，零花钱或生活费到位"
            elif direction == "负面" and strength >= 3:
                return "注意控制消费，可能有意外大额开销"
            elif direction == "负面":
                return "手头偏紧，建议节制非必要消费"
            else:
                return "财务状况有变动"
        else:
            if direction == "正面" and strength >= 3:
                return "财运看好——加薪/副业/投资收益有机会，或有大额进账"
            elif direction == "正面":
                return "财运向好，正财偏财皆有收获，适合理财规划"
            elif direction == "负面" and strength >= 3:
                return "财务有较大波动——注意投资亏损、被借钱或大额意外支出"
            elif direction == "负面":
                return "财运偏紧，开销增多或进账减少，宜控制支出"
            else:
                return "财务有变动——可能是换工作带来的收入变化或阶段性调整"

    elif category == "健康":
        if stage in ("中学", "大学", "深造"):
            if strength >= 3:
                return "健康需重视——注意运动伤害、意外磕碰或突发疾病，及时就医"
            elif strength >= 2:
                return "注意作息规律和运动安全，避免熬夜和过量运动"
            else:
                return "精力尚可，但熬夜或饮食不规律需注意"
        elif stage == "晚年":
            if strength >= 3:
                return "健康风险较高——务必定期体检，防范心脑血管、慢性病突发或跌倒"
            elif strength >= 2:
                return "建议体检复查，注意慢性病管理和换季保暖"
            else:
                return "注意养生保健，适度锻炼，保持良好作息"
        if strength >= 3:
            return "健康风险较高——建议体检排查，注意意外伤害或旧疾复发"
        elif strength >= 2:
            return "健康需留意——劳逸结合，避免过劳或情绪压力影响身体"
        else:
            return "注意小病小痛，保持良好生活习惯"

    elif category == "搬迁":
        if stage in ("中学", "大学", "深造"):
            if strength >= 2:
                return "可能换宿舍/换校区、留学或异地求学"
            else:
                return "可能有出行/旅行或短期游学"
        if strength >= 3:
            return "很可能搬家、换城市或出国等远行"
        elif strength >= 2:
            return "居住或工作地点可能有变动"
        else:
            return "可能有短途出行或出差"

    elif category == "状态":
        if stage in ("中学", "大学", "深造"):
            if direction == "负面":
                return "学业或情绪压力较大，宜与同学/老师/家长多沟通"
            elif direction == "正面":
                return "精力充沛，自信足，适合备考冲刺或参加竞赛活动"
        if direction == "正面" and strength >= 3:
            return "精力充沛，自信心和执行力处于高峰"
        elif direction == "正面":
            return "状态良好，适合推进重要事项或尝试新突破"
        elif direction == "负面":
            return "身心压力较大——注意焦虑、失眠或倦怠，适当放松调节"
        else:
            return "心态有波动，宜稳住节奏，避免冲动决策"

    elif category == "人际":
        if stage in ("中学", "大学", "深造"):
            if direction == "负面":
                return "同学关系紧张，注意友谊维护"
            elif strength >= 2:
                return "校园社交活跃，师生/同学关系不错"
            else:
                return "同学关系平稳"
        if direction == "负面":
            return "人际有摩擦——注意职场/朋友圈的口舌是非或竞争"
        elif strength >= 2:
            return "社交活跃，人缘或合作关系向好"
        else:
            return "人际关系平稳，维持现有圈子"

    elif category == "官非":
        if strength >= 3:
            return "高风险年份——注意法律纠纷、官非诉讼或与权威机构的冲突，切忌触犯规则底线"
        elif strength >= 2:
            return "注意法律风险或与权威的冲突，遵守规则，避免冲动行事"
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
    for hs in DIZHI_CANGGAN.get(branch, []):
        if hs.stem.wuxing == wx:
            return True
    return False

def _is_ke_wx(a, b) -> bool:
    """a 五行克 b 五行？"""
    ke_map = {
        Wuxing.木: Wuxing.土, Wuxing.土: Wuxing.水,
        Wuxing.水: Wuxing.火, Wuxing.火: Wuxing.金, Wuxing.金: Wuxing.木,
    }
    return ke_map.get(a) == b

def _wealth_magnitude(total: int, triggers: list[str] | None = None,
                     dayun_theme: str = "", is_cong_ge: bool = False) -> str:
    """v0.13.0: 根据 ScoreAccumulator 总分 + 触发类型 + 格局判定财运量级。

    升级规则：
    - 财库冲开 → +2 级（墓库核爆，资金放大器）
    - 财来合我 → +1 级（最直接的得财信号）
    - 大运主题=财运 → +1 级（十年财运共振）
    - 从格 → +1 级（格局指向财富上限更高）
    """
    trigger_str = str(triggers or [])
    has_caiku = "财库" in trigger_str or "冲开" in trigger_str
    has_cailai = "财来合我" in trigger_str
    is_wealth_dayun = "财运" in dayun_theme

    base_level = 0
    if total >= 7:
        base_level = 3  # 大额
    elif total >= 4:
        base_level = 2  # 中额
    elif total >= 2:
        base_level = 1  # 小额
    elif total <= -7:
        base_level = -3  # 大破财
    elif total <= -4:
        base_level = -2  # 破财
    elif total <= -2:
        base_level = -1  # 小额破财

    # 正财：升级
    if base_level > 0:
        if has_caiku:
            base_level += 2  # 财库冲开跳 2 级
        if has_cailai:
            base_level += 1
        if is_wealth_dayun:
            base_level += 1
        if is_cong_ge:
            base_level += 1

    # 负财（破财）：降级不加重
    magnitude_map = {
        1: "小额", 2: "中额", 3: "大额", 4: "大额", 5: "大额",
        -1: "小额破财", -2: "破财", -3: "大破财",
    }
    return magnitude_map.get(base_level, "小额" if total > 0 else "小额破财")

