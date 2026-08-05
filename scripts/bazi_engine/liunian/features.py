"""流年近失特征提取 — 供 LLM 多因子综合推理。"""
from .._constants import DIZHI_CANGGAN, HONGLUAN, TAOHUA, TIANXI, YIMA
from ..enums import Shishen
from ..ten_gods import get_ten_god
from .utils import (
    HEAVENLY_HE,
    _changsheng_status,
    _has_branch_interaction,
    _is_in_same_sanhe,
    _is_kongwang,
    _kongwang_branches,
)


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

    if ln_branch == tianxi:
        features["天喜"] = f"流年{ln_branch.value}=天喜入命"
    elif tianxi:
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
        rizhi_rels.append("流年与日支六合（结构参考）")
    if _has_branch_interaction(day_branch, ln_branch, "六冲"):
        rizhi_rels.append("流年与日支六冲（结构参考）")
    if _has_branch_interaction(day_branch, ln_branch, "三合"):
        rizhi_rels.append("流年与日支三合（结构参考）")
    if _has_branch_interaction(day_branch, ln_branch, "相害"):
        rizhi_rels.append("流年与日支相害（结构参考）")
    if rizhi_rels:
        features["夫妻宫引动"] = ", ".join(rizhi_rels)

    # 4. 配偶星
    spouse_star = Shishen.正财 if gender == "男" else Shishen.正官
    second_star = Shishen.偏财 if gender == "男" else Shishen.偏官
    if ln_shishen == spouse_star:
        features["配偶星透干"] = f"流年{ln_stem.value}={spouse_star.value}透干(正配偶星)"
    elif ln_shishen == second_star:
        features["关系星透干"] = f"流年{ln_stem.value}={second_star.value}透干(次级关系星)"
    hidden_stars = [
        get_ten_god(day_master, hidden.stem)
        for hidden in DIZHI_CANGGAN.get(ln_branch, [])
    ]
    hidden_names = [
        star.value for star in hidden_stars
        if star in (spouse_star, second_star)
    ]
    if hidden_names:
        features["关系星藏干"] = (
            f"流年{ln_branch.value}藏{'/'.join(dict.fromkeys(hidden_names))}"
            "（区分正配偶星与次级关系星）"
        )

    # 5. 天干五合（流年合日主）
    he_pair = HEAVENLY_HE.get(day_master)
    if he_pair and ln_stem == he_pair:
        features["流年合日主"] = f"{ln_stem.value}合{day_master.value}→天地感应"

    # 6. 空亡
    kw = _kongwang_branches(day_master, day_branch)
    if _is_kongwang(ln_branch, kw):
        features["空亡"] = f"流年{ln_branch.value}落旬空（结构参考，影响需结合合冲旺衰）"

    # 7. 十二长生
    cs = _changsheng_status(day_master, ln_branch)
    if cs:
        features["十二长生"] = f"日主在流年{ln_branch.value}为{cs}"

    # 8. 大运与夫妻宫关系（婚嫁关键特征）
    if dn_branch:
        dn_rizhi_rels = []
        if _has_branch_interaction(dn_branch, day_branch, "六冲"):
            dn_rizhi_rels.append("大运与日支六冲（结构参考）")
        if _has_branch_interaction(dn_branch, day_branch, "六合"):
            dn_rizhi_rels.append("大运与日支六合（结构参考）")
        if dn_rizhi_rels:
            features["大运夫妻宫"] = ", ".join(dn_rizhi_rels)

    # 9. 岁运交战检测（天战+地战，v0.11.1: 补全知识）
    if dn_branch:
        suiyun_parts: list[str] = []
        # 天干相克（天战）
        from ..ten_gods import TIANGAN_KE_PAIRS
        ln_v = ln_stem.value if ln_stem else ""
        dn_v = dn_stem.value if dn_stem else ""
        if (ln_v, dn_v) in TIANGAN_KE_PAIRS:
            suiyun_parts.append(f"流年{ln_v}克大运{dn_v}(天战)")
        elif (dn_v, ln_v) in TIANGAN_KE_PAIRS:
            suiyun_parts.append(f"大运{dn_v}克流年{ln_v}(天战-运伐岁)")

        # 地支冲（地战）
        if _has_branch_interaction(ln_branch, dn_branch, "六冲"):
            suiyun_parts.append("岁运相冲(地战)")
        elif _has_branch_interaction(ln_branch, dn_branch, "六合"):
            suiyun_parts.append("岁运相合")

        if suiyun_parts:
            features["岁运关系"] = " + ".join(suiyun_parts)
            if "天战" in features["岁运关系"] and "地战" in features["岁运关系"]:
                features["岁运交战"] = (
                    "大运与流年同时存在天干相克、地支相冲。该字段只记录结构关系，"
                    "不直接推断事业、财务、健康、法律或家庭事件，具体方向以规则层信号为准。"
                )

    return features

