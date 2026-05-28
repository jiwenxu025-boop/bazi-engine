"""流年逐年扫描 — 7 类事件信号检测，整合校准规则"""

from dataclasses import dataclass, field
from datetime import date
from .enums import Tiangan, Dizhi, Shishen
from ._constants import (
    HONGLUAN, TIANXI, TAOHUA, YIMA, WENCHANG, hour_to_dizhi, chong_pair,
    TIANGAN_WUHE, DIZHI_LIUHE, DIZHI_LIUCHONG, DIZHI_XIANGHAI, DIZHI_XIANGXING,
    DIZHI_ZIXING, DIZHI_SANHE, DIZHI_CANGGAN, SHIER_CHANGSHENG, _TIANYI_FLAT,
)
from .enums import TIANGAN_YANGREN, TIANGAN_LU
from .ten_gods import get_ten_god

# 天干五合配对: 天干 → 其合配天干
HEAVENLY_HE: dict[Tiangan, Tiangan] = {}
for (a, b) in [(Tiangan.甲, Tiangan.己), (Tiangan.乙, Tiangan.庚),
               (Tiangan.丙, Tiangan.辛), (Tiangan.丁, Tiangan.壬),
               (Tiangan.戊, Tiangan.癸)]:
    HEAVENLY_HE[a] = b
    HEAVENLY_HE[b] = a
del a, b



@dataclass
class Factor:
    """打分因子：每个触发条件贡献一个分数"""
    score: int            # 正=吉, 负=凶, 绝对值=强度
    trigger: str          # 触发描述
    note: str = ""        # 补充说明


class ScoreAccumulator:
    """打分累加器：收集因子 → 综合判断信号"""
    def __init__(self, favorable_set: set[str] | None = None):
        self.factors: list[Factor] = []
        self._min_strength: int = 0
        self._favorable: set[str] | None = favorable_set

    def add(self, score: int, trigger: str, note: str = "", fixed: bool = False):
        """添加因子。fixed=True 的因子不被喜忌调分（伤官/冲刑等方向固定型）。"""
        shishen = getattr(self, '_current_shishen', '')
        fav = getattr(self, '_current_fav', None)
        modulate_score = getattr(self, '_modulate_score', True)
        if shishen and fav is False:
            trigger += " [忌]"
            if modulate_score and not fixed:
                score = score - 1 if score > 0 else score - 1
        elif shishen and fav is True:
            trigger += " [喜]"
            if modulate_score and not fixed and score > 0:
                score = score + 1
        self.factors.append(Factor(score=score, trigger=trigger, note=note))

    def set_modulate(self, enabled: bool):
        """是否启用分数调制（婚嫁类只需标记，不需调分）"""
        self._modulate_score = enabled

    def set_shishen(self, shishen_val: str, is_fav: bool | None = None):
        """设定当前流年十神和喜忌状态"""
        self._current_shishen = shishen_val
        self._current_fav = is_fav

    def guarantee(self, min_strength: int):
        """确保至少有min_strength级别的信号(用于伤官/枭神等必然触发型)"""
        self._min_strength = max(self._min_strength, min_strength)

    @property
    def total(self) -> int:
        return sum(f.score for f in self.factors)

    @property
    def strength(self) -> int:
        """从总分映射到1-3星，不低于最小保证"""
        base = max(abs(self.total), self._min_strength)
        if base >= 4: return 3
        if base >= 2: return 2
        return 1

    @property
    def direction(self) -> str:
        t = self.total
        if t >= 1: return "正面"
        if t <= -1: return "负面"
        return "中性"

    def is_significant(self, threshold: int = 0) -> bool:
        """是否有足够信号输出。threshold: 最小总分绝对值，默认0=任何非零"""
        return abs(self.total) > threshold or self._min_strength > 0

    def triggers(self) -> list[str]:
        return [f.trigger for f in self.factors]

    def notes(self) -> list[str]:
        return [f.note for f in self.factors if f.note]


@dataclass
class EventSignal:
    category: str         # "桃花" | "升学" | "婚嫁" | "事业" | "财运" | "健康" | "搬迁"
    direction: str        # "正面" | "负面" | "中性"
    strength: int         # 1-3 (★ ~ ★★★)
    prediction: str = ""  # 自然语言预测
    triggers: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    calibration_refs: list[str] = field(default_factory=list)
    personality_note: str = ""  # 性格联动备注

    def to_dict(self) -> dict:
        return {
            "category": self.category,
            "direction": self.direction,
            "strength": self.strength,
            "prediction": self.prediction,
            "triggers": self.triggers,
            "notes": self.notes,
            "calibration_refs": self.calibration_refs,
            "personality_note": self.personality_note,
        }


@dataclass
class AnnualScan:
    year: int
    liunian_stem: Tiangan
    liunian_branch: Dizhi
    dayun_stem: Tiangan | None = None
    dayun_branch: Dizhi | None = None
    events: list[EventSignal] = field(default_factory=list)
    age: int | None = None
    sb_relation: str = ""            # 干支关系
    stem_weight: float = 0.5         # 天干权重
    branch_weight: float = 0.5       # 地支权重
    dayun_weight_note: str = ""      # 大运重地支/流年重天干说明

    def to_dict(self) -> dict:
        return {
            "year": self.year,
            "age": self.age,
            "liunian": f"{self.liunian_stem.value}{self.liunian_branch.value}",
            "dayun": f"{self.dayun_stem.value}{self.dayun_branch.value}" if self.dayun_stem else None,
            "sb_relation": self.sb_relation,
            "stem_weight": self.stem_weight,
            "branch_weight": self.branch_weight,
            "dayun_weight_note": self.dayun_weight_note,
            "events": [e.to_dict() for e in self.events],
        }


# ═══════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════

def compute_liunian_pillar(year: int) -> tuple[Tiangan, Dizhi]:
    """流年干支: (year - 4) % 60"""
    from .enums import tiangan_by_index, dizhi_by_index
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
    from .enums import TIANGAN_WUXING, DIZHI_WUXING, Wuxing

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
    from .enums import dizhi_by_index
    xun_start = (day_branch.index - day_stem.index) % 12
    kw1 = dizhi_by_index((xun_start + 10) % 12)
    kw2 = dizhi_by_index((xun_start + 11) % 12)
    return kw1, kw2


def _is_kongwang(branch: Dizhi, kw: tuple[Dizhi, Dizhi]) -> bool:
    """检查地支是否落空亡"""
    return branch in kw


# ═══════════════════════════════════════════════════════════════
# 1. 桃花/感情
# ═══════════════════════════════════════════════════════════════

def detect_taohua_signals(ln_stem: Tiangan, ln_branch: Dizhi,
                          year_branch: Dizhi, day_branch: Dizhi,
                          day_master: Tiangan, gender: str,
                          dayun_stem: Tiangan | None, dayun_branch: Dizhi | None,
                          prev_year_has_relationship: bool = False,
                          relationship_state: str = "single",
                          favorable: set[str] | None = None,
                          all_branches: tuple[Dizhi, ...] = ()) -> list[EventSignal]:
    """检测桃花/感情信号

    Incorporates calibration rules from bazi-ganzhi-interactions.md:
    - 天喜合动 = 感情机遇打开 (2/2 verified)
    - 红鸾+伏吟 = 方向取决于有无自刑和前一年感情状态
    - 卯辰穿 = 负面人际/情绪困扰 (3/3)
    - v0.11.1: relationship_state 跨年状态机——single/dating/married
      已有感情时桃花信号语境化为"关系深化/危机"而非"脱单"
    """
    signals: list[EventSignal] = []

    # 红鸾/天喜
    hongluan = HONGLUAN.get(year_branch)
    tianxi = TIANXI.get(year_branch)
    taohua = TAOHUA.get(year_branch)

    spouse_star = Shishen.正财 if gender == "男" else Shishen.正官
    spouse_star_name = "正财" if gender == "男" else "正官"
    ln_shishen = get_ten_god(day_master, ln_stem)

    strength = 0
    triggers = []
    notes = []

    # ── ★★★ 级别 ──
    # 流年地支合入夫妻宫（桃花合入日支）
    if _has_branch_interaction(day_branch, ln_branch, "六合"):
        strength = max(strength, 3)
        triggers.append("桃花合入夫妻宫")

    # 红鸾/天喜叠临桃花
    if (ln_branch == hongluan or ln_branch == tianxi) and ln_branch == taohua:
        strength = max(strength, 3)
        triggers.append("红鸾/天喜叠桃花")

    # 配偶星透干+合入日柱
    if ln_shishen == spouse_star and _has_branch_interaction(day_branch, ln_branch, "六合"):
        strength = max(strength, 3)
        triggers.append(f"{spouse_star_name}透干合入夫妻宫")

    # ── ★★ 级别 ──
    # 天喜合动 (calibration: 3/3 verified: 案例A2023卯戌合, 2026午戌半合, 案例B2022寅亥合)
    # 三种情况: 流年直接=天喜, 六合天喜, 半合/三合天喜
    if ln_branch == tianxi:
        strength = max(strength, 2)
        triggers.append("流年天喜入命")
        notes.append("天喜合动: 感情机遇打开 (校准 3/3)")
    elif _has_branch_interaction(ln_branch, tianxi, "六合"):
        strength = max(strength, 2)
        triggers.append(f"{ln_branch.value}{tianxi.value}合→天喜被合动")
        notes.append("天喜合动: 感情机遇打开 (校准 3/3)")
    elif tianxi and _is_in_same_sanhe(ln_branch, tianxi):
        strength = max(strength, 2)
        triggers.append(f"{ln_branch.value}{tianxi.value}半/三合→天喜被合动")
        notes.append("天喜合动: 感情机遇打开 (校准 3/3)")

    # 流年地支合日支
    if _has_branch_interaction(day_branch, ln_branch, "六合"):
        strength = max(strength, 2)
        triggers.append("流年合夫妻宫")

    # 桃花年
    if ln_branch == taohua:
        strength = max(strength, 2)
        triggers.append("流年桃花入命")

    # 红鸾+伏吟 (calibration: direction depends on自刑 and prev year)
    # 扩展至全部四柱伏吟，不限于日支
    if ln_branch == hongluan:
        fuyin_on_ri = ln_branch == day_branch
        fuyin_on_any = any(ln_branch == br for br in all_branches)
        has_zixing = fuyin_on_any and _has_branch_interaction(ln_branch, ln_branch, "自刑")

        if fuyin_on_ri and has_zixing:
            strength = max(strength, 2)
            triggers.append("红鸾入命+夫妻宫伏吟+自刑")
            notes.append("红鸾伏吟+自刑→倾向感情结束 (校准 1/2: 案例A2024)")
        elif fuyin_on_any and has_zixing:
            strength = max(strength, 2)
            triggers.append("红鸾入命+命局伏吟+自刑")
            notes.append("红鸾伏吟+自刑→情绪内耗/矛盾 (校准: 案例C2024)")
        elif fuyin_on_ri and prev_year_has_relationship:
            strength = max(strength, 2)
            triggers.append("红鸾入命+夫妻宫伏吟")
            notes.append("红鸾伏吟+前一年有感情→倾向节点性变化")
        elif fuyin_on_ri:
            strength = max(strength, 2)
            triggers.append("红鸾入命+夫妻宫伏吟")
            notes.append("红鸾伏吟+前一年空窗→倾向新开始 (校准 1/2: 案例B2022)")

    # 天喜合动+偏财/正财 (男) or 官星 (女)
    if ln_branch == tianxi:
        if gender == "男" and ln_shishen in (Shishen.偏财, Shishen.正财):
            strength = max(strength, 2)
            triggers.append("天喜+财星同现")
        elif gender == "女" and ln_shishen in (Shishen.偏官, Shishen.正官):
            strength = max(strength, 2)
            triggers.append("天喜+官星同现")

    # 流年支冲夫妻宫
    if _has_branch_interaction(day_branch, ln_branch, "六冲"):
        strength = max(strength, 2)
        triggers.append("流年冲夫妻宫")
        notes.append("夫妻宫逢冲→感情波动/分手可能性")

    # 卯辰穿 (calibration: 3/3 负面) — 扩展至全部四柱
    from ._constants import DIZHI_XIANGHAI, DIZHI_LIUHE
    tianxi_activated = (
        ln_branch == tianxi
        or (tianxi and (ln_branch, tianxi) in DIZHI_LIUHE)
    )
    # 检查流年是否与四柱中任一柱形成卯辰穿
    maochen_chuan = False
    maochen_on_ri = False
    for br in all_branches:
        if (Dizhi.卯, Dizhi.辰) in [(ln_branch, br), (br, ln_branch)]:
            maochen_chuan = True
            if br == day_branch:
                maochen_on_ri = True
    if maochen_chuan:
        if maochen_on_ri and tianxi_activated:
            strength = max(strength, 2)
            triggers.append("卯辰穿夫妻宫+天喜伴生")
            notes.append("卯辰穿+天喜伴生→可进入但根基不稳 (校准 1/1: 案例A2023)")
        elif maochen_on_ri:
            strength = max(strength, 2)
            triggers.append("卯辰穿夫妻宫")
            notes.append("卯辰穿→感情困扰/走不出来 (校准 3/3)")
        else:
            strength = max(strength, 2)
            triggers.append("卯辰穿命局")
            notes.append("卯辰穿→人际/情绪困扰 (校准: 案例B2023/案例C2023时柱)")

    # ── ★ 级别 ──
    # 空亡：降星+加备注（升级：统一降强度）
    kw = _kongwang_branches(day_master, day_branch)
    if _is_kongwang(ln_branch, kw):
        if triggers:
            notes.append("流年落空亡→机会真实但结果虚浮不实（《三命通会》：吉神空亡则吉减半，非无吉也）")

    if ln_branch == hongluan:
        strength = max(strength, 1)
        if "红鸾" not in str(triggers):
            triggers.append("流年红鸾入命")

    if ln_shishen == spouse_star:
        strength = max(strength, 1)
        if spouse_star_name not in str(triggers):
            triggers.append(f"流年{spouse_star_name}透干")

    if ln_branch == taohua and strength < 2:
        strength = max(strength, 1)
        triggers.append("流年桃花")

    # 劫财年+男命 → 感情竞争/分手风险 (即使无神煞)
    if ln_shishen == Shishen.劫财 and gender == "男":
        strength = max(strength, 2)
        triggers.append("劫财夺财→感情竞争风险")
        notes.append("劫财年→比劫夺财，感情易被第三者介入 (段建业: 比劫争妻)")
    if ln_shishen == Shishen.比肩 and gender == "男" and strength < 2:
        strength = max(strength, 1)
        triggers.append("比肩透干→同辈竞争可能影响感情")
        notes.append("比肩年→注意感情竞争 (段建业)")

    # 伤官年+女命 → 克夫/婚姻危机
    if ln_shishen == Shishen.伤官 and gender == "女":
        strength = max(strength, 2)
        triggers.append("伤官克官→婚姻危机")
        notes.append("伤官年→伤官见官，女命婚姻高危年 (段建业: 伤官运找不到老公)")

    # 伤官年+男命+合/冲夫妻宫 → 克妻/婚姻危机（v0.9.1: M14王宝强案）
    if ln_shishen == Shishen.伤官 and gender == "男":
        gong_he_taohua = _has_branch_interaction(day_branch, ln_branch, "六合")
        gong_chong_taohua = _has_branch_interaction(day_branch, ln_branch, "六冲")
        if gong_he_taohua or gong_chong_taohua:
            strength = max(strength, 3)
            triggers.append("伤官合/冲夫妻宫→婚灾信号")
            notes.append("男命伤官克正官+妻宫引动→克妻/婚姻危机 (《渊海子平》: 伤官见官为祸百端)")
        else:
            strength = max(strength, 2)
            triggers.append("伤官透干→感情波动")
            notes.append("男命伤官年→注意与伴侣口舌争执，克正官不利婚姻稳定")

    # 偏财/正财向正财过渡模式检查
    if gender == "男":
        if ln_shishen == Shishen.偏财:
            notes.append("偏财年→吸引/机会，看次年正财是否接得住")
        elif ln_shishen == Shishen.正财:
            notes.append("正财年→妻星出现，关系转正机会")

    if triggers:
        direction = "正面"
        # 校准数据驱动的方向修正（v0.7.0）
        _triggers_str = str(triggers)
        _notes_str = str(notes)

        # 比劫夺财/争官 → 负面（第三者竞争信号）
        if ln_shishen == Shishen.劫财:
            if gender == "男":
                direction = "负面"
                notes.append("劫财夺财→感情竞争/第三者风险 (段建业: 比劫争夫/争妻)")
            elif gender == "女" and any("官" in t for t in triggers):
                direction = "负面"
                notes.append("劫财争合官星→感情竞争/三角关系 (段建业: 比劫争夫)")

        # 伤官见官(女命) → 负面（克夫信号）
        if gender == "女" and ln_shishen == Shishen.伤官:
            direction = "负面"
            notes.append("伤官见官→克夫/婚姻危机 (段建业: 伤官运找不到老公)")

        # 伤官见官(男命+妻宫引动) → 负面（克妻信号）v0.9.1
        if gender == "男" and ln_shishen == Shishen.伤官:
            if any("夫妻宫" in t or "妻宫" in t or "婚灾" in t for t in triggers):
                direction = "负面"
                notes.append("伤官克正官+妻宫引动→克妻/婚姻高危 (《渊海子平》: 伤官见官为祸百端)")

        # 夫妻宫逢冲+七杀 → 负面
        if "冲夫妻宫" in _triggers_str and ln_shishen == Shishen.偏官:
            direction = "负面"
            notes.append("冲夫妻宫+七杀→感情危机加剧 (段建业: 夫宫冲穿必离婚)")

        # 冲夫妻宫 → 负面
        if "冲夫妻宫" in _triggers_str or "分手" in _notes_str:
            direction = "负面"
        # 卯辰穿（校准 4/4 负面, 含命局卯辰穿）
        elif "卯辰穿" in _triggers_str and "天喜伴生" not in _triggers_str:
            direction = "负面"
        # 自刑+伏吟 → 负面（无论前一年状态，自刑即内耗）
        elif "自刑" in _triggers_str and "伏吟" in _triggers_str:
            direction = "负面"
        # 卯辰穿+天喜伴生 → 中性（校准 1/1: 可进入但根基不稳）
        elif "卯辰穿" in _triggers_str and "天喜伴生" in _triggers_str:
            direction = "中性"
        elif "困扰" in _notes_str or "不稳" in _notes_str:
            direction = "中性"

        # ── v0.11.1: 跨年关系状态语境化 ──
        # 已有感情时，桃花信号≠脱单，而是关系内部事件
        if relationship_state == "dating" and direction == "正面":
            # 正面桃花在恋爱中→关系升温/深化/里程碑，不是新恋情
            notes.insert(0, "已有感情→此年桃花为关系内升温/深化，非新恋情")
            # 降半级强度（不是新开始的冲击力）
            strength = max(1, strength - 1)
        elif relationship_state == "dating" and direction == "负面":
            # 负面桃花在恋爱中→感情危机，比单身时更严重
            notes.insert(0, "已有感情→此年桃花负面信号实为感情危机/分手风险")
            strength = min(3, strength + 1)  # 危机信号加码
        elif relationship_state == "married":
            notes.insert(0, "已婚状态→桃花信号解读为婚姻内事件（升温/危机/外部诱惑），非婚变")

        # v0.10.1: 仅≥★2桃花输出——★1弱信号(红鸾/桃花/配偶星透干/流年合夫妻宫)不独立发信号
        if strength >= 2:
            signals.append(EventSignal(
                category="桃花",
                direction=direction,
                strength=min(strength, 3),
                prediction=_make_prediction("桃花", direction, min(strength,3), triggers, notes),
                triggers=triggers,
                notes=notes,
                calibration_refs=[t for t in triggers if "校准" in t or "calibration" in str(t)],
            ))

    return signals


