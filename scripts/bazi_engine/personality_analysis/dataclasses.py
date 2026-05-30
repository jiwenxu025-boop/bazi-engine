"""数据类：PersonalityResult, FamilyResult"""
from dataclasses import dataclass, field


class PersonalityResult:
    """性格分析结果"""
    day_master_core: str = ""           # 日干核心性格
    strength_label: str = ""            # 身强弱描述
    dominant_ten_god: str = ""          # 最旺十神及其影响
    pattern_influence: str = ""         # 格局对性格的影响
    special_combos: list[str] = field(default_factory=list)  # 特殊组合
    traits: dict = field(default_factory=dict)  # {领域: 简短描述}（前端回退用）
    trait_signals: dict = field(default_factory=dict)  # {领域: {信号名: 数值}}（LLM融合用）
    profile: str = ""                   # 综合性格画像
    stress_profile: dict | None = None  # 抗压画像 (v0.10.0: 三引擎)
    bingyao_combos: list[dict] = field(default_factory=list)  # 病药组合 (v0.11.0)
    weighted_shishen: dict = field(default_factory=dict)      # 加权十神报告 (v0.11.0)
    sub_traits: list[dict] = field(default_factory=list)      # 十神子特质 (v0.15.0)
    combo_traits: list[dict] = field(default_factory=list)    # 十神组合特质 (v0.15.0)
    dizhi_traits: list[dict] = field(default_factory=list)    # 地支关系→性格 (v0.15.0)

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

class FamilyResult:
    """家境分析结果"""
    level: str = ""                     # A / B / C / D / E
    level_label: str = ""               # 家境等级中文标签
    surface: str = ""                   # 表面现象
    reality: str = ""                   # 实际情况
    family_type: str = ""               # 家庭出身类型（书香/商贾/官宦/寒门/小康）
    father: str = ""                    # 父亲状况
    mother: str = ""                    # 母亲状况
    parents_relation: str = ""          # 父母关系/祖辈关系
    parents_health: str = ""            # 父母健康寿元提示
    childhood: str = ""                 # 童年环境
    inheritance: str = ""               # 继承情况
    ancestral: str = ""                 # 祖辈状况
    profile: str = ""                   # 综合家境描述

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

