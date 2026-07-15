"""Gender-specific rules shared across chart and interpretation layers."""

from .enums import Shishen, Tiangan


def is_forward_luck(year_stem: Tiangan, gender: str) -> bool:
    """Return True for 阳男阴女顺排, False for 阴男阳女逆排."""
    is_yang_year = year_stem.yinyang == "阳"
    return (is_yang_year and gender == "男") or (not is_yang_year and gender == "女")


def get_kinship_map(gender: str) -> dict:
    """Return the core ten-god kinship mapping for gendered readings."""
    if gender == "女":
        return {
            "spouse": {"label": "夫星", "stars": [Shishen.正官.value, Shishen.偏官.value]},
            "child": {"label": "子女星", "stars": [Shishen.食神.value, Shishen.伤官.value]},
            "mother_in_law": {"label": "婆婆", "stars": [Shishen.偏财.value]},
        }
    return {
        "spouse": {"label": "妻星", "stars": [Shishen.正财.value, Shishen.偏财.value]},
        "child": {"label": "子女星", "stars": [Shishen.正官.value, Shishen.偏官.value]},
        "father_in_law": {"label": "岳父", "stars": [Shishen.偏财.value, Shishen.正财.value]},
        "mother_in_law": {"label": "岳母", "stars": [Shishen.偏印.value, Shishen.正印.value]},
    }


def spouse_star_names(gender: str) -> tuple[str, str, str]:
    """Return spouse label, primary star, and secondary star names."""
    mapping = get_kinship_map(gender)["spouse"]
    return mapping["label"], mapping["stars"][0], mapping["stars"][1]