# ═══════════════════════════════════════════════════════════════
# 2. 升学/考试
# ═══════════════════════════════════════════════════════════════

def detect_xuesheng_signals(ln_stem: Tiangan, ln_branch: Dizhi,
                            day_branch: Dizhi, day_master: Tiangan,
                            year_branch: Dizhi,
                            month_branch: Dizhi | None = None,
                            hour_branch: Dizhi | None = None,
                            favorable: set[str] | None = None) -> list[EventSignal]:
    """检测升学/考试信号 — v0.3.0 增强版"""
    signals: list[EventSignal] = []
    ln_shishen = get_ten_god(day_master, ln_stem)
    wenchang = WENCHANG.get(day_master)
    yima = YIMA.get(year_branch)

    strength = 0
    triggers = []
    notes = []

    is_yin = ln_shishen in (Shishen.正印, Shishen.偏印)
    is_guan = ln_shishen in (Shishen.正官, Shishen.偏官)
    is_shishang = ln_shishen in (Shishen.食神, Shishen.伤官)
    fav = is_favorable(ln_shishen, favorable)

    # ═══ ★★★ 级别 ═══

    # 官印相生+文昌（完整版：官星+印星+文昌三要素）
    if is_yin and ln_branch == wenchang:
        strength = 3
        triggers.append(f"流年印星透干+文昌{wenchang.value}")
        if fav is True:
            notes.append("印星为喜→考试运强")
        elif fav is False:
            notes.append("印星为忌→压力大但成绩未必差")

    # 官星得位+印星有力（textbook ★★★）
    if is_guan and is_yin:
        # 同柱官印相生（天干官+地支含印）
        for hs in DIZHI_CANGGAN.get(ln_branch, []):
            if get_ten_god(day_master, hs.stem) in (Shishen.正印, Shishen.偏印):
                strength = max(strength, 3)
                triggers.append("流年官印相生+文昌有力")
                notes.append("官印相生→功名最利 (textbook)")
                break

    # ═══ ★★ 级别 ═══

    # 印星透干且有根
    if is_yin:
        strength = max(strength, 2)
        triggers.append("流年印星透干")

    # 文昌贵人
    if ln_branch == wenchang:
        strength = max(strength, 2)
        triggers.append("流年文昌贵人入命")

    # 巳亥冲+驿马→高考远行 (calibration: 2/2)
    if ln_branch == yima and _has_branch_interaction(year_branch, ln_branch, "六冲"):
        strength = max(strength, 2)
        triggers.append(f"{year_branch.value}{ln_branch.value}冲+驿马→为学业远行")
        notes.append("巳亥冲+驿马+升学年龄→高考异地 (校准 2/2: 案例A2025, 案例C2025)")

    # 文昌+驿马同现
    if ln_branch == yima and ln_branch == wenchang:
        strength = max(strength, 2)
        triggers.append("文昌+驿马同现")

    # 食神吐秀（食伤年+文昌/印星伴生）
    if is_shishang and ln_branch == wenchang:
        strength = max(strength, 2)
        triggers.append("流年食伤+文昌→食神吐秀")
        notes.append("以才华考试/竞赛见长 (textbook)")

    # 冲时柱（时柱为考试/晚年学业宫）
    if hour_branch and _has_branch_interaction(hour_branch, ln_branch, "六冲"):
        strength = max(strength, 2)
        triggers.append("流年冲时柱")
        notes.append("冲时柱→考试/证书相关变动")

    # 月柱逢合（学业宫被合动）
    if month_branch and _has_branch_interaction(month_branch, ln_branch, "六合"):
        strength = max(strength, 2)
        triggers.append("流年合月柱(学业宫)")
        notes.append("合动月柱→学业环境变化")

    # ═══ ★ 级别 ═══

    if is_yin and strength < 2:
        strength = 1
        triggers.append("流年印星透干")

    if ln_branch == wenchang and strength < 2:
        strength = 1
        triggers.append("文昌贵人")

    if triggers:
        direction = "中性" if fav is False else "正面"
        signals.append(EventSignal(
            category="升学",
            direction=direction,
            strength=min(strength, 3),
            prediction=_make_prediction("升学", direction, min(strength,3), triggers, notes),
            triggers=triggers,
            notes=notes,
        ))
    return signals


# ═══════════════════════════════════════════════════════════════
# 3. 婚嫁/婚姻
# ═══════════════════════════════════════════════════════════════

def detect_hunjia_signals(ln_stem: Tiangan, ln_branch: Dizhi,
                          day_branch: Dizhi, day_master: Tiangan,
                          year_branch: Dizhi, gender: str,
                          favorable: set[str] | None = None,
                          dayun_branch: Dizhi | None = None,
                          age: int = 0) -> list[EventSignal]:
    """检测婚嫁/婚姻信号 — v0.6.0: 打分制 + 大运联动"""
    signals: list[EventSignal] = []
    spouse_star = Shishen.正财 if gender == "男" else Shishen.正官
    spouse_name = "正财" if gender == "男" else "正官"
    second_star = Shishen.偏财 if gender == "男" else Shishen.偏官
    second_name = "偏财" if gender == "男" else "七杀"
    ln_shishen = get_ten_god(day_master, ln_stem)
    s = ScoreAccumulator(favorable)
    s.set_shishen(ln_shishen.value, is_favorable(ln_shishen, favorable))
    s.set_modulate(False)  # 婚嫁只标记不调分

    hongluan = HONGLUAN.get(year_branch)
    tianxi_dz = TIANXI.get(year_branch)
    taohua = TAOHUA.get(year_branch)

    gong_he = _has_branch_interaction(day_branch, ln_branch, "六合")
    gong_sanhe = _has_branch_interaction(day_branch, ln_branch, "三合")
    gong_chong = _has_branch_interaction(day_branch, ln_branch, "六冲")

    # ── 大运联动: 夫妻宫冲处逢合 / 合处逢冲 ──
    if dayun_branch:
        dy_chong_gong = _has_branch_interaction(dayun_branch, day_branch, "六冲")
        dy_he_gong = _has_branch_interaction(dayun_branch, day_branch, "六合")
        # 大运冲夫妻宫 + 流年合夫妻宫 → 婚期 (段建业: 冲处逢合)
        if dy_chong_gong and (gong_he or gong_sanhe):
            s.add(4, "大运冲夫妻宫+流年合入→冲处逢合婚期", "段建业: 原局冲/大运冲, 岁合为婚期", fixed=True)
        # 大运合夫妻宫 + 流年冲夫妻宫 → 婚变风险
        if dy_he_gong and gong_chong:
            s.add(-3, "大运合夫妻宫+流年冲→合处逢冲婚变", "段建业: 合处逢冲为离婚应期", fixed=True)

    # 检查流年地支藏干是否含配偶星
    ln_canggan_shishen = [get_ten_god(day_master, hs.stem) for hs in DIZHI_CANGGAN.get(ln_branch, [])]
    has_spouse_in_branch = (spouse_star in ln_canggan_shishen or second_star in ln_canggan_shishen)
    spouse_in_branch_label = spouse_name if spouse_star in ln_canggan_shishen else (second_name if second_star in ln_canggan_shishen else "")

    tianxi_activated = False
    if tianxi_dz:
        tianxi_activated = (_has_branch_interaction(tianxi_dz, ln_branch, "六合")
                            or _has_branch_interaction(tianxi_dz, ln_branch, "三合"))

    # ════════════════════════════════════════════════
    # 正面因子（结婚应期）
    # ════════════════════════════════════════════════

    # 配偶星合日主
    he_pair = HEAVENLY_HE.get(day_master)
    if he_pair and ln_stem == he_pair and ln_shishen in (spouse_star, second_star):
        star_label = spouse_name if ln_shishen == spouse_star else second_name
        s.add(4, f"流年{star_label}合日主→婚期最强信号", "配偶星合入日主 (段建业: 星宫同现)")

    # 日柱天合地合 + 配偶星
    if gong_he and ln_shishen == spouse_star:
        s.add(4, f"流年与日柱天合地合+{spouse_name}透干")

    # 天喜入命 + 合夫妻宫
    if ln_branch == tianxi_dz and (gong_he or gong_sanhe):
        s.add(3, "天喜入命+合夫妻宫→婚期")
    elif ln_branch == tianxi_dz:
        s.add(2, "流年天喜入命")

    # 合动天喜 + 夫妻宫引动
    if tianxi_activated and (gong_he or gong_sanhe or gong_chong):
        s.add(3, "流年合动天喜+夫妻宫引动→婚期")

    # 配偶星合入夫妻宫
    if ln_shishen in (spouse_star, second_star) and gong_he:
        s.add(3, f"配偶星透干合入夫妻宫")

    # 地支藏配偶星 + 合夫妻宫
    if has_spouse_in_branch and (gong_he or gong_sanhe):
        s.add(3, f"地支{spouse_in_branch_label}合入夫妻宫→婚期")

    # 红鸾/天喜/桃花叠加 + 配偶星
    triple = sum([ln_branch == hongluan, ln_branch == tianxi_dz, ln_branch == taohua])
    if triple >= 2 and (ln_shishen in (spouse_star, second_star) or has_spouse_in_branch):
        s.add(3, "红鸾/天喜/桃花叠加+配偶星")

    # 红鸾+配偶星
    if ln_branch == hongluan and (ln_shishen in (spouse_star, second_star) or has_spouse_in_branch):
        s.add(2, "红鸾入命+配偶星")

    # 地支藏配偶星 — 成人+3, 学生+1(暗恋非婚)
    if has_spouse_in_branch:
        sp_visible = ln_shishen in (spouse_star, second_star)
        is_student = age and age <= 21
        if sp_visible:
            s.add(3, f"干支皆见{spouse_in_branch_label}(配偶星透+藏)", "配偶星公开→正缘/婚期")
        elif is_student:
            s.add(1, f"地支暗藏{spouse_in_branch_label}(配偶星·学生)", "藏干不透+学生→暗恋, 待透干之年转正")
        else:
            s.add(3, f"地支暗藏{spouse_in_branch_label}(配偶星·不透干)", "藏干不透→暗处流动, 但成人仍可成婚")

    # 流年合夫妻宫（弱因子，需搭配配偶星或天喜）
    if gong_he:
        s.add(1, "流年合夫妻宫")
    if gong_sanhe:
        s.add(1, "流年三合夫妻宫")

    # 配偶星透干（有根=有力, 无根=虚浮）
    if ln_shishen == spouse_star:
        if _has_root(ln_stem, ln_branch):
            s.add(2, f"流年{spouse_name}透干有根", "配偶星有力→正缘/正妻")
        else:
            s.add(1, f"流年{spouse_name}透干虚浮", "天干无根→有气无力/机会虚浮")
    if ln_shishen == second_star:
        if _has_root(ln_stem, ln_branch):
            s.add(1, f"流年{second_name}透干有根")
        else:
            s.add(0, f"流年{second_name}透干虚浮", "偏星无根→短暂/非正式")

    # ════════════════════════════════════════════════
    # 负面因子（婚变/离婚风险）
    # ════════════════════════════════════════════════

    # 冲夫妻宫
    if gong_chong:
        if ln_shishen == Shishen.偏官:
            s.add(-3, "流年冲夫妻宫+七杀→婚变危机", "段建业: 夫宫冲穿必离婚")
        else:
            s.add(-2, "流年冲夫妻宫", "夫妻宫逢冲→感情波动/婚姻危机")

    # 比劫夺财(男) / 比劫争官(女) — 弱风险，不抵消婚期
    if ln_shishen == Shishen.劫财:
        if gender == "男":
            s.add(-1, "劫财夺财→感情竞争", "比劫争妻/注意第三者 (段建业)")
        else:
            s.add(-1, "劫财争合→感情竞争", "比劫争夫/注意三角关系 (段建业)")

    # 伤官见官(女命)
    if gender == "女" and ln_shishen == Shishen.伤官:
        s.add(-3, "伤官克官→婚姻危机", "伤官年→女命婚姻高危年 (段建业)")

    # 夫妻宫被穿害
    for br_dummy in []:  # placeholder — actual check would need all_branches
        pass
    # (简化: 穿害在人际模块已处理, 此处不重复)

    # 空亡（仅在总分≥3时才扣分，避免弱信号被空亡全吞）
    kw = _kongwang_branches(day_master, day_branch)
    if _is_kongwang(ln_branch, kw) and s.total >= 3:
        s.add(-1, "流年落空亡", "强婚期落空亡→真实但结果虚浮")

    # ════════════════════════════════════════════════
    # 输出判断
    # ════════════════════════════════════════════════
    if s.is_significant():
        # 学生年龄段(≤21岁): 婚嫁降级为桃花(只恋不爱, 不论婚嫁)
        cat = "婚嫁"
        pred_cat = "婚嫁"
        if age and age <= 21:
            cat = "桃花"
            pred_cat = "桃花"
        # v0.10.1: 仅≥★2输出——★1弱信号不独立发信号
        if s.strength >= 2:
            signals.append(EventSignal(
                category=cat,
                direction=s.direction,
                strength=s.strength,
                prediction=_make_prediction(pred_cat, s.direction, s.strength, s.triggers(), s.notes()),
                triggers=s.triggers(),
                notes=s.notes(),
            ))
    return signals


