"""Event detection modules."""
from .banqian import detect_banqian_signals
from .caiyun import detect_caiyun_signals
from .guanfei import detect_guanfei_signals
from .hunjia import detect_hunjia_signals
from .jiankang import detect_jiankang_signals
from .renji import detect_renji_signals
from .shiye import detect_shiye_signals
from .taohua import detect_taohua_signals
from .xuesheng import detect_xuesheng_signals
from .zhuangtai import detect_zhuangtai_signals

__all__ = [
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
]
