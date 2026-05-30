"""八字性格分析与家境分析引擎

公共接口：
    from bazi_engine.personality_analysis import analyze_personality, ...
"""
from .dataclasses import PersonalityResult, FamilyResult
from .main import analyze_personality, _apply_reality_check
from .family import analyze_family
from .builder import build_pillars_data_for_analysis
from .weighting import get_weighted_shishen_report
from .bingyao import detect_bingyao_combos

__all__ = [
    'PersonalityResult', 'FamilyResult',
    'analyze_personality', 'analyze_family',
    'build_pillars_data_for_analysis',
    'get_weighted_shishen_report',
    'detect_bingyao_combos',
]