# ═══════════════════════════════════════════════════════════════
# 4. 事业/工作变动
# ═══════════════════════════════════════════════════════════════

def detect_shiye_signals(ln_stem: Tiangan, ln_branch: Dizhi,
                         day_master: Tiangan, year_branch: Dizhi,
                         month_branch: Dizhi,
                         day_branch: Dizhi,
                         hour_branch: Dizhi | None = None,
                         dayun_stem: Tiangan | None = None,
                         dayun_branch: Dizhi | None = None,
                         favorable: set[str] | None = None) -> list[EventSignal]:
    """检测事业/工作变动信号 — v0.5.0: 打分制"""
    signals: list[EventSignal] = []
    ln_shishen = get_ten_god(day_master, ln_stem)
    yima = YIMA.get(year_branch)
    lu = TIANGAN_LU.get(day_master)
    s = ScoreAccumulator(favorable)
    fav = is_favorable(ln_shishen, favorable)
    s.set_shishen(ln_shishen.value, fav)
    s.set_modulate(False)  # 事业只标记不调分（跳槽/晋升不因忌神而消失）

    is_guan = ln_shishen in (Shishen.正官, Shishen.偏官)
    is_ying = ln_shishen in (Shishen.正印, Shishen.偏印)
    is_shang = ln_shishen == Shishen.伤官
    is_shishang = ln_shishen in (Shishen.食神, Shishen.伤官)

    # ── 正面: 晋升/机会 ──
    if is_guan and _has_tiangan_wuhe(ln_stem, day_master):
        s.add(4, "官来合我→晋升/上级赏识", "流年官星合日主 (textbook)")

    # 财官双透
    cai_types = (Shishen.正财, Shishen.偏财)
    ln_cg = [get_ten_god(day_master, hs.stem) for hs in DIZHI_CANGGAN.get(ln_branch, [])]
    if is_guan and any(c in cai_types for c in ln_cg):
        s.add(4, "财官双美→加薪+晋升同现", "财生官 (textbook)")

    # 官印相生
    if is_guan and dayun_stem:
        if get_ten_god(day_master, dayun_stem) in (Shishen.正印, Shishen.偏印):
            s.add(3, "大运印+流年官→官印相生晋升")

    # 禄神到位（固定: 临官总是好事）
    if ln_branch == lu:
        s.add(3, "禄神到位→事业自我实现", "日主临官/能量充足", fixed=True)

    # 官星到位
    if is_guan:
        has_cai = any(c in cai_types for c in ln_cg)
        if has_cai:
            s.add(2, "官星到位+财生官", "间接晋升/加薪")
        else:
            s.add(2, "流年官星到位")

    # 杀印相生
    if ln_shishen == Shishen.偏官 and Shishen.偏印 in ln_cg:
        s.add(2, "偏官+偏印→杀印相生", "压力转化动力")

    # 地支藏官
    if not is_guan:
        if any(c in (Shishen.正官, Shishen.偏官) for c in ln_cg):
            guan_l = "正官" if Shishen.正官 in ln_cg else "偏官"
            s.add(2, f"地支藏{guan_l}→隐性晋升机会")

    # 驿马+官/食伤/财 → 工作变动
    if ln_branch == yima:
        if is_guan:
            s.add(2, "驿马+官星→工作调动")
        elif is_shishang:
            s.add(1, "驿马+食伤→主动跳槽/创业")
        elif ln_shishen in (Shishen.正财, Shishen.偏财):
            s.add(1, "驿马+财星→为财换工作")
        else:
            s.add(1, "流年驿马")

    # 印星 → 入职签约（固定: 签约不因忌神失效）
    if is_ying:
        y_l = "正印" if ln_shishen == Shishen.正印 else "偏印"
        s.add(1, f"印星透干→签约/入职 ({y_l})", fixed=True)

    # 冲月柱(事业宫)（固定: 环境变动不因喜忌消失）
    if _has_branch_interaction(month_branch, ln_branch, "六冲"):
        s.add(1, "冲月柱(事业宫)→工作环境变动", fixed=True)

    # 冲时柱(门户)
    if hour_branch and _has_branch_interaction(hour_branch, ln_branch, "六冲"):
        s.add(1, "冲时柱→工作地点变动", fixed=True)

    # ── 负面: 挫折/风险 (方向固定，不受喜忌翻转) ──
    if is_shang:
        s.add(-1, "伤官透干→想改变/离职风险", "伤官=变革冲动 (textbook)", fixed=True)
        s.guarantee(2)

    if ln_shishen == Shishen.偏印 and is_shishang:
        s.add(-2, "枭神夺食→决策失误/事业受阻", fixed=True)
        s.guarantee(2)

    if dayun_branch and _has_branch_interaction(dayun_branch, ln_branch, "六冲"):
        tianke = dayun_stem and ln_stem and _is_ke_wx(ln_stem.wuxing, dayun_stem.wuxing)
        s.add(-2 if tianke else -1, "天克地冲→重大变动" if tianke else "大运流年冲→环境变化", fixed=True)

    if is_guan:
        dn_s = get_ten_god(day_master, dayun_stem) if dayun_stem else None
        if dn_s in (Shishen.正官, Shishen.偏官) and dn_s != ln_shishen:
            s.add(-1, "官杀混杂→选择困难/多重压力", fixed=True)

    # 空亡
    if is_guan:
        kw_s = _kongwang_branches(day_master, day_branch)
        if _is_kongwang(ln_branch, kw_s) and s.total >= 2:
            s.add(-1, "官星落空亡→机会虚浮", fixed=True)

    if s.is_significant():
        signals.append(EventSignal(
            category="事业",
            direction=s.direction,
            strength=s.strength,
            prediction=_make_prediction("事业", s.direction, s.strength, s.triggers(), s.notes()),
            triggers=s.triggers(),
            notes=s.notes(),
        ))
    return signals


# ═══════════════════════════════════════════════════════════════
# 5. 财运
# ═══════════════════════════════════════════════════════════════

def detect_caiyun_signals(ln_stem: Tiangan, ln_branch: Dizhi,
                          day_master: Tiangan, year_branch: Dizhi,
                          day_branch: Dizhi,
                          favorable: set[str] | None = None) -> list[EventSignal]:
    """检测财运信号 — v0.5.0: 打分制"""
    signals: list[EventSignal] = []
    ln_shishen = get_ten_god(day_master, ln_stem)
    s = ScoreAccumulator(favorable)
    fav = is_favorable(ln_shishen, favorable)
    s.set_shishen(ln_shishen.value, fav)

    is_cai = ln_shishen in (Shishen.正财, Shishen.偏财)
    is_piancai = ln_shishen == Shishen.偏财
    is_shishang = ln_shishen in (Shishen.食神, Shishen.伤官)
    is_bijian = ln_shishen == Shishen.比肩
    is_jiecai = ln_shishen == Shishen.劫财

    fav = is_favorable(ln_shishen, favorable)
    yima = YIMA.get(year_branch)
    caiku = get_caiku_branch(day_master)
    lu_cai = TIANGAN_LU.get(day_master)
    cs_cai = _changsheng_status(day_master, ln_branch)
    is_weak = cs_cai in ("死", "病", "绝", "墓")

    # ── 正面: 得财 ──
    if _has_tiangan_wuhe(ln_stem, day_master):
        hua_wx = TIANGAN_WUHE.get((ln_stem, day_master)) or TIANGAN_WUHE.get((day_master, ln_stem))
        from .enums import Wuxing
        if hua_wx and _is_ke_wx(day_master.wuxing, hua_wx):
            s.add(2 if is_weak else 4, "财来合我→化财", "身弱不担财→大额支出" if is_weak else "最直接的得财信号 (textbook)")

    if _has_branch_interaction(ln_branch, caiku, "六冲"):
        s.add(3, "冲开财库→财务重大变动", "喜财则发财/忌财则破财 (textbook)")

    # ── 墓库相冲核爆（v0.8.0: 涉及财库时升级为资金巨变）──
    from .interactions import analyze_muku_chong
    muku_cai_check = [ln_branch]
    muku_cai_results = analyze_muku_chong(muku_cai_check, day_master, caiku_branch=caiku)
    for mr in muku_cai_results:
        if caiku in mr.pair:
            s.add(4, f"墓库相冲({mr.name})冲开财库→资金巨变",
                  f"土气×{mr.tu_boost}倍+财库冲开→"
                  f"{'暴富机会' if fav is not False else '大破财风险'}")
        else:
            # 墓库冲虽不涉财库，但全局五行失衡
            s.add(-2, f"墓库相冲({mr.name})→全局五行失衡",
                  "土气暴增→间接影响财运稳定", fixed=True)

    tianyi_cy = _TIANYI_FLAT.get(day_master)
    if is_cai and tianyi_cy and ln_branch in tianyi_cy:
        s.add(4, "财星+天乙贵人→贵人带财", "收入增+贵人助 (textbook)")

    if is_shishang and cs_cai in ("临官", "帝旺", "冠带"):
        s.add(3, "食伤生财+身强→财可得", "靠技能/创意赚钱 (textbook)")
    elif is_shishang:
        s.add(2, "食伤生财", "靠技能/创意赚钱" if fav is not False else "投机冲动消费")
        s.guarantee(2)

    if is_cai:
        cai_l = "正财" if ln_shishen == Shishen.正财 else "偏财"
        s.add(3, f"流年{cai_l}透干", f"{cai_l}年→财运关注 (textbook)")

    if is_piancai and ln_branch == yima:
        s.add(3, "偏财+驿马→远方得财/投资机会")

    cai_types_cy = (Shishen.正财, Shishen.偏财)
    if not is_cai:
        ln_cg_cy = [get_ten_god(day_master, hs.stem) for hs in DIZHI_CANGGAN.get(ln_branch, [])]
        if any(c in cai_types_cy for c in ln_cg_cy):
            c_l = "正财" if Shishen.正财 in ln_cg_cy else "偏财"
            s.add(3, f"地支藏{c_l}→隐性得财", "暗财/偏门收入 (段建业)")

    # ── 负面: 破财 ──
    if is_jiecai and fav is not True:
        s.add(-2, "劫财夺财→破财/被借钱", "劫财为忌→注意破耗 (textbook)")
        s.guarantee(2)
    elif is_jiecai:
        s.add(-1, "劫财透干→开销增大")
    elif is_bijian:
        s.add(-1, "比肩透干→竞争分财/开销", "比肩年→注意同辈竞争 (textbook)" if fav is False else "比肩→社交开销增加")

    if is_cai and _has_branch_interaction(ln_branch, day_branch, "六冲"):
        s.add(-2, "财星+冲夫妻宫→财损风险")

    if lu_cai and _has_branch_interaction(ln_branch, lu_cai, "六冲"):
        s.add(-2, "冲禄→破财/花费大增")

    kw_cy = _kongwang_branches(day_master, day_branch)
    if _is_kongwang(ln_branch, kw_cy) and is_cai:
        s.add(-1, "财星落空亡→得财虚浮")

    if s.is_significant():
        signals.append(EventSignal(
            category="财运",
            direction=s.direction,
            strength=s.strength,
            prediction=_make_prediction("财运", s.direction, s.strength, s.triggers(), s.notes()),
            triggers=s.triggers(),
            notes=s.notes(),
        ))
    return signals

    return signals


def _has_root(stem: Tiangan, branch: Dizhi) -> bool:
    """天干在地支是否有根(同五行藏干)。无根=虚浮无力。"""
    wx = stem.wuxing
    for hs in DIZHI_CANGGAN.get(branch, []):
        if hs.stem.wuxing == wx:
            return True
    return False

def _is_ke_wx(a, b) -> bool:
    """a 五行克 b 五行？"""
    from .enums import Wuxing
    ke_map = {
        Wuxing.木: Wuxing.土, Wuxing.土: Wuxing.水,
        Wuxing.水: Wuxing.火, Wuxing.火: Wuxing.金, Wuxing.金: Wuxing.木,
    }
    return ke_map.get(a) == b


# ═══════════════════════════════════════════════════════════════
# 6. 健康
# ═══════════════════════════════════════════════════════════════

