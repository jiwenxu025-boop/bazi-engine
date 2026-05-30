"""家境分析"""
from ..enums import Tiangan, Dizhi, Shishen, Wuxing
from .._constants import DIZHI_CANGGAN, SHIER_CHANGSHENG
from .dataclasses import FamilyResult
from .constants import FAMILY_LEVELS
from .special_combos import _yangren_branch


def _find_parent_star(stars: list[str], pillars_data: list[dict]) -> dict:
    """灵活检测父母星：同时检查正偏两类，取更强的一方。

    Returns:
        {"found": bool, "best_star": str, "positions": [...], "tougan": bool}
    """
    found = False
    tougan = False
    positions = []
    best_star = stars[0]
    best_score = 0

    for star in stars:
        star_score = 0
        star_positions = []
        star_tougan = False
        for p in pillars_data:
            tg = p.get("ten_god", "")
            if tg == star:
                found = True
                star_tougan = True
                star_score += 2  # 透干权重2
                star_positions.append(f"{p['pillar_type']}透干")
            for hs_name in p.get("hidden_ten_gods", []):
                if hs_name == star:
                    found = True
                    star_score += 1  # 藏干权重1
                    star_positions.append(f"{p['pillar_type']}藏干")

        if star_score > best_score:
            best_score = star_score
            best_star = star
            positions = star_positions
            tougan = star_tougan

    if not positions and found:
        # fallback
        for star in stars:
            for p in pillars_data:
                for hs_name in p.get("hidden_ten_gods", []):
                    if hs_name == star:
                        positions.append(f"{p['pillar_type']}藏干")
                        best_star = star
                        break

    return {"found": found, "best_star": best_star, "positions": positions, "tougan": tougan}

