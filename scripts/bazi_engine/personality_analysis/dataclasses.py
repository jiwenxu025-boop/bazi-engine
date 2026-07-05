"""数据类：PersonalityResult, FamilyResult"""
from dataclasses import dataclass, field


@dataclass
class PersonalityResult:
    """性格分析结果"""
    day_master_core: dict = field(default_factory=dict)
    strength_label: str = ""
    dominant_ten_god: str = ""
    pattern_influence: str = ""
    special_combos: list[str] = field(default_factory=list)
    traits: dict = field(default_factory=dict)
    trait_signals: dict = field(default_factory=dict)
    profile: str = ""
    stress_profile: dict | None = None
    bingyao_combos: list[dict] = field(default_factory=list)
    weighted_shishen: dict = field(default_factory=dict)
    sub_traits: list[dict] = field(default_factory=list)
    combo_traits: list[dict] = field(default_factory=list)
    dizhi_traits: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "day_master_core": self.day_master_core,
            "strength_label": self.strength_label,
            "dominant_ten_god": self.dominant_ten_god,
            "pattern_influence": self.pattern_influence,
            "special_combos": self.special_combos,
            "traits": self.traits,
            "trait_signals": self.trait_signals,
            "profile": self.profile,
            "stress_profile": self.stress_profile,
            "bingyao_combos": self.bingyao_combos,
            "weighted_shishen": self.weighted_shishen,
            "sub_traits": self.sub_traits,
            "combo_traits": self.combo_traits,
            "dizhi_traits": self.dizhi_traits,
        }


@dataclass
class FamilyResult:
    """家境分析结果"""
    level: str = ""
    level_label: str = ""
    surface: str = ""
    reality: str = ""
    family_type: str = ""
    father: str = ""
    mother: str = ""
    parents_relation: str = ""
    parents_health: str = ""
    childhood: str = ""
    inheritance: str = ""
    ancestral: str = ""
    profile: str = ""

    def to_dict(self) -> dict:
        return {
            "level": self.level,
            "level_label": self.level_label,
            "surface": self.surface,
            "reality": self.reality,
            "family_type": self.family_type,
            "father": self.father,
            "mother": self.mother,
            "parents_relation": self.parents_relation,
            "parents_health": self.parents_health,
            "childhood": self.childhood,
            "inheritance": self.inheritance,
            "ancestral": self.ancestral,
            "profile": self.profile,
        }