def detect_jiankang_signals(ln_stem: Tiangan, ln_branch: Dizhi,
                            day_branch: Dizhi, day_master: Tiangan,
                            year_branch: Dizhi,
                            dayun_stem: Tiangan | None = None,
                            dayun_branch: Dizhi | None = None,
                            favorable: set[str] | None = None,
                            all_branches: tuple[Dizhi, ...] = (),
                            health_profile: dict | None = None,
                            first_year: bool = False,
                            ) -> list[EventSignal]:
    """检测健康信号 — v0.10.0: +调候体质筛查 + 五行脏腑预警"""
    signals: list[EventSignal] = []
    ln_shishen = get_ten_god(day_master, ln_stem)

    strength = 0
    triggers = []
    notes = []

    fav = is_favorable(ln_shishen, favorable)

    # ── 多柱联动: 三合官杀局 ──
    # 流年+大运+原局三合官杀局 → 官杀过旺克身
    dm_wx = day_master.wuxing
    from .enums import Wuxing
    ke_wx_map = {Wuxing.木: Wuxing.土, Wuxing.火: Wuxing.金, Wuxing.土: Wuxing.水,
                 Wuxing.金: Wuxing.木, Wuxing.水: Wuxing.火}
    guansha_wx = ke_wx_map.get(dm_wx)  # 克日主的五行=官杀

    if guansha_wx:
        # 找对应的三合局(如官杀=火→寅午戌)
        sanhe_wx = {Wuxing.木: {Dizhi.亥, Dizhi.卯, Dizhi.未},
                    Wuxing.火: {Dizhi.寅, Dizhi.午, Dizhi.戌},
                    Wuxing.金: {Dizhi.巳, Dizhi.酉, Dizhi.丑},
                    Wuxing.水: {Dizhi.申, Dizhi.子, Dizhi.辰}}
        target_trio = sanhe_wx.get(guansha_wx, set())
        # 收集所有相关地支
        all_dz = set(all_branches)
        if dayun_branch:
            all_dz.add(dayun_branch)
        all_dz.add(ln_branch)
        # 计算命中数
        hits = len(target_trio & all_dz)
        if hits >= 3:
            strength = 3
            triggers.append(f"三合官杀局(流年+大运+原局){hits}柱→克身重灾")
            notes.append("官杀汇聚成局→防重大疾病/手术/意外 (《渊海子平》)")

    # ── 多柱联动: 羊刃聚会 ──
    yangren_jk = TIANGAN_YANGREN.get(day_master)
    if yangren_jk:
        all_dz_y = set(all_branches)
        if dayun_branch:
            all_dz_y.add(dayun_branch)
        all_dz_y.add(ln_branch)
        yr_count = sum(1 for dz in all_dz_y if dz == yangren_jk)
        if yr_count >= 3:
            strength = max(strength, 3)
            triggers.append(f"羊刃聚会({yr_count}重)→血光/手术/中风")
            notes.append("多柱羊刃汇聚→防意外血光/心脑血管 (textbook: 五羊刃聚会中风案)")

    # ── 多柱联动: 墓库相冲核爆（v0.8.0）──
    # 流年引动原局/大运中辰戌或丑未冲 → 土气激增+杂气损毁
    # v0.10.1: 仅流年参与的墓库冲才触发年度健康信号（原局墓库冲是体质，非年度事件）
    from .interactions import analyze_muku_chong
    muku_branches = list(all_branches)
    if dayun_branch:
        muku_branches.append(dayun_branch)
    muku_branches.append(ln_branch)
    muku_results = analyze_muku_chong(muku_branches, day_master)
    for mr in muku_results:
        if ln_branch not in mr.pair:
            continue  # 流年未参与→原局体质特征，非年度健康事件
        if mr.zaqi_damaged:
            strength = max(strength, 2)
            triggers.append(f"流年引动墓库相冲({mr.name})→杂气损毁")
            notes.append(mr.health_note)
            notes.append(f"土气×{mr.tu_boost}倍暴增→脾胃消化系统负担加重")
        if day_branch in mr.pair or (dayun_branch and dayun_branch in mr.pair):
            strength = max(strength, 3)
            triggers.append("墓库冲涉日柱/大运→重灾级")
            notes.append("墓库冲直击日主根基→防突发重病/手术")

    # ═══ ★★★ 级别 ═══

    # 岁运并临+日柱受冲（需要第二个凶信号才3★）
    is_suiyun_binglin = (dayun_stem == ln_stem and dayun_branch == ln_branch)
    if is_suiyun_binglin and _has_branch_interaction(day_branch, ln_branch, "六冲"):
        # 检查是否有额外凶信号（七杀/偏印/三刑等）
        has_extra = (ln_shishen in (Shishen.偏官, Shishen.偏印) or
                     _changsheng_status(day_master, ln_branch) in ("死", "绝"))
        if has_extra:
            strength = 3
            triggers.append("岁运并临+日柱受冲+凶星叠加")
            notes.append("多重凶信号叠加→需高度重视健康安全")
        else:
            strength = 2
            triggers.append("岁运并临+日柱受冲")
            notes.append("注意健康/安全，避免重大决策")

    # 羊刃逢冲 + 羊刃聚会（阴干+阳干通用）
    yangren = TIANGAN_YANGREN.get(day_master)
    if ln_branch == yangren:
        chong_target = chong_pair(ln_branch)
        if dayun_branch == chong_target:
            strength = 3
            triggers.append("羊刃逢冲+大运来冲")
            notes.append("大运冲流年羊刃→防意外血光/手术")
        elif _has_branch_interaction(ln_branch, chong_target, "六冲"):
            strength = max(strength, 2)
            triggers.append("羊刃逢冲")
            notes.append("羊刃逢冲→注意运动安全，避免冲突")

    # 流年临帝旺之地(禄/羊刃) → 对所有天干通用
    if not yangren:  # 阴干无羊刃时，禄/帝旺等同羊刃效应
        cs_temp = _changsheng_status(day_master, ln_branch)
        if cs_temp in ("帝旺", "临官"):
            # 临官+七杀/偏官叠加 → 旺极招灾
            has_sha_risk = any(
                get_ten_god(day_master, hs.stem) == Shishen.偏官
                for hs in DIZHI_CANGGAN.get(ln_branch, [])
            )
            if has_sha_risk:
                strength = max(strength, 2)
                triggers.append("流年临禄旺之地+藏七杀")
                notes.append("旺极+七杀→防意外血光/心脑血管 (textbook)")
            elif ln_branch == TIANGAN_LU.get(day_master):
                strength = max(strength, 1)
                triggers.append("流年临禄地")
                notes.append("禄地太旺→注意劳逸结合，防止过劳")

    # ═══ ★★ 级别 ═══

    # 岁运并临 (calibration: 2026 徐继文，喜用非凶)
    if is_suiyun_binglin:
        strength = max(strength, 2)
        triggers.append("岁运并临")
        notes.append("岁运并临≠必然凶；喜用则凶性大减 (校准: 案例A2026)")

    # 日柱天克地冲（降级: 2★改为1★基础，有额外凶星才2★）
    if _has_branch_interaction(day_branch, ln_branch, "六冲"):
        if strength > 0:  # 已有其他健康信号→叠加
            strength = max(strength, 2)
            triggers.append("流年与日柱天克地冲→叠加")
        else:
            strength = max(strength, 1)
            triggers.append("流年冲日柱")
            notes.append("自身或配偶有波动，注意休息")

    # 日主入流年死/绝/病/墓（十二长生）— 仅叠加，需至少2个其他信号
    cs = _changsheng_status(day_master, ln_branch)
    if cs in ("死", "绝", "病", "墓"):
        if strength >= 2:
            strength = max(strength, 2)
            triggers.append(f"日主入流年{cs}地→叠加")
            notes.append(f"日主临{cs}→健康低谷/精力不足 (textbook)")

    # 官杀攻身（七杀旺+无制）
    if ln_shishen == Shishen.偏官 and fav is False:
        strength = max(strength, 2)
        triggers.append("流年七杀攻身")
        notes.append("七杀为忌→压力伤害/意外风险 (textbook)")

    # 地支藏七杀+日主衰 → 隐性七杀攻身
    if not (ln_shishen == Shishen.偏官):
        ln_canggan_sha = [get_ten_god(day_master, hs.stem) for hs in DIZHI_CANGGAN.get(ln_branch, [])]
        has_sha_in_branch = Shishen.偏官 in ln_canggan_sha
        cs_sha = _changsheng_status(day_master, ln_branch)
        if has_sha_in_branch and cs_sha in ("病", "死", "绝", "墓"):
            strength = max(strength, 2)
            triggers.append("流年地支藏七杀+日主衰")
            notes.append("隐性七杀攻身+身弱→健康风险/意外手术 (textbook)")

    # 枭神夺食
    if ln_shishen == Shishen.偏印 and not is_suiyun_binglin:
        # 检查是否有食神被夺（食神为日主所生+同性）
        # 简化：偏印年+地支含食神日主衰地
        shen_shishen = get_ten_god(day_master, ln_stem)
        if shen_shishen == Shishen.偏印:
            cs2 = _changsheng_status(day_master, ln_branch)
            if cs2 in ("病", "死", "绝"):
                strength = max(strength, 2)
                triggers.append("枭神夺食")
                notes.append("影响饮食消化/精神状态 (textbook)")

    # 三刑入命 — 仅叠加
    if strength >= 2:
        xt_hits = []
        if _has_branch_interaction(day_branch, ln_branch, "相刑"):
            xt_hits.append("日柱")
        if dayun_branch and _has_branch_interaction(dayun_branch, ln_branch, "相刑"):
            xt_hits.append("大运")
        # 自刑：必须有伏吟（流年支与四柱重复）才算
        if ln_branch in (Dizhi.辰, Dizhi.午, Dizhi.酉, Dizhi.亥):
            if day_branch == ln_branch:
                xt_hits.append("日柱自刑")
            elif dayun_branch == ln_branch:
                xt_hits.append("大运自刑")
        if xt_hits:
            strength = max(strength, 2)
            triggers.append(f"三刑入命({'&'.join(xt_hits)})")
            notes.append("刑入命→健康隐患/慢性问题 (textbook)")

    # ═══ ★ 级别 ═══

    # 灾煞/丧门/吊客 — 流年逢之叠加健康风险（2026-05-23 WebSearch 验证）
    from ._constants import ZAISHA, SANGMEN, DIAOKE
    zaisha_target = ZAISHA.get(year_branch)
    sangmen_target = SANGMEN.get(year_branch)
    diaoke_target = DIAOKE.get(year_branch)
    if zaisha_target and ln_branch == zaisha_target:
        if strength >= 2:
            strength = max(strength, 2)
            triggers.append("流年逢灾煞→叠加")
            notes.append("灾煞(白虎)→防意外血光")
    if sangmen_target and ln_branch == sangmen_target:
        if strength >= 2:
            strength = max(strength, 2)
            triggers.append("流年逢丧门→叠加")
            notes.append("丧门→注意家人健康/白事")
    if diaoke_target and ln_branch == diaoke_target:
        if strength >= 2:
            strength = max(strength, 2)
            triggers.append("流年逢吊客→叠加")
            notes.append("吊客→注意六亲孝服")

    # 七杀透干
    if ln_shishen == Shishen.偏官:
        strength = max(strength, 1)
        triggers.append("流年七杀透干")
        # 凶星落空则凶减（WebSearch 2026-05-23 验证）
        kw_jk = _kongwang_branches(day_master, day_branch)
        if _is_kongwang(ln_branch, kw_jk):
            notes.append("七杀落空亡→凶性大减")
            strength = max(strength - 1, 1)
        elif fav is True:
            notes.append("七杀为喜→压力可控")
        elif fav is False:
            notes.append("七杀为忌→注意压力")

    # ── v0.10.0: 五行脏腑交叉引用 ──
    # 已有健康触发时，附加对应脏腑风险提示
    if triggers and health_profile:
        wx_risks = health_profile.get("wuxing_risks", [])
        if wx_risks:
            high_risks = [r for r in wx_risks if r["severity"] == "高"]
            if high_risks:
                organ_labels = "、".join(r["organ"] for r in high_risks[:3])
                notes.append(f"体质弱点（{organ_labels}）：{'; '.join(r['note'] for r in high_risks[:2])}")

    # ── v0.10.0: 调候体质基线筛查（首年输出体质画像）──
    if first_year and health_profile:
        tiaohou_label = health_profile.get("tiaohou_label", "")
        if "高风险" in tiaohou_label:
            strength = max(strength, 1)
            triggers.append(f"体质基线：{tiaohou_label}")
            for risk in health_profile.get("tiaohou_risks", [])[:2]:
                notes.append(risk)
            if health_profile.get("tiaohou_advice"):
                notes.append(health_profile["tiaohou_advice"])

    if triggers:
        signals.append(EventSignal(
            category="健康",
            direction="负面",
            strength=min(strength, 3),
            prediction=_make_prediction("健康", "负面", min(strength,3), triggers, notes),
            triggers=triggers,
            notes=notes,
        ))
    return signals


# ═══════════════════════════════════════════════════════════════
# 7. 搬迁/远行
# ═══════════════════════════════════════════════════════════════

def detect_banqian_signals(ln_branch: Dizhi,
                           year_branch: Dizhi, day_branch: Dizhi,
                           month_branch: Dizhi,
                           hour_branch: Dizhi | None = None,
                           dayun_branch: Dizhi | None = None,
                           dayun_stem: Tiangan | None = None,
                           ln_stem: Tiangan | None = None,
                           day_master: Tiangan | None = None,
                           favorable: set[str] | None = None) -> list[EventSignal]:
    """检测搬迁/远行信号 — v0.3.0 增强版"""
    signals: list[EventSignal] = []
    yima = YIMA.get(year_branch)

    strength = 0
    triggers = []
    notes = []

    is_yima_yr = ln_branch == yima
    ln_shishen = get_ten_god(day_master, ln_stem) if day_master and ln_stem else None

    # ═══ ★★★ 级别 ═══

    # 大运流年双驿马
    if is_yima_yr and dayun_branch and dayun_branch == yima:
        strength = 3
        triggers.append("大运流年双驿马")
        notes.append("双驿马→重大搬迁/远行 (textbook)")

    # ═══ ★★ 级别 ═══

    # 驒马逢冲（流年驿马与原局/大运相冲）
    if is_yima_yr:
        chong_dz = chong_pair(ln_branch)
        chong_yuanju = _has_branch_interaction(year_branch, chong_dz, "六冲") or \
                       _has_branch_interaction(day_branch, chong_dz, "六冲") or \
                       _has_branch_interaction(month_branch, chong_dz, "六冲")
        chong_dayun = dayun_branch and _has_branch_interaction(dayun_branch, chong_dz, "六冲")
        if chong_yuanju or chong_dayun:
            strength = max(strength, 2)
            triggers.append("流年驿马逢冲")
            notes.append("驿马逢冲→必动 (textbook)")

    # 驿马年
    if is_yima_yr:
        strength = max(strength, 2)
        triggers.append("流年驿马")

    # 大运驿马+流年合驿马
    if dayun_branch and dayun_branch == yima and _has_branch_interaction(ln_branch, yima, "六合"):
        strength = max(strength, 2)
        triggers.append("大运驿马+流年合动")
        notes.append("大运驿马被流年合动→当年搬迁 (textbook)")

    # 驿马+财星/官星 → 因工作/求财远行
    if is_yima_yr and ln_shishen:
        if ln_shishen in (Shishen.正财, Shishen.偏财):
            strength = max(strength, 2)
            triggers.append("驿马+财星→求财远行")
        elif ln_shishen in (Shishen.正官, Shishen.偏官):
            strength = max(strength, 2)
            triggers.append("驿马+官星→工作调动远行")

    # 冲月柱（环境宫）
    if _has_branch_interaction(month_branch, ln_branch, "六冲"):
        strength = max(strength, 2)
        triggers.append("流年冲月柱(环境宫)")
        notes.append("冲月柱→环境/居住地变动")

    # 冲年柱（祖基宫）
    if _has_branch_interaction(year_branch, ln_branch, "六冲"):
        strength = max(strength, 2)
        triggers.append("流年冲年柱(祖基宫)")

    # 冲时柱（门户）
    if hour_branch and _has_branch_interaction(hour_branch, ln_branch, "六冲"):
        strength = max(strength, 2)
        triggers.append("流年冲时柱(门户)")
        notes.append("冲时柱→门户变动/搬家 (textbook)")

    # 合月柱（环境宫被合动）
    if _has_branch_interaction(month_branch, ln_branch, "六合") or _has_branch_interaction(month_branch, ln_branch, "三合"):
        strength = max(strength, 2)
        triggers.append("流年合月柱(环境宫)")
        notes.append("合动月柱→环境变化/搬迁移居")

    # 驿马+印星 → 因学业/工作调动搬迁
    if is_yima_yr and ln_shishen in (Shishen.正印, Shishen.偏印):
        strength = max(strength, 2)
        triggers.append("驿马+印星→学习/工作调动搬迁")
        notes.append("印星主文书/合同→因入学/入职/调令而搬迁 (textbook)")

    # ═══ ★ 级别 ═══

    if is_yima_yr and strength < 2:
        strength = 1
        triggers.append("流年驿马")

    if triggers:
        signals.append(EventSignal(
            category="搬迁",
            direction="中性",
            strength=min(strength, 3),
            prediction=_make_prediction("搬迁", "中性", min(strength,3), triggers, notes),
            triggers=triggers,
            notes=notes,
        ))
    return signals


