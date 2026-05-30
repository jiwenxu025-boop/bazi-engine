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
from .signal import AnnualScan, EventSignal, Factor, ScoreAccumulator
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
    'Factor', 'ScoreAccumulator', 'EventSignal', 'AnnualScan',
    'compute_liunian_pillar', 'classify_sb_relation',
    'is_favorable', 'is_harmful', '_fav_note',
    'get_caiku_branch', '_has_branch_interaction',
    '_has_sanhe_with_dizhi', '_has_tiangan_wuhe',
    '_changsheng_status', '_is_in_same_sanhe',
    '_life_stage', '_make_prediction',
    '_kongwang_branches', '_is_kongwang',
    '_has_root', '_is_ke_wx', '_wealth_magnitude',
    'HEAVENLY_HE', '_CAIKU_MAP', '_CAIKU_BY_DAY_WUXING',
    'detect_taohua_signals', 'detect_xuesheng_signals',
    'detect_hunjia_signals', 'detect_shiye_signals',
    'detect_caiyun_signals', 'detect_jiankang_signals',
    'detect_banqian_signals', 'detect_zhuangtai_signals',
    'detect_renji_signals', 'detect_guanfei_signals',
    'build_personality_context',
    'SHISHEN_YEAR_SOURCES',
    'apply_shishen_year_notes', 'apply_personality_notes',
    '_merge_same_category_events', '_check_event_conflicts',
    '_cross_ref_hunjia_taohua',
    '_process_suiyun_clash', '_extract_year_features',
    '_execute_llm_reviews_streaming', '_execute_llm_reviews_parallel',
    '_annotate_taohua_clusters',
    'scan_years',
]
