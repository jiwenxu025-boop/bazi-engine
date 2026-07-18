"""Data classes for liunian signal system."""
from dataclasses import dataclass, field

from ..enums import Dizhi, Tiangan


@dataclass
class Factor:
    """打分因子：每个触发条件贡献一个分数"""
    score: int
    trigger: str
    note: str = ""

class ScoreAccumulator:
    """打分累加器：收集因子 → 综合判断信号"""
    def __init__(self, favorable_set: set[str] | None = None):
        self.factors: list[Factor] = []
        self._min_strength: int = 0
        self._favorable: set[str] | None = favorable_set
        self._current_shishen: str = ""
        self._current_fav: bool | None = None
        self._modulate_score: bool = True

    def add(self, score: int, trigger: str, note: str = "", fixed: bool = False):
        """添加因子。fixed=True 的因子不被喜忌调分（伤官/冲刑等方向固定型）。"""
        shishen = getattr(self, '_current_shishen', '')
        fav = getattr(self, '_current_fav', None)
        modulate_score = getattr(self, '_modulate_score', True)
        if shishen and fav is False:
            trigger += " [忌]"
            if modulate_score and not fixed:
                score -= 1
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
        if base >= 4:
            return 3
        if base >= 2:
            return 2
        return 1

    @property
    def direction(self) -> str:
        t = self.total
        if t >= 1:
            return "正面"
        if t <= -1:
            return "负面"
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
    category: str
    direction: str        # "正面" | "负面" | "中性"
    strength: int         # 1-3 (★ ~ ★★★)
    prediction: str = ""  # 自然语言预测
    triggers: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    calibration_refs: list[str] = field(default_factory=list)
    personality_note: str = ""  # 性格联动备注
    magnitude: str = ""         # 财务信号强度 "弱"/"中"/"较强"，不表示金额或损失规模
    source: str = "rule"        # v0.16.0: 信号来源 "rule"|"llm"
    review_status: str = ""     # AI审阅状态："有信号"|"无明显信号"|"未完成"

    def to_dict(self) -> dict:
        d = {
            "category": self.category,
            "direction": self.direction,
            "strength": self.strength,
            "prediction": self.prediction,
            "triggers": self.triggers,
            "notes": self.notes,
            "calibration_refs": self.calibration_refs,
            "personality_note": self.personality_note,
            "source": self.source,
        }
        if self.magnitude:
            d["magnitude"] = self.magnitude
        if self.review_status:
            d["review_status"] = self.review_status
        return d

@dataclass
class AnnualScan:
    year: int
    liunian_stem: Tiangan
    liunian_branch: Dizhi
    dayun_stem: Tiangan | None = None
    dayun_branch: Dizhi | None = None
    events: list[EventSignal] = field(default_factory=list)
    ai_reviews: list[EventSignal] = field(default_factory=list)
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
            "ai_reviews": [review.to_dict() for review in self.ai_reviews],
        }