# ═══════════════════════════════════════════════════════════════
# 8. 个人状态
# ═══════════════════════════════════════════════════════════════

def detect_zhuangtai_signals(ln_stem: Tiangan, ln_branch: Dizhi,
                              day_master: Tiangan, day_branch: Dizhi,
                              dayun_stem: Tiangan | None = None,
                              dayun_branch: Dizhi | None = None,
                              favorable: set[str] | None = None) -> list[EventSignal]:
    """检测个人状态信号（精力/自信/情绪）"""
    signals: list[EventSignal] = []
    ln_shishen = get_ten_god(day_master, ln_stem)
    fav = is_favorable(ln_shishen, favorable)
    lu = TIANGAN_LU.get(day_master)

    strength = 0
    triggers = []
    notes = []

    # ★★★: 禄神到位（日主临官）
    if ln_branch == lu:
        strength = 3
        triggers.append(f"流年{lu.value}为日主禄地")
        notes.append("禄神到位→精力充沛/自信高峰 (textbook)")

    # ★★★: 七杀攻身+身弱
    if ln_shishen == Shishen.偏官 and fav is False:
        strength = max(strength, 3)
        triggers.append("流年七杀攻身")
        notes.append("压力大/焦虑/身心疲惫 (textbook)")

    # ★★: 食神吐秀
    if ln_shishen == Shishen.食神:
        strength = max(strength, 2)
        triggers.append("流年食神透干")
        notes.append("心态放松/创造力强/享受生活" if fav is not False else "食神为忌→懒散贪玩")

    # ★★: 伤官透干
    if ln_shishen == Shishen.伤官:
        strength = max(strength, 2)
        triggers.append("流年伤官透干")
        notes.append("思维活跃/反叛/想改变 (textbook)")

    # ★★: 正印护身
    if ln_shishen in (Shishen.正印, Shishen.偏印) and fav is not False:
        strength = max(strength, 2)
        triggers.append("流年印星护身")
        notes.append("内心安稳/有依靠/适合学习 (textbook)")

    # 十二长生状态（独立触发，不依赖已有信号）
    cs = _changsheng_status(day_master, ln_branch)
    if cs in ("帝旺", "临官"):
        strength = max(strength, 2)
        triggers.append(f"日主{cs}")
        notes.append("自身状态佳/精力充沛")
    elif cs in ("死", "病", "绝", "墓"):
        strength = max(strength, 2)
        triggers.append(f"日主{cs}")
        notes.append("自身状态低迷/需休养")

    # 日柱伏吟（流年与日柱相同→个人重大节点）
    if ln_branch == day_branch:
        strength = max(strength, 2)
        triggers.append("流年伏吟日柱")
        notes.append("日柱伏吟→个人状态转折点/情绪波动 (textbook)")

    # 枭神夺食（偏印年+日主食神受制）
    if ln_shishen == Shishen.偏印:
        # 简化: 偏印年本身就压抑
        if fav is False:
            strength = max(strength, 2)
            triggers.append("枭神夺食→思维受限")
            notes.append("偏印为忌→思虑过度/钻牛角尖/情绪压抑")

    if triggers:
        # 方向判断
        _trig_str = str(triggers)
        if ln_branch == lu or "临官" in _trig_str or "帝旺" in _trig_str:
            direction = "正面"
        elif "死" in _trig_str or "病" in _trig_str or "绝" in _trig_str or "墓" in _trig_str:
            direction = "负面"
        elif "伏吟" in _trig_str:
            direction = "中性"
        elif "枭神" in _trig_str:
            direction = "负面"
        elif ln_shishen == Shishen.偏官 and fav is not True:
            direction = "负面"
        elif ln_shishen == Shishen.伤官:
            direction = "中性"
        elif fav is not False:
            direction = "正面"
        else:
            direction = "负面"
        # v0.10.1: 仅≥★3输出——★2模式(食神透干/十二长生/伏吟)太常见，稀释信号价值
        if strength >= 3:
            signals.append(EventSignal(
            category="状态",
            direction=direction,
            strength=min(strength, 3),
            prediction=_make_prediction("状态", direction, min(strength, 3), triggers, notes),
            triggers=triggers,
            notes=notes,
        ))
    return signals


# ═══════════════════════════════════════════════════════════════
# 9. 人际关系
# ═══════════════════════════════════════════════════════════════

def detect_renji_signals(ln_stem: Tiangan, ln_branch: Dizhi,
                          year_branch: Dizhi, month_branch: Dizhi,
                          day_branch: Dizhi, hour_branch: Dizhi,
                          day_master: Tiangan,
                          all_branches: tuple[Dizhi, ...],
                          favorable: set[str] | None = None) -> list[EventSignal]:
    """检测人际关系信号（朋友/同事/社交）— v0.4.0"""
    signals: list[EventSignal] = []
    ln_shishen = get_ten_god(day_master, ln_stem)
    strength = 0
    triggers = []
    notes = []

    is_bijian = ln_shishen == Shishen.比肩
    is_jiecai = ln_shishen == Shishen.劫财
    is_shang = ln_shishen == Shishen.伤官
    fav = is_favorable(ln_shishen, favorable)

    # ── ★★★: 三刑汇聚 ──
    # 流年+命局凑齐三刑(寅巳申/丑未戌/子卯)
    sanxing_sets = [
        ({Dizhi.寅, Dizhi.巳, Dizhi.申}, "寅巳申三刑→官非/人际重大冲突"),
        ({Dizhi.丑, Dizhi.未, Dizhi.戌}, "丑未戌三刑→口舌/纠纷"),
    ]
    for trio, label in sanxing_sets:
        yr_set = set(all_branches)
        yr_set.add(ln_branch)
        if len(trio & yr_set) >= 3:  # 流年+原局凑齐三刑
            strength = max(strength, 3)
            triggers.append(label)
            notes.append("三刑汇聚→重大人际冲突/官非 (《渊海子平》)")
            break

    # ── ★★: 卯辰穿/子未穿等相害 ──
    # 日支参与的害更严重，非日支也有影响
    for br in all_branches:
        if _has_branch_interaction(ln_branch, br, "相害"):
            hai_pair = f"{ln_branch.value}{br.value}"
            if br == day_branch:
                strength = max(strength, 2)
                triggers.append(f"{hai_pair}穿夫妻宫→人际困扰")
                notes.append("夫妻宫被穿→情绪/人际受影响 (textbook)")
            elif br == month_branch:
                strength = max(strength, 2)
                triggers.append(f"{hai_pair}穿月柱→职场人际摩擦")
                notes.append("穿月柱→同事/朋友关系受损")
            else:
                strength = max(strength, 1)
                if not any("穿" in t for t in triggers):
                    triggers.append(f"{hai_pair}穿→隐性人际摩擦")

    # ── ★★: 相刑 ──
    has_xing = False
    for br in all_branches:
        if _has_branch_interaction(ln_branch, br, "相刑"):
            has_xing = True
            break
    if has_xing:
        strength = max(strength, 2)
        triggers.append("流年与原局相刑")
        notes.append("刑→人际摩擦/口舌是非 (textbook)")

    # ── ★★: 比劫夺财/争官 → 人际竞争 ──
    if is_jiecai and fav is not True:
        strength = max(strength, 2)
        triggers.append("劫财透干→朋友竞争/被借钱")
        notes.append("劫财→人际竞争加剧，慎防被友拖累 (段建业)")
    elif is_bijian and fav is False:
        strength = max(strength, 1)
        triggers.append("比肩透干→同辈竞争")
        notes.append("比肩→注意同辈间的竞争比较")

    # ── ★★: 伤官+人际 → 口舌惹事 ──
    if is_shang:
        strength = max(strength, 1)
        triggers.append("伤官透干→言语直接易得罪人")
        notes.append("伤官→直言不讳，注意言语冲突")

    # ── ★: 流年合动 → 社交活跃 ──
    for br in all_branches:
        if _has_branch_interaction(ln_branch, br, "六合"):
            if strength < 2:
                strength = max(strength, 1)
                triggers.append("流年合动→社交活跃")
                notes.append("六合→人缘好/社交机会多")
            break

    # ── ★: 天喜合动 → 社交活跃 ──
    tianxi_rj = TIANXI.get(year_branch)
    if tianxi_rj and (ln_branch == tianxi_rj or _is_in_same_sanhe(ln_branch, tianxi_rj)):
        strength = max(strength, 1)
        triggers.append("流年合动天喜→社交活跃")
        notes.append("天喜年→人缘提升/社交机会增多")

    if triggers:
        is_negative = any(kw in str(triggers) for kw in ["刑", "穿", "劫财", "伤官"])
        direction = "负面" if is_negative else "正面"
        # v0.10.1: 仅≥★2输出——★1弱信号不独立发信号
        if strength >= 2:
            signals.append(EventSignal(
                category="人际",
                direction=direction,
                strength=min(strength, 3),
                prediction=_make_prediction("人际", direction, min(strength, 3), triggers, notes),
                triggers=triggers,
                notes=notes,
            ))
    return signals


# ═══════════════════════════════════════════════════════════════
# 主扫描函数
# ═══════════════════════════════════════════════════════════════

# ═══════════════════════════════════════════════════════════════
# 性格联动 —— 个性调节事件措辞
# ═══════════════════════════════════════════════════════════════

def build_personality_context(day_master: Tiangan, strength: str,
                              favorable_shishen: list[str],
                              harmful_shishen: list[str],
                              pillars_tengan: list[Tiangan],
                              gender: str) -> dict:
    """从命盘数据提取性格关键指标，供流年事件个性化用"""
    ctx = {}

    # 身强弱
    ctx["is_strong"] = "强" in strength
    ctx["is_weak"] = "弱" in strength
    ctx["gender"] = gender

    # 是否有正财/正官合日主 → 感情被动
    from ._constants import TIANGAN_WUHE
    ctx["passive_romance"] = False
    for tg in pillars_tengan:
        pair = (day_master, tg)
        if pair in TIANGAN_WUHE or (tg, day_master) in TIANGAN_WUHE:
            from .ten_gods import get_ten_god
            g = get_ten_god(day_master, tg)
            if g and g.value in ("正财", "正官"):
                ctx["passive_romance"] = True
                break

    # 七杀旺 + 有制 → 果断恢复型
    ctx["resilient"] = False
    if "偏官" in favorable_shishen or "七杀" in favorable_shishen:
        ctx["resilient"] = True

    # 偏印忌神 → 内心疏离
    ctx["inner_withdrawn"] = "偏印" in harmful_shishen

    # 食伤旺 → 外放表达型
    ctx["expressive"] = ("食神" in favorable_shishen or
                         "伤官" in favorable_shishen)

    # 印星旺 → 内敛思考型
    ctx["introspective"] = ("正印" in favorable_shishen or
                            "偏印" in favorable_shishen)

    return ctx


# ═══════════════════════════════════════════════════════════════
# 十神流年权威出处（来源：《渊海子平》《滴天髓》原文）
# ═══════════════════════════════════════════════════════════════

SHISHEN_YEAR_SOURCES = {
    "比肩": (
        "比肩年",
        "《渊海子平·论兄弟姊妹》：「甲木旺相，兄姊争财」— "
        "比肩代表同辈、兄弟、朋友、竞争者。比肩年社交活跃但易有竞争分夺，"
        "合作需谨慎，利益容易被分散。"
    ),
    "劫财": (
        "劫财年",
        "《渊海子平·论妻妾》：「比肩分夺、财临沐浴桃花，主妻妾私通」— "
        "劫财比之比肩争夺性更强，主破财、被借钱、竞争激烈。"
        "男命劫财年注意感情被夺，女命注意闺蜜介入。"
    ),
    "食神": (
        "食神年",
        "《渊海子平·论食神》：「财厚食丰、腹量宽洪、肌体肥大、优游自足、有子息、有寿考」— "
        "食神主享受、口福、才华展现、心宽体胖。食神年心态放松，"
        "适合创作、享受生活，但忌偏印夺食（枭神夺食则福减）。"
    ),
    "伤官": (
        "伤官年",
        "《渊海子平·论伤官》：「伤官见官，为祸百端」「伤官主人多才艺、傲物气高」— "
        "伤官主才华、叛逆、不拘一格、口才出众。伤官年创造力和表达欲强，"
        "但注意言行锋芒，避免与权威冲突。"
    ),
    "正财": (
        "正财年",
        "《渊海子平·论正财》：「大抵吾妻之财也，人之女赉财以事我」— "
        "正财主稳定收入、正妻、务实节俭。正财年适合积累、理财规划，"
        "收入稳定可期。男命正财年正缘运强。"
    ),
    "偏财": (
        "偏财年",
        "《渊海子平》：「偏财，妾也」；《滴天髓·何知章》：「夫论财与论妻之法，可相通也」— "
        "偏财主意外之财、情人、多情慷慨、一掷千金。偏财年消费欲和情感欲望同步增强，"
        "男命异性缘上升，但也容易用情不专。"
    ),
    "正官": (
        "正官年",
        "《渊海子平》：「正气官星者，真君子也，最忌有破」— "
        "正官主事业、名誉、上级、规则约束。正官年适合争取晋升、考试、"
        "建立威信。注意言行合规，忌与上级对抗。"
    ),
    "偏官": (
        "七杀年",
        "《渊海子平·论偏官》：「有制伏则为偏官，无制伏则为七杀」；"
        "「人有偏官，如抱虎而眠，虽借其威足以慑群畜，稍失关防，必为其噬脐」— "
        "七杀主权威、压力、挑战、魄力。有制则化权升职，无制则小人是非。"
        "七杀年压力大但机会也大，关键是'制化'。"
    ),
    "正印": (
        "正印年",
        "《渊海子平》：「生气印绶，利官运畏见财乡」— "
        "正印主学习、贵人、庇护、母亲。正印年适合进修深造、考试考证，"
        "有贵人相助，内心安稳。忌财星来破印。"
    ),
    "偏印": (
        "偏印年",
        "《渊海子平·论食神》：「忌倒食，恐伤其食神」— "
        "偏印（枭神）主偏门学问、孤独思考、洞察力。偏印年适合钻研冷门领域，"
        "但注意人际关系疏离，枭神夺食则福气被打折扣。"
    ),
}


def apply_shishen_year_notes(events: list[EventSignal],
                              shishen_name: str | None) -> None:
    """为所有事件追加流年十神权威出处"""
    if not shishen_name:
        return
    # "七杀" → "偏官" 别名（Shishen 枚举统一用"偏官"）
    lookup_name = "偏官" if shishen_name == "七杀" else shishen_name
    info = SHISHEN_YEAR_SOURCES.get(lookup_name)
    if not info:
        return
    label, source = info
    note_text = f"[{label}] {source}"
    for e in events:
        e.notes.append(note_text)