def analyze_family(
    day_master_stem: str,
    day_master_wuxing: str,
    gender: str,
    strength: str,
    yongshen_result: dict | None,
    pillars_data: list[dict],
    interactions: dict,
    pattern: str,
    family_context: dict | None = None,
) -> FamilyResult:
    """分析家境

    Args:
        yongshen_result: {"favorable_wuxing": [...], "harmful_wuxing": [...], ...}
        pillars_data: 四柱数据，含 ten_god, hidden_ten_gods, stem, branch
        interactions: {"tiangan": [...], "dizhi": [...]}
    """
    result = FamilyResult()
    fav_wx = set(yongshen_result.get("favorable_wuxing", [])) if yongshen_result else set()
    harm_wx = set(yongshen_result.get("harmful_wuxing", [])) if yongshen_result else set()

    def _wx_of_stem(s: str) -> str:
        try:
            return Tiangan(s).wuxing.value
        except (ValueError, KeyError):
            return ""

    def _wx_of_branch(b: str) -> str:
        try:
            return Dizhi(b).wuxing.value
        except (ValueError, KeyError):
            return ""

    def _is_wx_fav(wx: str) -> bool:
        if not fav_wx:  # 无喜用数据时不做判断，默认中性
            return True
        return wx in fav_wx

    year_p = pillars_data[0] if len(pillars_data) > 0 else {}
    month_p = pillars_data[1] if len(pillars_data) > 1 else {}
    day_p = pillars_data[2] if len(pillars_data) > 2 else {}
    hour_p = pillars_data[3] if len(pillars_data) > 3 else {}

    year_stem = year_p.get("stem", "")
    year_branch = year_p.get("branch", "")
    month_stem = month_p.get("stem", "")
    month_branch = month_p.get("branch", "")
    day_branch = day_p.get("branch", "")
    hour_branch = hour_p.get("branch", "")

    year_stem_wx = _wx_of_stem(year_stem)
    year_branch_wx = _wx_of_branch(year_branch)
    month_stem_wx = _wx_of_stem(month_stem)
    month_branch_wx = _wx_of_branch(month_branch)

    year_tg_fav = _is_wx_fav(year_stem_wx)
    year_dz_fav = _is_wx_fav(year_branch_wx)
    month_tg_fav = _is_wx_fav(month_stem_wx)
    month_dz_fav = _is_wx_fav(month_branch_wx)

    # ── 年月财官检查 ──
    year_tg = year_p.get("ten_god", "")
    month_tg = month_p.get("ten_god", "")
    year_has_cai = "财" in str(year_tg)
    year_has_guan = "官" in str(year_tg) or "杀" in str(year_tg)
    month_has_cai = "财" in str(month_tg)
    month_has_guan = "官" in str(month_tg) or "杀" in str(month_tg)

    nian_caiguan = year_has_cai or year_has_guan
    yue_caiguan = month_has_cai or month_has_guan

    # ── 家境评级（基于古籍权威规则）──
    # 来源：
    # 《滴天髓》任铁樵注：「财官印绶，在于年月，为日主之喜，父母不贵亦富；为日主之忌，不贫亦贱。」
    # 《渊海子平》：「岁月财官印绶，生于富贵之家」「岁月伤官劫财，生于贫贱之家」
    # 《渊海子平》：「年月相冲，难为祖业」
    # 《三命通会》：纳音月生年→祖业受生
    # 验证日期: 2026-05-26

    # 核心判定：年月柱的十神是否为喜用
    year_tg_is_fav = year_tg_fav if fav_wx else True  # 无喜用数据时默认中性
    month_tg_is_fav = month_tg_fav if fav_wx else True

    # 年月是否有财/官/印透干
    year_has_caiguan = year_has_cai or year_has_guan
    year_has_yin = "印" in str(year_tg)
    month_has_caiguan = month_has_cai or month_has_guan
    month_has_yin = "印" in str(month_tg)
    year_has_caiguanyin = year_has_caiguan or year_has_yin
    month_has_caiguanyin = month_has_caiguan or month_has_yin

    # 年月是否有伤官/劫财
    month_has_shangjie = month_tg in ("伤官", "劫财")
    year_has_shangjie = year_tg in ("伤官", "劫财")

    level_reasons = []

    # 【核心规则】年月财官印为喜用 → 宽裕/普通；为忌 → 普通/紧张
    # 来源：《滴天髓》「财官印绶，在于年月，为日主之喜，父母不贵亦富；为日主之忌，不贫亦贱」
    # 注：三档模糊分类+置信度，不强行细分（统计数据显示四层细分准确率仅20-30%）

    # 年月是否有升级信号
    upgrade_signals = 0
    if year_has_guan and month_has_guan:
        upgrade_signals += 1
        level_reasons.append("年月双透官杀（父母辈有实质权威）")
    month_tg_name = month_p.get("ten_god", "")
    if month_tg_name in ("食神", "伤官") and month_stem_wx and fav_wx and month_stem_wx in fav_wx:
        upgrade_signals += 1
        level_reasons.append("月柱食伤为喜用（父母有真技术/本事）")
    # 纳音月生年
    year_nayin = year_p.get("nayin", "")
    month_nayin = month_p.get("nayin", "")
    yn_wx = None; mn_wx = None
    for kw in ("金", "木", "水", "火", "土"):
        if kw in year_nayin: yn_wx = kw
        if kw in month_nayin: mn_wx = kw
    _wx_sheng_map = {"木": "火", "火": "土", "土": "金", "金": "水", "水": "木"}
    if yn_wx and mn_wx and _wx_sheng_map.get(mn_wx) == yn_wx:
        upgrade_signals += 1
        level_reasons.append("纳音月生年（祖业受生）")

    # 年月是否有降级信号
    downgrade_signals = 0
    ym_chong = any(
        "年柱" in inter.get("pillars", []) and "月柱" in inter.get("pillars", [])
        and inter["type"] == "六冲"
        for inter in interactions.get("dizhi", [])
    )
    if ym_chong:
        downgrade_signals += 1
        level_reasons.append("年月相冲（难为祖业）")

    # 核心判定
    if (year_has_caiguanyin and year_tg_is_fav) or (month_has_caiguanyin and month_tg_is_fav):
        # 财官印为喜用 → 普通打底，有升级→宽裕
        if upgrade_signals >= 1:
            result.level = "宽裕"
            confidence = "中高"
            level_reasons.append("《滴天髓》：父母不贵亦富 + 升级信号 → 宽裕")
        else:
            result.level = "普通"
            confidence = "中"
            level_reasons.append("《滴天髓》：喜用匹配但无额外信号 → 普通")
    elif year_has_caiguanyin or month_has_caiguanyin:
        # 有财官印但是忌神
        if downgrade_signals >= 1:
            result.level = "紧张"
            confidence = "中高"
            level_reasons.append("《滴天髓》：财官为忌 + 降级信号 → 紧张")
        else:
            result.level = "普通"
            confidence = "中"
            level_reasons.append("《滴天髓》：财官为忌但无严重降级 → 普通")
    elif month_has_shangjie or year_has_shangjie:
        result.level = "紧张"
        confidence = "中"
        level_reasons.append("《渊海子平》：年月伤官劫财 → 紧张")
    else:
        result.level = "普通"
        confidence = "低"

    result.reality = "；".join(level_reasons) if level_reasons else "年月组合平正，信号不明确"
    result.reality += f"（置信度: {confidence}）"
    result.level_label = FAMILY_LEVELS.get(result.level, "家境普通")

    # ── 父母星（灵活检测：同时检查正偏两类）──
    father_stars = ["偏财", "正财"]  # 双星检测，哪个强用哪个
    mother_stars = ["正印", "偏印"]

    father_info = _find_parent_star(father_stars, pillars_data)
    mother_info = _find_parent_star(mother_stars, pillars_data)

    father_found = father_info["found"]
    mother_found = mother_info["found"]
    father_positions = father_info["positions"]
    mother_positions = mother_info["positions"]
    father_tougan = father_info["tougan"]
    mother_tougan = mother_info["tougan"]
    father_canggan_only = father_found and not father_tougan
    mother_canggan_only = mother_found and not mother_tougan
    father_star = father_info["best_star"]
    mother_star = mother_info["best_star"]

    # 检查父星/母星是否受冲克
    year_stem_is_father = year_tg == father_star
    year_stem_is_mother = year_tg == mother_star
    month_stem_is_father = month_tg == father_star
    month_stem_is_mother = month_tg == mother_star

    father_chongke = False
    mother_chongke = False
    father_chong_type = ""
    mother_chong_type = ""
    for inter in interactions.get("dizhi", []):
        if inter["type"] in ("六冲", "相害", "相刑"):
            pills = inter["pillars"]
            if year_stem_is_father and "年柱" in pills:
                father_chongke = True
                father_chong_type = inter["type"]
            if month_stem_is_father and "月柱" in pills:
                father_chongke = True
                father_chong_type = inter["type"]
            if year_stem_is_mother and "年柱" in pills:
                mother_chongke = True
                mother_chong_type = inter["type"]
            if month_stem_is_mother and "月柱" in pills:
                mother_chongke = True
                mother_chong_type = inter["type"]

    # 父亲描述（细化：位置+状态）
    if not father_found:
        result.father = f"父星（{father_star}）四柱不显→ 父缘较薄，父亲影响力不突出或不在正位"
    elif father_chongke:
        result.father = (f"父星（{father_star}）{', '.join(father_positions)}受{father_chong_type}→ "
                         f"父缘较薄，宜关注父亲健康，父子关系需用心维护")
    elif father_canggan_only:
        result.father = (f"父星（{father_star}）仅藏于{'、'.join(father_positions)}→ "
                         f"父亲影响力隐而不显，暗中支持但不直接出面")
    else:
        # 透干 → 看在哪一柱
        pos_details = []
        for pos in father_positions:
            if "年柱" in pos:
                pos_details.append("幼年父亲影响力明显")
            elif "月柱" in pos:
                pos_details.append("青少年期父亲承担主要养育角色")
            elif "时柱" in pos:
                pos_details.append("父亲影响来得晚但持久")
        pos_str = "；".join(pos_details) if pos_details else "父亲有一定影响力"
        result.father = f"父星（{father_star}）见于{'、'.join(father_positions)}→ {pos_str}"

    # 年支藏比肩 + 偏财不显 → 父亲财务问题（校准: 徐继文）
    year_branch_hidden = year_p.get("hidden_ten_gods", [])
    if "比肩" in year_branch_hidden and not father_found:
        result.father += ("。年支藏比肩夺财+父星不显→ "
                          "父亲可能有娱乐应酬过度、赌博或挥霍习惯，对家庭经济有负面消耗")

    # 母亲描述（细化）
    if not mother_found:
        result.mother = f"母星（{mother_star}）四柱不显→ 母缘较薄，母亲影响来得晚或较间接"
    elif mother_chongke:
        result.mother = (f"母星（{mother_star}）{', '.join(mother_positions)}受{mother_chong_type}→ "
                         f"母体弱或母子缘浅")
    elif mother_canggan_only:
        result.mother = (f"母星（{mother_star}）仅藏于{'、'.join(mother_positions)}→ "
                         f"母亲影响隐性的，在背后付出但不居功")
    else:
        pos_details = []
        for pos in mother_positions:
            if "年柱" in pos:
                pos_details.append("幼年受母亲影响最深")
            elif "月柱" in pos:
                pos_details.append("青少年期母亲扮演关键角色")
            elif "时柱" in pos:
                pos_details.append("母亲影响伴随终生且愈老愈深")
        pos_str = "；".join(pos_details) if pos_details else "母亲有一定影响力"
        result.mother = f"母星（{mother_star}）见于{'、'.join(mother_positions)}→ {pos_str}"

    # ── 祖辈/父母关系 ──
    relation_notes = []
    for inter in interactions.get("dizhi", []):
        pills = inter["pillars"]
        if "年柱" in pills and "月柱" in pills:
            if inter["type"] == "相害":
                relation_notes.append("年支月支相害→ 父亲与祖辈关系不和")
            elif inter["type"] == "六冲":
                relation_notes.append("年柱月柱相冲→ 离祖成家，祖辈与父母辈关系紧张")
            elif inter["type"] == "相刑":
                relation_notes.append("年柱月柱相刑→ 祖辈与父母辈有矛盾摩擦")

    # 财破印 → 父母感情（需验证五行克制：财的五行克印的五行才算）
    # 财克印五行对: 木克土, 火克金, 土克水, 金克木, 水克火
    _wx_ke_map = {"木": "土", "火": "金", "土": "水", "金": "木", "水": "火"}
    has_cai_ke_yin = False
    for p in pillars_data:
        if p.get("ten_god", "") in ("正财", "偏财"):
            cai_wx = p.get("stem_wuxing", "")
            for p2 in pillars_data:
                if p2.get("ten_god", "") in ("正印", "偏印"):
                    yin_wx = p2.get("stem_wuxing", "")
                    if p["pillar_type"] != p2["pillar_type"] and cai_wx and yin_wx:
                        if _wx_ke_map.get(cai_wx) == yin_wx:
                            has_cai_ke_yin = True
                            break
            if has_cai_ke_yin:
                break
    if has_cai_ke_yin:
        relation_notes.append("财星克印星（五行真克）→ 财破印，父母感情可能不佳或家庭不和谐")

    result.parents_relation = "；".join(relation_notes) if relation_notes else "父母关系无明显冲克"

    # ── 离祖成家信号 ──
    # 来源：《三命通会》：年月相冲者离祖，日支冲年支者离乡
    leaves_home_notes = []
    day_chong_year = False
    for inter in interactions.get("dizhi", []):
        if inter["type"] == "六冲":
            pills = inter["pillars"]
            if "日柱" in pills and "年柱" in pills:
                day_chong_year = True
                leaves_home_notes.append("日支冲年支→ 离祖成家，异地发展，与祖地缘薄")
    is_strong = "强" in strength

    # ── 继承情况 ──
    if (nian_caiguan or yue_caiguan) and is_strong:
        result.inheritance = "年月有财官+身强能担→ 能承接家庭资源并发扬"
    elif (nian_caiguan or yue_caiguan) and not is_strong:
        result.inheritance = "年月有财官但身弱难担→ 家庭资源有限或自身无法充分利用"
    elif is_strong:
        result.inheritance = "年月无财官但身强→ 白手起家，靠自己本事"
    else:
        result.inheritance = "年月无财官+身弱→ 出身普通，发展较慢"

    if day_chong_year:
        result.inheritance += " 日年相冲→ 成年后离家发展，自力更生。"

    # 正财合日主 → 家庭资源倾斜（校准: 徐继文）
    for inter in interactions.get("tiangan", []):
        if inter["type"] == "天干五合" and day_master_stem in inter["participants"]:
            for p in pillars_data:
                if p["stem"] in inter["participants"] and p["stem"] != day_master_stem:
                    if p.get("ten_god") in ("正财", "偏财"):
                        result.inheritance += (
                            f" {p['stem']}{day_master_stem}合，正财合身→"
                            "家庭资源向命主倾斜，家里愿意在命主身上投入"
                        )
                        break
            break

    # ═══ 双亲寿元提示（来源：《滴天髓·六亲论》）═══
    # "财气斩丧于时干者，先克父；印气斩丧于时支者，先克母"
    health_notes = []
    hour_tg = hour_p.get("ten_god", "")
    if "财" in str(hour_tg) and father_found:
        health_notes.append("时干见财—古籍提示宜关注父亲健康")
    hour_hidden = hour_p.get("hidden_ten_gods", [])
    if any("印" in h for h in hour_hidden) and mother_found:
        health_notes.append("时支藏印—古籍提示宜关注母亲健康")
    # 父母星入墓库
    for p in pillars_data:
        for hs in p.get("hidden_ten_gods", []):
            if hs == father_star:
                # 父星在墓库支（辰戌丑未）
                if p.get("branch") in ("辰", "戌", "丑", "未"):
                    health_notes.append(f"父星入{p['pillar_type']}墓库—古籍提示宜关注父亲健康")
            if hs == mother_star:
                if p.get("branch") in ("辰", "戌", "丑", "未"):
                    health_notes.append(f"母星入{p['pillar_type']}墓库—古籍提示宜关注母亲健康")
    # 财星坐羊刃
    yr = _yangren_branch(day_master_stem)
    for p in pillars_data:
        if p.get("ten_god") == father_star and p.get("branch") == yr:
            health_notes.append("父星坐羊刃—《渊海子平》：财坐刃，父有损伤")
            break
    # 比劫重重克父
    bijie_total = sum(1 for p in pillars_data if p.get("ten_god") in ("比肩", "劫财"))
    bijie_total += sum(1 for p in pillars_data for h in p.get("hidden_ten_gods", []) if h in ("比肩", "劫财"))
    if bijie_total >= 3 and father_found:
        health_notes.append(f"比劫较多({bijie_total}个)—古籍提示父子关系可能有摩擦，宜多沟通")
    result.parents_health = "；".join(health_notes) if health_notes else "父母健康无明显古典警示"

    # ═══ 父母星旺衰（来源：《三命通会》长生十二宫）═══
    # 五行特定长生顺排：从长生位开始，顺数十二宫
    _wuxing_changsheng = {
        "木": ["亥","子","丑","寅","卯","辰","巳","午","未","申","酉","戌"],
        "火": ["寅","卯","辰","巳","午","未","申","酉","戌","亥","子","丑"],
        "土": ["申","酉","戌","亥","子","丑","寅","卯","辰","巳","午","未"],
        "金": ["巳","午","未","申","酉","戌","亥","子","丑","寅","卯","辰"],
        "水": ["申","酉","戌","亥","子","丑","寅","卯","辰","巳","午","未"],
    }
    _cycle_names = ["长生","沐浴","冠带","临官","帝旺","衰","病","死","墓","绝","胎","养"]

    def _get_changsheng(branch: str, wuxing: str) -> str:
        """返回某地支在该五行长生十二宫中的位置名"""
        if wuxing not in _wuxing_changsheng: return ""
        try:
            idx = _wuxing_changsheng[wuxing].index(branch)
            return _cycle_names[idx]
        except ValueError:
            return ""

    # 父星坐长生: 偏财五行
    father_wx_map = {"偏财": _wx_of_stem(""), "正财": _wx_of_stem("")}
    # 直接取父星所在柱的天干五行作为偏财五行
    for p in pillars_data:
        if p.get("ten_god") == father_star:
            fb = p.get("branch", "")
            fw = p.get("stem_wuxing", "")
            if fw:
                cycle_name = _get_changsheng(fb, fw)
                if cycle_name in ("长生", "帝旺", "临官"):
                    result.father += f"（父坐{fb}为{fw}之{cycle_name}，父亲康强）"
                elif cycle_name in ("死", "绝", "墓"):
                    result.father += f"（父坐{fb}为{fw}之{cycle_name}，父缘薄弱）"
            break

    for p in pillars_data:
        if p.get("ten_god") == mother_star:
            mb = p.get("branch", "")
            mw = p.get("stem_wuxing", "")
            if mw:
                cycle_name = _get_changsheng(mb, mw)
                if cycle_name in ("长生", "帝旺", "临官"):
                    result.mother += f"（母坐{mb}为{mw}之{cycle_name}，母亲康强）"
                elif cycle_name in ("死", "绝", "墓"):
                    result.mother += f"（母坐{mb}为{mw}之{cycle_name}，母缘薄弱）"
            break

    # ═══ 家庭出身类型（来源：《滴天髓·六亲论》）═══
    ft_notes = []
    year_tg_name = year_p.get("ten_god", "")
    month_tg_name = month_p.get("ten_god", "")
    # 年官月印 → 书香/官宦
    if "官" in str(year_tg_name) and "印" in str(month_tg_name):
        ft_notes.append("年官月印—《滴天髓》：祖上清高，出身书香或官宦之家")
    elif "印" in str(year_tg_name) and "官" in str(month_tg_name):
        ft_notes.append("年印月官—《滴天髓》：上叨荫庇，得祖辈福泽")
    # 年财月印 → 商贾富家
    if "财" in str(year_tg_name) and "印" in str(month_tg_name):
        ft_notes.append("年财月印—《滴天髓》：帮父兴家，家业有望")
    # 年伤+月劫 或 年伤→ 出身
    if "伤" in str(year_tg_name) and "劫" in str(month_tg_name):
        ft_notes.append("年伤月劫—出身靠自己，白手起家类型")
    if "伤" in str(year_tg_name):
        ft_notes.append("年柱伤官—祖业助力有限，独立性强")
    # 月柱七杀 → 早年艰苦
    if "七杀" in str(month_tg_name) or "偏官" in str(month_tg_name):
        ft_notes.append("月柱七杀—《渊海子平》：早年艰苦，家境不丰")
    # 年柱正官/正印
    if str(year_tg_name) == "正官":
        ft_notes.append("年柱正官—《三命通会》：出身正统，有家规")
    if str(year_tg_name) == "正印":
        ft_notes.append("年柱正印—《三命通会》：书香门第，得祖萌")
    # 月令判断
    from ..enums import Dizhi as _Dizhi
    try:
        month_branch_enum = _Dizhi(month_branch)
        month_wx_val = month_branch_enum.wuxing.value
        if month_wx_val == day_master_wuxing:
            ft_notes.append("月令建禄—出身中产，自食其力")
        # 财通门户
        dm_fav = set(yongshen_result.get("favorable_wuxing", [])) if yongshen_result else set()
        if month_wx_val in dm_fav:
            ft_notes.append(f"月令{month_wx_val}为喜用—家境有根基")
    except (ValueError, KeyError):
        pass

    if not ft_notes:
        ft_notes.append("年月组合平正，非典型家世格局")
    result.family_type = "；".join(ft_notes)

    # ═══ 童年环境（来源：《三命通会》+《滴天髓》）═══
    childhood_notes = []
    # 年月空亡
    yr_cb = year_p.get("branch", "")
    mt_cb = month_p.get("branch", "")
    kws = {"申": ("戌", "亥"), "子": ("戌", "亥"), "辰": ("戌", "亥"),
           "寅": ("子", "丑"), "午": ("子", "丑"), "戌": ("子", "丑"),
           "巳": ("午", "未"), "酉": ("午", "未"), "丑": ("午", "未"),
           "亥": ("申", "酉"), "卯": ("申", "酉"), "未": ("申", "酉")}
    yr_kw = kws.get(yr_cb, ("", ""))
    mt_kw = kws.get(mt_cb, ("", ""))
    if mt_cb in yr_kw:
        childhood_notes.append("月柱空亡—《渊海子平》：父母无靠，童年动荡")
    # 年冲日
    for inter in interactions.get("dizhi", []):
        if inter["type"] == "六冲" and "年柱" in inter.get("pillars", []) and "日柱" in inter.get("pillars", []):
            childhood_notes.append("年日相冲—《三命通会》：童年离祖，早离父母庇护")
    # 火土燥烈 → 家境一般
    n_fire_earth = sum(1 for p in pillars_data
                       if p.get("stem_wuxing") in ("火", "土") or p.get("branch_wuxing") in ("火", "土"))
    n_water = sum(1 for p in pillars_data
                  if p.get("stem_wuxing") == "水" or p.get("branch_wuxing") == "水")
    if n_fire_earth >= 6 and n_water <= 1:
        childhood_notes.append("四柱火土燥烈—《穷通宝鉴》：家境偏炎旱，可能起伏较大")
    # 金水清润 → 较好
    n_metal = sum(1 for p in pillars_data
                  if p.get("stem_wuxing") == "金" or p.get("branch_wuxing") == "金")
    if n_metal >= 2 and n_water >= 2:
        childhood_notes.append("金水相涵—《穷通宝鉴》：出身清润，环境不差")
    result.childhood = "；".join(childhood_notes) if childhood_notes else "童年环境无明显特殊信号"

    # ═══ 祖辈状况（来源：《三命通会》纳音）═══
    ancestral_notes = []
    # 纳音生克
    if year_nayin and month_nayin:
        try:
            ny_wx = ""
            mn_wx = ""
            for kw, v in {"金": "金", "木": "木", "水": "水", "火": "火", "土": "土"}.items():
                if kw in year_nayin: ny_wx = v
                if kw in month_nayin: mn_wx = v
            if ny_wx and mn_wx:
                from ..ten_gods import wuxing_ke, wuxing_sheng
                try:
                    if wuxing_sheng(Wuxing(ny_wx)) == Wuxing(mn_wx):
                        ancestral_notes.append(f"年纳音{ny_wx}生月纳音{mn_wx}—《三命通会》：祖荫绵长，代际传承好")
                    elif wuxing_ke(Wuxing(ny_wx)) == Wuxing(mn_wx):
                        ancestral_notes.append(f"年纳音{ny_wx}克月纳音{mn_wx}—《三命通会》：祖业破败，代际有损耗")
                except (ValueError, KeyError):
                    pass
        except Exception:
            pass
    # 年柱比劫 → 祖辈普通
    if "比" in str(year_tg_name) or "劫" in str(year_tg_name):
        ancestral_notes.append("年柱比劫—祖辈普通，无显赫家世")
    if not ancestral_notes:
        ancestral_notes.append("祖辈平正，无特殊格局标记")
    result.ancestral = "；".join(ancestral_notes)

    # ═══ 综合描述 ═══
    parts = [f"家境等级：{result.level}（{result.level_label}）。"]
    if result.surface:
        parts.append(f"表面：{result.surface}")
    if result.reality:
        parts.append(f"实际：{result.reality}")
    if result.family_type:
        parts.append(f"出身：{result.family_type}")
    parts.append(f"父亲：{result.father}")
    parts.append(f"母亲：{result.mother}")
    if result.parents_health:
        parts.append(f"双亲健康：{result.parents_health}")
    parts.append(f"童年：{result.childhood}")
    parts.append(f"祖辈：{result.ancestral}")
    parts.append(f"继承：{result.inheritance}")
    if relation_notes:
        parts.append(f"关系：{'；'.join(relation_notes)}")
    if leaves_home_notes:
        parts.append(f"迁徙：{'；'.join(leaves_home_notes)}")
    # ── 用户校准：与已知家境对比 ──
    if family_context:
        user_level = family_context.get("economic_level", "")
        if user_level and user_level != result.level:
            result.reality += (
                f" | 你反馈：{user_level} | "
                f"差异可能原因：古籍规则基于命局大势，现实中后天环境（地域/时代/个人选择）"
                f"可造成同八字不同家境，八字抓大方向但抓不到具体量级"
            )
        if family_context.get("father_occupation"):
            result.father += f"（已知职业：{family_context['father_occupation']}）"
        if family_context.get("mother_occupation"):
            result.mother += f"（已知职业：{family_context['mother_occupation']}）"

    return result

