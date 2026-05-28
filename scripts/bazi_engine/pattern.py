"""格局判定 + 成格/破格验证

来源:
- 骨架: 《子平真诠·论用神》——善神(财官印食)顺用,凶神(杀伤枭刃)逆用
- 效率: 段建业盲派——"制得干净"才成格,制不尽则降格
- 多视角: 陆致极——格局+强弱+调候综合判定
- 调候: 梁湘润+《穷通宝鉴》——废局下格局先天打折
"""

from .enums import Tiangan, Dizhi
from ._constants import DIZHI_CANGGAN
from .enums import TIANGAN_LU, TIANGAN_YANGREN
from .ten_gods import get_ten_god


def determine_pattern(month_branch: Dizhi, all_stems: list[Tiangan],
                      day_master: Tiangan) -> tuple[str, list[str]]:
    """返回 (格局名, 透干说明).

    all_stems: 四柱天干列表 [年干, 月干, 日干, 时干]

    优先级：
    1. 本气透干 → 取本气十神为格（建禄格/羊刃格特殊处理）
    2. 中气透干 → 取中气十神为格
    3. 余气透干 → 取余气十神为格
    4. 均不透 → 取本气十神为格
    """
    hidden_list = DIZHI_CANGGAN[month_branch]
    notes: list[str] = []

    for hs in hidden_list:
        if hs.stem in all_stems:
            ss = get_ten_god(day_master, hs.stem)
            notes.append(f"月支{month_branch.value} {hs.level}{hs.stem.value}透干")

            if hs.level == "本气":
                lu = TIANGAN_LU.get(day_master)
                yangren = TIANGAN_YANGREN.get(day_master)
                if month_branch == lu:
                    return "建禄格", notes
                if month_branch == yangren:
                    return "羊刃格", notes

            return f"{ss.value}格", notes

    benqi = hidden_list[0]
    ss = get_ten_god(day_master, benqi.stem)
    notes.append(f"月支{month_branch.value}本气{benqi.stem.value}不透，取本气为格")
    return f"{ss.value}格", notes