def apply_personality_notes(events: list[EventSignal],
                            ctx: dict) -> None:
    """为事件追加性格联动备注"""
    for e in events:
        note = ""

        if e.category == "桃花":
            if e.direction == "负面" and ctx.get("resilient"):
                note = "以你的性格，虽有不顺但能较快走出来，不必过度担心"
            elif e.direction == "负面" and ctx.get("introspective"):
                note = "你偏内省，感情波动后建议给自己多一些时间消化，不必急于做决定"
            elif e.direction == "负面":
                note = "感情波动期，注意沟通方式"
            elif e.direction == "正面" and ctx.get("passive_romance"):
                note = "机会出现，但你偏被动——对方可能会先迈出第一步，注意接收信号"
            elif e.direction == "正面" and ctx.get("resilient"):
                note = "你的主动性足够，抓住机会"
            elif e.direction == "正面" and ctx.get("is_strong"):
                note = "自信是最好的吸引力——这个阶段你状态在线，桃花质量也高"
            elif e.direction == "中性" and ctx.get("passive_romance"):
                note = "感情节点期，你倾向于等对方推进——但有时主动一步效果更好"

        elif e.category == "事业":
            if e.direction == "负面" and ctx.get("resilient"):
                note = "你有抗压能力，事业波动期反而可能激发你的潜能"
            elif e.direction == "负面" and ctx.get("is_weak"):
                note = "身弱时期事业压力较大，建议优先保稳，不要在这个阶段做冒险决策"
            elif e.direction == "负面" and ctx.get("is_strong"):
                note = "身强底子好，事业波折反而磨砺你，扛过去就是跃升"
            elif e.direction == "正面" and ctx.get("expressive"):
                note = "以你的才华和表达能力，事业机会能把握得比较好"
            elif e.direction == "正面" and ctx.get("is_strong"):
                note = "身强能担——这个阶段的事业机会你有能力接住，放手去做"

        elif e.category == "财运":
            if e.direction == "负面" and ctx.get("resilient"):
                note = "财务有波动，但你的果断风格有助于及时止损"
            elif e.direction == "负面":
                note = "注意控制消费冲动，这个阶段宜守不宜攻"
            elif e.direction == "正面" and ctx.get("expressive"):
                note = "靠才华和技能赚钱的机会多，发挥你的强项"

        elif e.category == "健康":
            if e.direction == "负面" and ctx.get("resilient"):
                note = "你体质底子好，但仍需注意劳逸结合，不要仗着年轻透支"
            elif e.direction == "负面":
                note = "健康信号值得重视，建议规律作息和定期体检"

        elif e.category == "状态":
            if e.direction == "负面" and ctx.get("inner_withdrawn"):
                note = "你容易在低谷时封闭自己——记得找信任的人聊聊，独处太久反而加重"
            elif e.direction == "负面" and ctx.get("resilient"):
                note = "状态波动是正常的，以你的恢复力，低迷期不会持续太久"

        elif e.category == "人际":
            if e.direction == "负面" and ctx.get("inner_withdrawn"):
                note = "人际摩擦时你倾向回避——有时直接沟通比沉默更有效"
            elif e.direction == "负面":
                note = "注意言辞分寸，这个阶段的人际冲突宜冷处理"

        if note:
            e.personality_note = note


def _check_event_conflicts(events: list[EventSignal],
                          ln_dz: Dizhi, day_branch: Dizhi,
                          day_master: Tiangan, year_branch: Dizhi,
                          month_branch: Dizhi, hour_branch: Dizhi):
    """事件矛盾检查：检测同一年内多个信号之间的冲突，修正强度和方向。

    规则：
    - 桃花+空亡 → 强度-1，"浮桃花不落地"
    - 桃花+冲夫妻宫 → 方向变中性
    - 事业+伤官见官 → 同时输出上升/冲突两面
    - 财+比劫夺财 → 标注社交/感情消费
    - 婚嫁+冲夫妻宫 → 方向变中性
    """
    # 收集事件类别
    cats = {e.category for e in events}
    ev_map = {e.category: e for e in events}

    # 检查流年是否冲夫妻宫（日支）
    chong_fuqi = (ln_dz == chong_pair(day_branch)) if day_branch else False

    # 桃花+冲夫妻宫 → 中性
    if "桃花" in ev_map and chong_fuqi:
        e = ev_map["桃花"]
        if e.direction == "正面":
            e.direction = "中性"
            e.notes.append("流年冲夫妻宫→桃花机会与波动并存，感情节点期")
            if e.strength >= 2:
                e.strength -= 1

    # 婚嫁+冲夫妻宫 → 中性
    if "婚嫁" in ev_map and chong_fuqi:
        e = ev_map["婚嫁"]
        if e.direction == "正面":
            e.direction = "中性"
            e.notes.append("婚年逢冲夫妻宫→婚姻建立可能伴随压力，需沟通")

    # 桃花+财运同时出现 → 感情消费提示
    if "桃花" in cats and "财运" in cats:
        ev_map["桃花"].notes.append("桃花+财运同现→社交和感情消费增加")
        ev_map["财运"].notes.append("财运+桃花同现→部分开支与感情/社交有关")

    # 事业+搬迁同时出现 → 可能是工作地点变动
    if "事业" in cats and "搬迁" in cats:
        ev_map["事业"].notes.append("事业+搬迁同现→工作地点或环境可能变动")
        ev_map["搬迁"].notes.append("搬迁+事业同现→搬家可能与工作/学业有关")

    # 健康+事业同时出现 → 注意工作压力影响健康
    if "健康" in cats and "事业" in cats:
        ev_map["健康"].notes.append("健康+事业同现→工作/学业压力可能影响身体")

    # 桃花负面(分手型) + 婚嫁正面 → 婚嫁降级
    # 仅当桃花负面源于分手信号(冲夫妻宫/卯辰穿)才降级, 竞争型(劫财)不降
    if "桃花" in ev_map and "婚嫁" in ev_map:
        th = ev_map["桃花"]
        hj = ev_map["婚嫁"]
        th_trig = str(th.triggers)
        is_breakup_type = ("冲夫妻宫" in th_trig or "卯辰穿" in th_trig)
        if th.direction == "负面" and hj.direction == "正面" and is_breakup_type:
            hj.direction = "中性"
            hj.strength = max(1, hj.strength - 1)
            hj.notes.append("桃花负面(分手型)+婚嫁正面矛盾→婚期信号存疑")


def detect_guanfei_signals(
    ln_tg: Tiangan, ln_dz: Dizhi,
    day_master: Tiangan, day_branch: Dizhi,
    year_branch: Dizhi, month_branch: Dizhi,
    hour_branch: Dizhi,
    dn_tg: Tiangan | None, dn_dz: Dizhi | None,
    natal_shang_guan: bool = False,
    pillars_tengan: list[Tiangan] | None = None,
) -> list[EventSignal]:
    """官非/法律风险检测——伤官见官+流年触发。

    古籍来源：《渊海子平》「伤官见官，为祸百端」；
    《三命通会》「伤官见官，仕途多阻，轻则口舌，重则官非牢狱」

    触发条件（需同时满足）：
    1. 命局有伤官见官（天干透出或地支构成）
    2. 流年天干/大运天干透出正官或伤官
    3. 有冲克激化（流年冲大运/大运冲月柱等）
    """
    if not natal_shang_guan:
        return []

    events: list[EventSignal] = []
    strength = 0
    triggers: list[str] = []
    notes: list[str] = []

    # 大运天干是否透正官/伤官
    dn_shishen = None
    if dn_tg:
        dn_shishen = get_ten_god(day_master, dn_tg)
    dn_is_guan = dn_shishen and dn_shishen.value in ("正官", "偏官")
    dn_is_shang = dn_shishen and dn_shishen.value == "伤官"

    # 流年天干
    ln_shishen = get_ten_god(day_master, ln_tg)
    ln_is_guan = ln_shishen and ln_shishen.value in ("正官", "偏官")
    ln_is_shang = ln_shishen and ln_shishen.value == "伤官"

    # 流年透伤官 → +1
    if ln_is_shang:
        strength += 1
        triggers.append("流年伤官透干")
        notes.append("流年伤官→才华锋芒外露，注意言行不要触碰规则红线")

    # 流年透正官 → +1（伤官见官直接触发）
    if ln_is_guan:
        strength += 1
        triggers.append("流年正官出现→伤官见官触发")
        notes.append("正官到位+伤官冲撞→官非口舌风险升高")

    # 大运透伤官/正官 → +1
    if dn_is_shang or dn_is_guan:
        strength += 1
        triggers.append(f"大运透{dn_shishen.value if dn_shishen else '?'}")
        notes.append(f"大运{dn_shishen.value if dn_shishen else ''}持续施加影响")

    # 流年冲大运 → +1（环境冲击）
    if dn_dz and ln_dz == chong_pair(dn_dz):
        strength += 1
        triggers.append("流年冲大运→环境激变")
        notes.append("流年冲大运→人生阶段被迫改变")

    # 流年合官星 → +1
    if ln_dz and day_branch:
        pair = frozenset({ln_dz, day_branch})
        if pair in DIZHI_LIUHE or pair in DIZHI_SANHE or any(
            pair.issubset(s) for s in DIZHI_SANHE
        ):
            strength += 1
            triggers.append("流年合动日支→牵动自身")

    if strength >= 2:
        direction = "负面"
        if strength == 2:
            pred = "注意法律风险或与权威的冲突，遵守规则，避免冲动行事"
        else:
            pred = "高风险年份——注意法律纠纷、官非诉讼或与权威机构的冲突，切忌触犯规则底线"

        events.append(EventSignal(
            category="官非",
            direction=direction,
            strength=min(strength, 3),
            prediction=pred,
            triggers=triggers,
            notes=notes,
        ))

    return events


# ═══════════════════════════════════════════════════════════════
# 婚嫁↔桃花交叉引用（v0.9.1）
# ═══════════════════════════════════════════════════════════════

def _cross_ref_hunjia_taohua(events: list[EventSignal], age: int = 0):
    """婚嫁与桃花共享触发空间（合冲、配偶星、天喜红鸾），一侧≥2★时应补足另一侧。

    规则:
    1. 成人(>21): 桃花≥2★但无婚嫁 → 派生婚嫁信号（星数=桃花-0或2，取低值）
    2. 婚嫁≥2★ → 派生桃花信号（星数=婚嫁-1），婚嫁必有感情机遇
    3. 学生(≤21): 不派生——婚嫁原已降级为桃花，反向不处理
    """
    taohua_evts = [e for e in events if e.category == "桃花"]
    hunjia_evts = [e for e in events if e.category == "婚嫁"]
    max_th = max((e.strength for e in taohua_evts), default=0)
    max_hj = max((e.strength for e in hunjia_evts), default=0)

    # Rule 1: 成人桃花≥2 → 补婚嫁（max_hj<2：婚嫁本身未达到2★才补）
    if age > 21 and max_th >= 2 and max_hj < 2:
        best = max(taohua_evts, key=lambda e: e.strength)
        derived_strength = min(best.strength, 2)
        events.append(EventSignal(
            category="婚嫁",
            direction=best.direction,
            strength=derived_strength,
            triggers=best.triggers + ["桃花→婚嫁(交叉引用)"],
            notes=best.notes + ["感情信号较强，成年命主→倾向婚姻/长期关系方向"],
        ))

    # Rule 2: 婚嫁≥2 → 补桃花（仅当无原生桃花≥2★时才补，避免重复）
    if max_hj >= 2 and max_th < 2:
        already_derived = any(
            "婚嫁→桃花" in str(t)
            for e in taohua_evts
            for t in (e.triggers or [])
        )
        if not already_derived:
            best = max(hunjia_evts, key=lambda e: e.strength)
            events.append(EventSignal(
                category="桃花",
                direction=best.direction,
                strength=min(best.strength, 2),
                triggers=best.triggers + ["婚嫁→桃花(交叉引用)"],
                notes=best.notes + ["婚嫁信号强→必有感情事件铺垫"],
            ))


# ═══════════════════════════════════════════════════════════════
# 岁运交战处理器（v0.8.0: P6）
# ═══════════════════════════════════════════════════════════════

