"""
流年逐年扫描 — liunian 子包

公共接口：
    from bazi_engine.liunian import scan_years, AnnualScan, ...
"""
from .battle import _process_suiyun_clash
from .calibration import (
    SHISHEN_YEAR_SOURCES,
    _check_event_conflicts,
    _cross_ref_hunjia_taohua,
    _merge_same_category_events,
    apply_personality_notes,
    apply_shishen_year_notes,
)
from .events import (
    detect_banqian_signals,
    detect_caiyun_signals,
    detect_guanfei_signals,
    detect_hunjia_signals,
    detect_jiankang_signals,
    detect_renji_signals,
    detect_shiye_signals,
    detect_taohua_signals,
    detect_xuesheng_signals,
    detect_zhuangtai_signals,
)
from .features import _extract_year_features
from .llm_bridge import (
    _execute_llm_reviews_parallel,
    _execute_llm_reviews_streaming,
)
from .scanner import (
    _annotate_taohua_clusters,
    build_personality_context,
    scan_years,
)
from .signal import AnnualScan, EventSignal, EvidenceItem, Factor, ScoreAccumulator
from .utils import (
    _CAIKU_BY_DAY_WUXING,
    _CAIKU_MAP,
    HEAVENLY_HE,
    _changsheng_status,
    _fav_note,
    _has_branch_interaction,
    _has_root,
    _has_sanhe_with_dizhi,
    _has_tiangan_wuhe,
    _is_in_same_sanhe,
    _is_ke_wx,
    _is_kongwang,
    _kongwang_branches,
    _life_stage,
    _make_prediction,
    _wealth_magnitude,
    classify_sb_relation,
    compute_liunian_pillar,
    get_caiku_branch,
    is_favorable,
    is_harmful,
)

__all__ = [
    'HEAVENLY_HE',
    'SHISHEN_YEAR_SOURCES',
    '_CAIKU_BY_DAY_WUXING',
    '_CAIKU_MAP',
    'AnnualScan',
    'EventSignal',
    'EvidenceItem',
    'Factor',
    'ScoreAccumulator',
    '_annotate_taohua_clusters',
    '_changsheng_status',
    '_check_event_conflicts',
    '_cross_ref_hunjia_taohua',
    '_execute_llm_reviews_parallel',
    '_execute_llm_reviews_streaming',
    '_extract_year_features',
    '_fav_note',
    '_has_branch_interaction',
    '_has_root',
    '_has_sanhe_with_dizhi',
    '_has_tiangan_wuhe',
    '_is_in_same_sanhe',
    '_is_ke_wx',
    '_is_kongwang',
    '_kongwang_branches',
    '_life_stage',
    '_make_prediction',
    '_merge_same_category_events',
    '_process_suiyun_clash',
    '_wealth_magnitude',
    'apply_personality_notes',
    'apply_shishen_year_notes',
    'build_personality_context',
    'classify_sb_relation',
    'compute_liunian_pillar',
    'detect_banqian_signals',
    'detect_caiyun_signals',
    'detect_guanfei_signals',
    'detect_hunjia_signals',
    'detect_jiankang_signals',
    'detect_renji_signals',
    'detect_shiye_signals',
    'detect_taohua_signals',
    'detect_xuesheng_signals',
    'detect_zhuangtai_signals',
    'get_caiku_branch',
    'is_favorable',
    'is_harmful',
    'scan_years',
]