def validate_pattern(pattern: str, day_master,
                     pillars_data: list[dict],
                     harmful_shishen: list[str],
                     weighted_scores: dict | None = None,
                     strength: str = "中和",
                     tiaohou_is_fei_ju: bool = False) -> dict:
    """验证格局成格/破格/带忌/不成格。

    来源:
    - 骨架: 《子平真诠·论用神》——善神(财官印食)顺用,凶神(杀伤枭刃)逆用
    - 效率: 段建业盲派——"制得干净"才成格,制不尽降格
    - 多视角: 陆致极——格局+强弱+调候综合判定
    - 调候: 梁湘润+《穷通宝鉴》——废局下格局先天打折

    Returns:
        {"status": "成格"/"破格"/"带忌"/"不成格",
         "issues": [破格/带忌原因],
         "supports": [成格支撑],
         "note": 一句话说明}
    """
    issues: list[str] = []
    supports: list[str] = []

    def _w(name: str) -> float:
        return (weighted_scores or {}).get(name, 0)

    shi_w = _w("食神"); shang_w = _w("伤官")
    guan_w = _w("正官"); sha_w = _w("偏官") + _w("七杀")
    cai_w = _w("正财") + _w("偏财"); yin_w = _w("正印") + _w("偏印")
    bijie_w = _w("比肩") + _w("劫财")

    all_shishen = set()
    for p in pillars_data:
        if p.get("ten_god"):
            all_shishen.add(p["ten_god"])
        all_shishen.update(p.get("hidden_ten_gods", []))

    shang_tg = any((p.get("ten_god") or "") == "伤官" and p.get("source") == "stem" for p in pillars_data)
    shi_tg = any((p.get("ten_god") or "") == "食神" and p.get("source") == "stem" for p in pillars_data)
    guan_tg = any((p.get("ten_god") or "") == "正官" and p.get("source") == "stem" for p in pillars_data)
    sha_tg = any((p.get("ten_god") or "") in ("偏官", "七杀") and p.get("source") == "stem" for p in pillars_data)
    cai_tg = any("财" in (p.get("ten_god") or "") and p.get("source") == "stem" for p in pillars_data)
    yin_tg = any("印" in (p.get("ten_god") or "") and p.get("source") == "stem" for p in pillars_data)
    pian_yin_tg = any((p.get("ten_god") or "") == "偏印" and p.get("source") == "stem" for p in pillars_data)

    has_shi = "食神" in all_shishen; has_shang = "伤官" in all_shishen
    has_guan = "正官" in all_shishen; has_sha = "偏官" in all_shishen or "七杀" in all_shishen
    has_yin = "正印" in all_shishen or "偏印" in all_shishen

    pk = pattern.replace("格", "")
    is_weak = "弱" in strength
    tiaohou_penalty = tiaohou_is_fei_ju

    # ═══ 正官格(善神,顺用:喜财生印护) ═══
    if pk == "正官":
        if shang_tg:
            issues.append("伤官见官——格局已破(《子平真诠》:伤官克官)")
        if guan_tg and sha_tg:
            issues.append("官杀混杂——两套标准互扰")
        if cai_tg and yin_tg:
            supports.append("财印双辅——官得财生印护,格局气足")
        elif cai_tg:
            supports.append("财生官——有资源支撑")
        elif yin_tg:
            supports.append("印护官——有理解框架护身")

    # ═══ 七杀格(凶神,逆用:喜食制/印化) ═══
    elif pk in ("七杀", "偏官"):
        zhi_clean = shi_w >= sha_w * 1.5 or shang_w >= sha_w * 1.5
        zhi_barely = (shi_w >= sha_w * 0.7) or (shang_w >= sha_w * 0.7)
        has_zhi = shi_tg or shang_tg; has_hua = yin_tg

        if has_zhi and has_hua:
            issues.append("制化两立——食制又见印化,互相掣肘(《子平真诠》:制化不宜并见)")
        elif shi_tg and zhi_clean:
            supports.append("食神制杀且制得干净(段建业:制力>=杀1.5倍)——最佳成格")
        elif shi_tg and zhi_barely:
            supports.append("食神制杀但制力偏弱(段建业:制不尽)——需大运补足")
        elif shang_tg and zhi_clean:
            supports.append("伤官驾杀且制得干净——成格但偏激")
        elif has_hua:
            supports.append("杀印相生——压力转化为权威")
        elif cai_tg and not has_zhi and not has_hua:
            issues.append("财生杀攻身——杀逢财生,无制化(《子平真诠》:财生杀,攻身尤甚)")
        elif not has_zhi and not has_hua:
            issues.append("杀无制化——无食伤制也无印化")

    # ═══ 财格(善神,顺用:喜食生/官护) ═══
    elif pk in ("正财", "偏财"):
        if bijie_w >= 4 and not guan_tg and not shi_tg:
            issues.append("比劫夺财无救——财被劫,无官护/食泄(《子平真诠》:财轻比重)")
        if sha_tg and not shi_tg and not shang_tg:
            issues.append("财格透杀——财杀结党,无食制(《子平真诠》:财格露杀)")
        if is_weak and cai_w >= 6:
            issues.append("财多身弱(陆致极:身弱不胜财官)——格局效率打折")
        if shi_tg:
            supports.append("食神生财——创造力持续供能")
        if guan_tg:
            supports.append("财旺生官——资源支撑权威")

    # ═══ 印格(善神,顺用:喜官杀生/食泄) ═══
    elif pk in ("正印", "偏印"):
        if cai_tg and not guan_tg and not sha_tg:
            issues.append("财破印无救——独印被财坏,无官杀通关(《子平真诠》:印轻逢财)")
        if sha_tg:
            supports.append("杀印相生——压力喂养安全系统")
        elif guan_tg:
            supports.append("官印双全——贵气流通")
        if (shi_tg or shang_tg) and yin_w >= 6:
            supports.append("印旺食泄——印格有输出通道(陆致极:印重需食伤泄秀)")

    # ═══ 食神格(善神,顺用:喜生财/制杀) ═══
    elif pk == "食神":
        if pian_yin_tg and "偏印" in harmful_shishen:
            issues.append("枭神夺食——创造本能被绞杀(《子平真诠》:食逢枭)")
        if cai_tg:
            supports.append("食神生财——创造力能变现")
        if sha_tg:
            if shi_w >= sha_w * 1.2:
                supports.append("食神制杀且制得干净(段建业)——英雄独压万人")
            else:
                supports.append("食神制杀但制力偏弱——需大运补足")

    # ═══ 伤官格(凶神,逆用:喜生财/佩印/驾杀) ═══
    elif pk == "伤官":
        if has_guan:
            issues.append("伤官见官——除金水伤官外格局有伤(《子平真诠》:伤官见官,为祸百端)")
        if cai_tg:
            supports.append("伤官生财——天赋有商业出口")
        if yin_tg:
            supports.append("印制伤官——安全系统调和真我(陆致极:伤官佩印,贵格)")

    # ═══ 阳刃格(凶神,逆用:喜官杀制) ═══
    elif pk == "羊刃":
        if guan_tg or sha_tg:
            supports.append("官杀制刃——行动力有方向")
        else:
            issues.append("阳刃无制——刃无官杀,暴戾难驯(《子平真诠》)")

    # ═══ 建禄月劫格(善神:透官用财印/透财用食/透杀用食制) ═══
    elif pk == "建禄":
        if guan_tg:
            supports.append("建禄透官——有权威方向")
        if cai_tg and (shi_tg or shang_tg):
            supports.append("建禄透财带食伤——财有源头")
        if sha_tg and (shi_tg or shang_tg):
            supports.append("建禄透杀带食制——高压有解")
        if sha_tg and yin_tg and not (shi_tg or shang_tg):
            issues.append("建禄透杀印无食制——杀无制(《子平真诠》:忌杀印同途)")

    # ═══ 判定(四档) ═══
    if tiaohou_penalty and not issues:
        issues.append("调候废局(梁湘润:调候严重失衡→格局先天打折)")

    if issues and not supports:
        status = "破格"
        note = f"{pattern}已破：{'；'.join(issues)}。勿按格局特性解读,应基于实际十神分布。"
    elif issues and supports:
        status = "带忌"
        note = f"{pattern}成中有败：{'；'.join(supports)}。但{'；'.join(issues)}。格局部分可用。"
    elif not issues and supports:
        status = "成格"
        note = f"{pattern}成格：{'；'.join(supports)}。"
    else:
        status = "不成格"
        note = f"{pattern}无明显成破信号,格局标签支撑不足。"

    return {"status": status, "issues": issues, "supports": supports, "note": note}