def _process_suiyun_clash(ln_stem, ln_branch, dn_stem, dn_branch,
                           day_master, dayun_mod: dict | None) -> list[EventSignal]:
    """流年 vs 大运冲突拦截。

    优先级体系:
    - 太岁为君 (ROOT)，大运为臣 (ADMIN)
    - 天干冲(天战): 表层，事业/人际
    - 地支冲(地战): 底层，环境/健康/家庭 (比天干冲严重1.5-2倍)
    - 刑害不分局（无论喜忌一律负面）

    Returns:
        岁运交战产生的 EventSignal 列表
    """
    signals: list[EventSignal] = []

    from ._constants import DIZHI_LIUCHONG, DIZHI_XIANGXING, DIZHI_XIANGHAI, DIZHI_LIUHE

    has_conflict = False

    # ── 1. 天干冲（天战）──
    # 天干相克: 甲乙木克戊己土, 丙丁火克庚辛金, 戊己土克壬癸水, 庚辛金克甲乙木, 壬癸水克丙丁火
    _ke_pairs_tg = {
        ("甲", "戊"): True, ("甲", "己"): True, ("乙", "戊"): True, ("乙", "己"): True,
        ("丙", "庚"): True, ("丙", "辛"): True, ("丁", "庚"): True, ("丁", "辛"): True,
        ("戊", "壬"): True, ("戊", "癸"): True, ("己", "壬"): True, ("己", "癸"): True,
        ("庚", "甲"): True, ("庚", "乙"): True, ("辛", "甲"): True, ("辛", "乙"): True,
        ("壬", "丙"): True, ("壬", "丁"): True, ("癸", "丙"): True, ("癸", "丁"): True,
    }
    ln_tg_val = ln_stem.value if hasattr(ln_stem, 'value') else str(ln_stem)
    dn_tg_val = dn_stem.value if hasattr(dn_stem, 'value') else str(dn_stem)
    tg_clash = (ln_tg_val, dn_tg_val) in _ke_pairs_tg or (dn_tg_val, ln_tg_val) in _ke_pairs_tg

    if tg_clash:
        # 判定大运天干是否为喜用
        dn_tg_fav = dayun_mod.get("stem_is_favorable") if dayun_mod else None
        if dn_tg_fav is True:
            signals.append(EventSignal(
                category="状态",
                direction="负面",
                strength=2,
                prediction="岁运天战：流年克大运喜神→十年保护伞被太岁打破，事业/人际面临较大压力",
                triggers=[f"流年{ln_tg_val}克大运{dn_tg_val}(天战)"],
                notes=["岁运天战→权威之争/环境剧变", "大运天干为喜→保护被掀翻，压力增大"],
            ))
        elif dn_tg_fav is False:
            signals.append(EventSignal(
                category="状态",
                direction="正面",
                strength=1,
                prediction="岁运天战：流年克大运忌神→十年枷锁被太岁打破，困境出现转机",
                triggers=[f"流年{ln_tg_val}克大运{dn_tg_val}(天战)"],
                notes=["岁运天战→打破困局", "大运天干为忌→枷锁被破，转机出现"],
            ))
        else:
            signals.append(EventSignal(
                category="状态",
                direction="中性",
                strength=1,
                prediction="岁运天战：流年与大运天干相克，有权威之争或环境变化",
                triggers=[f"流年{ln_tg_val}克大运{dn_tg_val}(天战)"],
                notes=["岁运天战→注意职场人际摩擦"],
            ))
        has_conflict = True

    # ── 2. 地支冲（地战）── 比天干冲严重1.5-2倍
    dz_clash = (ln_branch, dn_branch) in DIZHI_LIUCHONG
    if dz_clash:
        dn_dz_fav = dayun_mod.get("branch_is_favorable") if dayun_mod else None
        if dn_dz_fav is True:
            signals.append(EventSignal(
                category="状态",
                direction="负面",
                strength=3,
                prediction="岁运地战：流年冲大运喜神→十年根基被太岁动摇，环境/健康/家庭面临重大变动",
                triggers=[f"流年{ln_branch.value}冲大运{dn_branch.value}(地战)"],
                notes=["岁运地战→根基动摇，程度远大于天战",
                       "大运地支为喜→十年保护地基被破，重大变动"],
            ))
        elif dn_dz_fav is False:
            signals.append(EventSignal(
                category="状态",
                direction="正面",
                strength=2,
                prediction="岁运地战：流年冲大运忌神→十年困局被太岁打破根基，旧格局瓦解迎新生",
                triggers=[f"流年{ln_branch.value}冲大运{dn_branch.value}(地战)"],
                notes=["岁运地战→打破困局根基", "大运地支为忌→地基被翻，旧环境瓦解"],
            ))
        else:
            signals.append(EventSignal(
                category="状态",
                direction="负面",
                strength=2,
                prediction="岁运地战：流年与大运地支相冲，环境/家庭有较大动荡",
                triggers=[f"流年{ln_branch.value}冲大运{dn_branch.value}(地战)"],
                notes=["岁运地战→根基动摇，注意家庭/居住环境变动"],
            ))
        has_conflict = True

    # ── 3. 岁运相刑/相害 ── 不分局，一律负面
    if not dz_clash:
        dz_xing = (ln_branch, dn_branch) in DIZHI_XIANGXING
        dz_hai = (ln_branch, dn_branch) in DIZHI_XIANGHAI
        if dz_xing:
            signals.append(EventSignal(
                category="状态",
                direction="负面",
                strength=1,
                prediction="岁运相刑：流年与大运相刑，有慢性摩擦或法律/健康隐患",
                triggers=[f"流年{ln_branch.value}刑大运{dn_branch.value}"],
                notes=["岁运相刑→慢性损耗/官非隐忧（不分局）"],
            ))
            has_conflict = True
        if dz_hai:
            signals.append(EventSignal(
                category="状态",
                direction="负面",
                strength=1,
                prediction="岁运相害：流年与大运相害，有人际暗害或健康隐患",
                triggers=[f"流年{ln_branch.value}害大运{dn_branch.value}"],
                notes=["岁运相害→暗箭难防/隐性疾病（不分局）"],
            ))
            has_conflict = True

    # ── 4. 岁运相合 ── 中性偏吉，十年力量被引导到具体事件
    if not has_conflict:
        dz_he = (ln_branch, dn_branch) in DIZHI_LIUHE
        if dz_he:
            signals.append(EventSignal(
                category="状态",
                direction="正面",
                strength=1,
                prediction="岁运相合：流年与大运地支六合，十年积累的力量在这一年集中兑现",
                triggers=[f"流年{ln_branch.value}合大运{dn_branch.value}"],
                notes=["岁运相合→力量聚焦，十年势能转化为年度事件"],
            ))

    return signals


def _extract_year_features(ln_stem, ln_branch, year_branch, day_branch,
                           day_master, gender, dn_stem, dn_branch) -> dict:
    """提取流年近失特征——信号检测函数内部计算但可能未触发规则的关键信息。

    这些信息供 LLM 做多因子综合推理。
    """
    features: dict = {}

    # 1. 流年十神
    ln_shishen = get_ten_god(day_master, ln_stem)
    features["流年十神"] = ln_shishen.value if ln_shishen else "?"

    # 2. 流年神煞
    hongluan = HONGLUAN.get(year_branch)
    tianxi = TIANXI.get(year_branch)
    taohua_dz = TAOHUA.get(year_branch)
    yima = YIMA.get(year_branch)

    if ln_branch == hongluan:
        features["红鸾"] = f"流年{ln_branch.value}=红鸾入命"
    elif hongluan:
        features["红鸾"] = f"红鸾在{hongluan.value}, 流年{ln_branch.value}"

    if ln_branch == tianxi:
        features["天喜"] = f"流年{ln_branch.value}=天喜入命"
    elif tianxi:
        features["天喜"] = f"天喜在{tianxi.value}, 流年{ln_branch.value}"
        # 检查是否合动天喜
        if _has_branch_interaction(ln_branch, tianxi, "六合"):
            features["天喜合动"] = f"流年{ln_branch.value}合天喜{tianxi.value}→天喜被引动"
        elif tianxi and _is_in_same_sanhe(ln_branch, tianxi):
            features["天喜合动"] = f"流年{ln_branch.value}与天喜{tianxi.value}三合→天喜被引动"

    if ln_branch == taohua_dz:
        features["桃花"] = f"流年{ln_branch.value}=桃花入命"

    if ln_branch == yima:
        features["驿马"] = f"流年{ln_branch.value}=驿马"

    # 3. 流年与夫妻宫(日支)的关系
    rizhi_rels = []
    if _has_branch_interaction(day_branch, ln_branch, "六合"):
        rizhi_rels.append("合夫妻宫")
    if _has_branch_interaction(day_branch, ln_branch, "六冲"):
        rizhi_rels.append("冲夫妻宫")
    if _has_branch_interaction(day_branch, ln_branch, "三合"):
        rizhi_rels.append("三合夫妻宫")
    if _has_branch_interaction(day_branch, ln_branch, "相害"):
        rizhi_rels.append("害夫妻宫")
    if rizhi_rels:
        features["夫妻宫引动"] = ", ".join(rizhi_rels)

    # 4. 配偶星
    spouse_star = Shishen.正财 if gender == "男" else Shishen.正官
    if ln_shishen == spouse_star:
        features["配偶星透干"] = f"流年{ln_stem.value}={spouse_star.value}透干(正配偶星)"

    # 5. 天干五合（流年合日主）
    he_pair = HEAVENLY_HE.get(day_master)
    if he_pair and ln_stem == he_pair:
        features["流年合日主"] = f"{ln_stem.value}合{day_master.value}→天地感应"

    # 6. 空亡
    kw = _kongwang_branches(day_master, day_branch)
    if _is_kongwang(ln_branch, kw):
        features["空亡"] = f"流年{ln_branch.value}落空亡→信号虚浮"

    # 7. 十二长生
    cs = _changsheng_status(day_master, ln_branch)
    if cs:
        features["十二长生"] = f"日主在流年{ln_branch.value}为{cs}"

    # 8. 大运与夫妻宫关系（婚嫁关键特征）
    if dn_branch:
        dn_rizhi_rels = []
        if _has_branch_interaction(dn_branch, day_branch, "六冲"):
            dn_rizhi_rels.append("大运冲夫妻宫")
        if _has_branch_interaction(dn_branch, day_branch, "六合"):
            dn_rizhi_rels.append("大运合夫妻宫")
        if dn_rizhi_rels:
            features["大运夫妻宫"] = ", ".join(dn_rizhi_rels)

    # 9. 岁运交战检测（天战+地战，v0.11.1: 补全知识）
    if dn_branch:
        suiyun_parts: list[str] = []
        # 天干相克（天战）
        _ke_pairs = {
            ("甲", "戊"), ("甲", "己"), ("乙", "戊"), ("乙", "己"),
            ("丙", "庚"), ("丙", "辛"), ("丁", "庚"), ("丁", "辛"),
            ("戊", "壬"), ("戊", "癸"), ("己", "壬"), ("己", "癸"),
            ("庚", "甲"), ("庚", "乙"), ("辛", "甲"), ("辛", "乙"),
            ("壬", "丙"), ("壬", "丁"), ("癸", "丙"), ("癸", "丁"),
        }
        ln_v = ln_stem.value if ln_stem else ""
        dn_v = dn_stem.value if dn_stem else ""
        if (ln_v, dn_v) in _ke_pairs:
            suiyun_parts.append(f"流年{ln_v}克大运{dn_v}(天战)")
        elif (dn_v, ln_v) in _ke_pairs:
            suiyun_parts.append(f"大运{dn_v}克流年{ln_v}(天战-运伐岁)")

        # 地支冲（地战）
        if _has_branch_interaction(ln_branch, dn_branch, "六冲"):
            suiyun_parts.append(f"岁运相冲(地战)")
        elif _has_branch_interaction(ln_branch, dn_branch, "六合"):
            suiyun_parts.append("岁运相合")

        if suiyun_parts:
            features["岁运关系"] = " + ".join(suiyun_parts)
            if "天战" in features["岁运关系"] and "地战" in features["岁运关系"]:
                features["岁运交战"] = (
                    "天克地冲(岁运反吟)——大运与流年天干相克、地支相冲，"
                    "是流年层面最剧烈的冲突形态。古诀'反吟伏吟泪淋淋'。"
                    "天战影响事业人际(表层)，地战动摇环境健康(底层，严重1.5-2倍)。"
                    "吉凶需看大运喜忌：冲克喜神→破财伤病官非，冲克忌神→换运转机去旧迎新。"
                )

    return features


def _annotate_taohua_clusters(results: list[AnnualScan]) -> list[AnnualScan]:
    """v0.11.1: 扫描后聚类——识别连续桃花年，标注首发年和延续年。

    逻辑：
    - 连续≥2年出现正面桃花信号 → 形成"桃花簇"
    - 簇中第一年标记为"最可能脱单/关系开始的年份"
    - 簇中后续年份标记为"关系内事件（升温/危机/里程碑），非新恋情"
    - 如果引擎已在运行时通过 relationship_state 做了标注，此处做补充校验
    """
    # 找出所有有正面桃花的年份
    positive_years: list[int] = []
    for r in results:
        taohua_events = [e for e in r.events if e.category == "桃花" and e.direction == "正面"]
        if taohua_events:
            positive_years.append(r.year)

    if len(positive_years) < 2:
        return results

    # 识别连续簇（间隔≤1年视为同一簇）
    clusters: list[list[int]] = []
    current_cluster = [positive_years[0]]
    for i in range(1, len(positive_years)):
        if positive_years[i] - positive_years[i-1] <= 1:
            current_cluster.append(positive_years[i])
        else:
            clusters.append(current_cluster)
            current_cluster = [positive_years[i]]
    clusters.append(current_cluster)

    # 为每个簇的首发年和后续年添加注记
    year_to_note: dict[int, str] = {}
    for cluster in clusters:
        if len(cluster) >= 2:
            first_year = cluster[0]
            year_to_note[first_year] = (
                f"连续{len(cluster)}年桃花簇首发年→最可能是感情开始的年份"
            )
            for y in cluster[1:]:
                year_to_note[y] = (
                    f"桃花簇第{cluster.index(y)+1}年→若已脱单则为关系内深化/升温，非新恋情；"
                    f"若仍单身则信号可能虚浮（首发年{first_year}未兑现时）"
                )

    # 将注记添加到对应年份的桃花事件中
    for r in results:
        if r.year in year_to_note:
            for e in r.events:
                if e.category == "桃花" and e.direction == "正面":
                    # 避免重复添加
                    if year_to_note[r.year] not in str(e.notes):
                        e.notes.insert(0, year_to_note[r.year])

    return results


def scan_years(
    day_master: Tiangan,
    year_branch: Dizhi,
    day_branch: Dizhi,
    month_branch: Dizhi,
    hour_branch: Dizhi,
    gender: str,
    start_age: int,
    luck_pillars: list[tuple[Tiangan, Dizhi]],
    birth_date: date,
    start_year: int,
    end_year: int,
    known_events: dict[int, str] | None = None,
    favorable: set[str] | None = None,
    personality_ctx: dict | None = None,
    life_stage_override: str = "",
    chart_pattern: str = "",
    pillars_tengan: list[Tiangan] | None = None,
    is_fei_ju: bool = False,
    tiaohou_climate: str = "中和",
    dayun_modulations: list[dict] | None = None,
    tansheng_wangke: list[dict] | None = None,
    health_profile: dict | None = None,
    chart_data: dict | None = None,
) -> list[AnnualScan]:
    """逐年扫描，返回每年所有事件信号

    known_events: {year: "relationship"/"single"} — 该年已知的感情状态
    favorable: {"正印","比肩",...} — 日主喜用十神集合，None=不判断喜忌
    is_fei_ju: 调候废局标志（v0.8.0: 废局→所有信号降1星）
    tiaohou_climate: 调候气候类型（v0.8.0: 大燥/大寒→信号额外压制）
    dayun_modulations: 大运调制结果列表（v0.8.0: 方向二—基线偏移+主题加权+岁运交战）
    tansheng_wangke: 贪生忘克结果（v0.8.0: 七杀/伤官攻击日主时若有通关→减凶）
    """
    results: list[AnnualScan] = []

    # 检测命局是否有伤官见官
    has_natal_shangguan = False
    if pillars_tengan:
        natal_stems_shishen = [get_ten_god(day_master, s) for s in pillars_tengan if s != day_master]
        has_shang = any(ss and ss.value == "伤官" for ss in natal_stems_shishen)
        has_guan = any(ss and ss.value in ("正官", "偏官") for ss in natal_stems_shishen)
        has_natal_shangguan = has_shang and has_guan

    # 将 known_events 转换为按年存储的"进入该年时是否恋爱中"
    known_rel: dict[int, bool] = {}
    if known_events:
        for y, status in known_events.items():
            known_rel[int(y)] = (status == "relationship")
    prev_year_rel = False
    relationship_state = "single"  # v0.11.1: 跨年关系状态机 single/dating/married

    for year in range(start_year, end_year + 1):
        ln_tg, ln_dz = compute_liunian_pillar(year)

        # 确定当前大运
        age = year - birth_date.year
        dayun_idx = (age - start_age) // 10
        dayun_idx = max(0, min(dayun_idx, len(luck_pillars) - 1))
        dn_tg, dn_dz = luck_pillars[dayun_idx] if luck_pillars else (None, None)

        # 流年干支分论: 权重分配
        sb_rel, sb_sw, sb_bw = classify_sb_relation(ln_tg, ln_dz)

        # 大运重地支/流年重天干: 权重说明
        if dn_dz:
            dn_wx = dn_dz.wuxing.value
            dn_weight_note = (
                f"大运重地支（60%），{dn_dz.value}为{dn_wx}，定十年基调；"
                f"流年{ln_tg.value}为主象，当年主题看天干"
            )
        else:
            dn_weight_note = "大运未定，流年干支并重"

        # 已知事件状态：前一年是否恋爱中（校准数据按年存储的是"该年状态"）
        if (year - 1) in known_rel:
            prev_year_rel = known_rel[year - 1]

        # 检测七类事件
        events: list[EventSignal] = []
        events.extend(detect_taohua_signals(
            ln_tg, ln_dz, year_branch, day_branch, day_master, gender,
            dn_tg, dn_dz, prev_year_rel, relationship_state, favorable,
            (year_branch, month_branch, day_branch, hour_branch),
        ))
        events.extend(detect_xuesheng_signals(
            ln_tg, ln_dz, day_branch, day_master, year_branch, month_branch, hour_branch, favorable,
        ))
        events.extend(detect_hunjia_signals(
            ln_tg, ln_dz, day_branch, day_master, year_branch, gender, favorable, dn_dz, age,
        ))
        events.extend(detect_shiye_signals(
            ln_tg, ln_dz, day_master, year_branch, month_branch, day_branch,
            hour_branch, dn_tg, dn_dz, favorable,
        ))
        events.extend(detect_caiyun_signals(
            ln_tg, ln_dz, day_master, year_branch, day_branch, favorable,
        ))
        events.extend(detect_jiankang_signals(
            ln_tg, ln_dz, day_branch, day_master, year_branch, dn_tg, dn_dz, favorable,
            (year_branch, month_branch, day_branch, hour_branch),
            health_profile=health_profile,
            first_year=(year == start_year),
        ))
        events.extend(detect_banqian_signals(
            ln_dz, year_branch, day_branch, month_branch, hour_branch, dn_dz,
            dn_tg, ln_tg, day_master, favorable,
        ))
        events.extend(detect_zhuangtai_signals(
            ln_tg, ln_dz, day_master, day_branch, dn_tg, dn_dz, favorable,
        ))
        events.extend(detect_renji_signals(
            ln_tg, ln_dz, year_branch, month_branch, day_branch, hour_branch,
            day_master,
            (year_branch, month_branch, day_branch, hour_branch),
            favorable,
        ))
        events.extend(detect_guanfei_signals(
            ln_tg, ln_dz, day_master, day_branch,
            year_branch, month_branch, hour_branch,
            dn_tg, dn_dz,
            natal_shang_guan=has_natal_shangguan,
            pillars_tengan=pillars_tengan,
        ))

        # 流年十神权威出处
        ln_shishen_name = get_ten_god(day_master, ln_tg)
        ln_shishen_val = ln_shishen_name.value if ln_shishen_name else None
        if ln_shishen_val:
            apply_shishen_year_notes(events, ln_shishen_val)

        # 财星流年联动：同时有桃花+财运信号时，加欲望消费提示
        has_taohua = any(e.category == "桃花" for e in events)
        has_caiyun = any(e.category == "财运" for e in events)
        is_caixing_year = ln_shishen_val in ("正财", "偏财")

        if is_caixing_year:
            for e in events:
                if e.category == "桃花":
                    e.notes.append(f"{ln_shishen_val}年→情感欲望增强，对异性的关注度上升")
                if e.category == "财运":
                    e.notes.append(f"{ln_shishen_val}年→消费欲增加，可能为感情/社交花钱")
            if has_taohua and has_caiyun:
                for e in events:
                    if e.category == "桃花" or e.category == "财运":
                        e.notes.append(f"{ln_shishen_val}年桃花+财运同现→钱和情的欲望同步放大，注意为感情消费")

        # 注入性格联动备注
        if personality_ctx:
            apply_personality_notes(events, personality_ctx)

        # 人生阶段适配：学生时期修正事业/财运措辞
        if life_stage_override:
            stage_for_year = life_stage_override
        else:
            # 智能判断：年龄 + 大运十神 + 格局 + 升学信号
            # 计算大运天干的十神（相对于日主），而非传天干本身
            dn_shishen = get_ten_god(day_master, dn_tg) if dn_tg else None
            dn_tg_name = dn_shishen.value if dn_shishen else None
            has_xs = any(e.category == "升学" for e in events)
            stage_for_year = _life_stage(
                age, dayun_ten_god=dn_tg_name,
                pattern=chart_pattern, has_xuesheng_signal=has_xs
            )

        for e in events:
            e.prediction = _make_prediction(
                e.category, e.direction, e.strength,
                e.triggers, e.notes, age=age,
                life_stage=stage_for_year,
            )

        # 人生阶段适配：非学生阶段重命名事件类别（在 prediction 生成之后）
        for e in events:
            if stage_for_year in ("职场", "晚年") and e.category == "升学":
                e.category = "进修"
            elif stage_for_year in ("中学", "大学", "深造") and e.category == "事业":
                e.category = "学业"

        # ── 事件矛盾检查 + 融合 ──
        _check_event_conflicts(events, ln_dz, day_branch, day_master,
                               year_branch, month_branch, hour_branch)

        # ── 婚嫁↔桃花交叉引用（v0.9.1: 两者共享触发空间，一侧≥2★时补足另一侧）──
        _cross_ref_hunjia_taohua(events, age)

        # ── 同柱隔离带调制（v0.8.0: 盖头/截脚→流年干支内部消耗，信号打折）──
        # 截脚破坏权重 > 盖头（《滴天髓》：截脚者地克天，根基不稳）
        # 仅降低最高烈度信号（≥3★），中等信号（2★）不受影响
        if sb_rel == "截脚":
            for e in events:
                if e.strength >= 3:
                    e.strength -= 1
                    e.notes.append(f"流年{sb_rel}({ln_tg.value}{ln_dz.value})→地支反克天干，内力消耗，高烈度事件打折")
        elif sb_rel == "盖头":
            for e in events:
                if e.strength >= 3:
                    e.strength -= 1
                    e.notes.append(f"流年{sb_rel}({ln_tg.value}{ln_dz.value})→天干压制地支，能量内耗，高烈度事件概率降低")

        # ── 调候废局降权（v0.8.0: 仅压制最高烈度，中等信号保留）──
        # 废局 + 极端气候合并处理：最多降1星，不重复
        tiaohou_severe = is_fei_ju and tiaohou_climate in ("大燥", "大寒")
        if is_fei_ju:
            for e in events:
                if e.strength >= 3:
                    e.strength -= 1
                    e.notes.append("⚠ 命局为调候废局：格局难发挥，高烈度事件打折（陆致极「失去调候为废局」）")
                    if tiaohou_severe:
                        e.notes.append(f"气候{tiaohou_climate}→环境极端，事件发挥进一步受限")
                elif e.strength == 2:
                    e.notes.append("调候废局：信号可信度打折扣，实际体验可能低于预期")
                elif e.strength == 1:
                    e.notes.append("调候废局：弱信号可信度降低")

        # ── 大运调制（v0.8.0: 方向二—基线偏移 + 主题加权）──
        current_dayun_mod = None
        if dayun_modulations:
            for mod in dayun_modulations:
                age_range = mod.get("age_range", "")
                if age_range:
                    parts = age_range.replace("岁", "").split("-")
                    if len(parts) == 2:
                        try:
                            rng_start = int(parts[0])
                            rng_end = int(parts[1])
                            if rng_start <= age <= rng_end:
                                current_dayun_mod = mod
                                break
                        except ValueError:
                            pass

        if current_dayun_mod:
            baseline = current_dayun_mod.get("baseline_offset", 0)
            theme = current_dayun_mod.get("theme", "")
            theme_w = current_dayun_mod.get("theme_weight", 1.0)

            # 基线偏移: 吉运+1星, 凶运-1星（仅影响≥2★的信号）
            # v0.9.1: 桃花/婚嫁免于凶运正面打压——方向判断常有歧义，不因大运基调降级
            if baseline != 0:
                for e in events:
                    if baseline > 0 and e.direction == "正面" and e.strength >= 2:
                        e.strength = min(3, e.strength + 1)
                        e.notes.append(f"大运吉调：十年基调偏吉，正面事件放大")
                    elif baseline < 0 and e.direction == "负面" and e.strength >= 2:
                        e.strength = min(3, e.strength + 1)
                        e.notes.append(f"大运凶调：十年基调偏凶，负面事件放大")
                    elif baseline < 0 and e.direction == "正面" and e.strength >= 2:
                        if e.category in ("桃花", "婚嫁"):
                            e.notes.append("大运凶调：婚恋事件在凶运中需谨慎辨别，但机会本身仍存在")
                        else:
                            e.strength = max(1, e.strength - 1)
                            e.notes.append("大运凶调：不幸之运，吉事打折扣")

            # 主题加权: 大运主题与流年事件一致时加权
            if theme and theme_w != 1.0:
                theme_event_map = {
                    "财运": "财运",
                    "官运": "事业",
                    "印运": "升学",
                    "食伤运": "事业",
                    "比劫运": "人际",
                }
                boosted_category = theme_event_map.get(theme, "")
                for e in events:
                    if boosted_category and e.category == boosted_category:
                        if theme_w > 1.0 and e.strength >= 2:
                            e.strength = min(3, e.strength + 1)
                            e.notes.append(f"大运主题'{theme}'共振→{e.category}信号增强")
                        elif theme_w < 1.0 and e.strength >= 2:
                            e.strength = max(1, e.strength - 1)
                            e.notes.append(f"大运主题偏移→{e.category}非此运重点，信号减弱")

        # ── 岁运交战处理器（v0.8.0: P6—流年vs大运优先级拦截）──
        if dn_tg and dn_dz:
            sui_yun_signals = _process_suiyun_clash(ln_tg, ln_dz, dn_tg, dn_dz,
                                                     day_master, current_dayun_mod)
            if sui_yun_signals:
                events.extend(sui_yun_signals)
                # 判断交战等级
                is_dizhan = any("地战" in str(s.triggers) for s in sui_yun_signals)
                is_tianzhan = any("天战" in str(s.triggers) for s in sui_yun_signals)
                is_ke_xishen = any("喜神" in str(s.triggers) for s in sui_yun_signals)
                clash_level = "地战" if is_dizhan else ("天战" if is_tianzhan else "刑害")

                # v0.11.1: 岁运交战分方向处理——动荡加剧≠信号变弱
                # 吉事打折(动荡中好事难落实)，凶事加码(动荡中坏事更易发生)
                is_dizhan = any("地战" in str(s.triggers) for s in sui_yun_signals)
                for e in events:
                    if e.category == "健康":
                        continue
                    if e.direction == "正面":
                        if is_dizhan:
                            e.notes.append("⚠ 岁运地战→根基动摇，好事打折，宜守不宜攻")
                        else:
                            e.notes.append("⚠ 岁运交战→吉事可信度下降，好事可能落空或附带代价")
                    elif e.direction == "负面":
                        if is_dizhan:
                            e.notes.append("⚠ 岁运地战→根基动摇，坏事加剧，重大决策暂缓")
                        else:
                            e.notes.append("⚠ 岁运交战→动荡加剧，负面事件更易坐实，不可轻视")
                    else:
                        e.notes.append("⚠ 岁运交战→波动大、变数多，中性事件偏负面方向倾斜")

        # ── LLM 推理层（v0.9.1: hybrid模式—提供流年近失特征）──
        if chart_data:
            try:
                from .llm_review import review_year_if_needed
                # 提取流年近失特征（信号检测函数内部计算但未触发规则的关键信息）
                yr_features = _extract_year_features(
                    ln_tg, ln_dz, year_branch, day_branch, day_master,
                    gender, dn_tg, dn_dz,
                )
                # v0.11.1: 提取性格画像供LLM综合判断
                personality_text = chart_data.get("personality", {}).get("profile", "")
                llm_events = review_year_if_needed(
                    chart_data=chart_data,
                    year=year,
                    age=age,
                    liunian_stem=ln_tg.value,
                    liunian_branch=ln_dz.value,
                    dayun_stem=dn_tg.value if dn_tg else None,
                    dayun_branch=dn_dz.value if dn_dz else None,
                    rule_events=events,
                    dayun_mod=current_dayun_mod,
                    tansheng_wangke=tansheng_wangke,
                    year_features=yr_features,
                    personality_text=personality_text,
                )
                for llm_evt in llm_events:
                    events.append(EventSignal(
                        category=llm_evt.category,
                        direction=llm_evt.direction,
                        strength=llm_evt.strength,
                        prediction=llm_evt.prediction,
                        triggers=llm_evt.triggers,
                        notes=[f"🤖 LLM综合推理 (置信度{llm_evt.confidence:.0%}): {llm_evt.reasoning}"],
                    ))
            except Exception:
                pass  # LLM review failure is non-blocking

        # ── 贪生忘克化解（v0.8.0: P7—七杀/伤官攻击日主若有通关→减凶）──
        if tansheng_wangke:
            dm_protected = any(
                gg.get("cancelled_ke") and
                (day_master and day_master.value == gg["cancelled_ke"][1])
                for gg in tansheng_wangke
            )
            if dm_protected:
                for e in events:
                    # 健康: 七杀攻身信号降级
                    if e.category == "健康":
                        sha_triggers = [t for t in e.triggers if "七杀" in t or "偏官" in t]
                        if sha_triggers:
                            if e.strength >= 2:
                                e.strength -= 1
                                e.notes.append("贪生忘克化解：杀印相生→压力转化动力，七杀凶性大减")
                    # 事业: 官杀混杂信号降级
                    if e.category == "事业":
                        guansha_triggers = [t for t in e.triggers if "官杀混杂" in t]
                        if guansha_triggers:
                            if e.strength >= 2:
                                e.strength -= 1
                                e.notes.append("贪生忘克化解：印星通关→官杀混杂压力可控")
                    # 女命伤官见官 → 有印制伤则减凶
                    if e.category in ("桃花", "婚嫁") and gender == "女":
                        shang_triggers = [t for t in e.triggers if "伤官" in t]
                        if shang_triggers:
                            e.notes.append("贪生忘克提示：若有印星通关，伤官克官之凶可减")

        results.append(AnnualScan(
            year=year,
            liunian_stem=ln_tg,
            liunian_branch=ln_dz,
            dayun_stem=dn_tg,
            dayun_branch=dn_dz,
            events=events,
            age=age,
            sb_relation=sb_rel,
            stem_weight=sb_sw,
            branch_weight=sb_bw,
            dayun_weight_note=dn_weight_note,
        ))

        # ── v0.11.1: 跨年关系状态机更新 ──
        taohua_sigs = [e for e in events if e.category == "桃花"]
        hunjia_sigs = [e for e in events if e.category == "婚嫁"]
        prev_year_rel = any(e.strength >= 2 for e in taohua_sigs)

        # 状态转换
        if relationship_state == "single":
            # 单身→恋爱：桃花≥3★正面 或 婚嫁信号
            has_strong_positive = any(
                e.strength >= 3 and e.direction == "正面"
                for e in taohua_sigs
            )
            has_hunjia = any(e.strength >= 2 for e in hunjia_sigs)
            if has_strong_positive or has_hunjia:
                relationship_state = "dating"
        elif relationship_state == "dating":
            # 恋爱→已婚：婚嫁信号≥3★
            has_strong_hunjia = any(e.strength >= 3 for e in hunjia_sigs)
            if has_strong_hunjia:
                relationship_state = "married"
            # 恋爱→分手：负面桃花≥2★ 且 有冲夫妻宫/劫财/伤官
            has_breakup = any(
                e.direction == "负面" and e.strength >= 2 and
                any("冲夫妻宫" in str(t) or "劫财" in str(t) or "伤官克官" in str(t)
                    for t in e.triggers)
                for e in taohua_sigs
            )
            if has_breakup:
                relationship_state = "single"
        # married→single: 婚嫁负面信号（离婚）
        elif relationship_state == "married":
            has_divorce = any(
                e.direction == "负面" and e.strength >= 3 and
                any("冲夫妻宫" in str(t) or "伤官" in str(t) for t in e.triggers)
                for e in hunjia_sigs + taohua_sigs
            )
            if has_divorce:
                relationship_state = "single"

    # ── v0.11.1: 扫描后聚类处理—标注连续桃花年的"首发年" ──
    results = _annotate_taohua_clusters(results)

    return results
