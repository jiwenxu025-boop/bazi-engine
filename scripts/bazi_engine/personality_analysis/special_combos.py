"""特殊组合检测 — 十神+地支+神煞联动"""
from ..enums import Tiangan, Dizhi, Wuxing, Shishen
from .._constants import (
    TAOHUA, HUAGAI, DIZHI_LIUHE, DIZHI_LIUCHONG,
    DIZHI_XIANGHAI, DIZHI_XIANGXING, DIZHI_SANHE, DIZHI_CANGGAN,
)
from ..enums import TIANGAN_YANGREN
from ..ten_gods import get_ten_god
from .constants import SHISHEN_PERSONALITY


def _taohua_branch(day_branch_str: str) -> str | None:
    """桃花: 申子辰在酉, 亥卯未在子, 寅午戌在卯, 巳酉丑在午"""
    map_ = {"申": "酉", "子": "酉", "辰": "酉",
            "亥": "子", "卯": "子", "未": "子",
            "寅": "卯", "午": "卯", "戌": "卯",
            "巳": "午", "酉": "午", "丑": "午"}
    return map_.get(day_branch_str)

def _huagai_branch(day_branch_str: str) -> str | None:
    """华盖: 申子辰见辰, 亥卯未见未, 寅午戌见戌, 巳酉丑见丑"""
    map_ = {"申": "辰", "子": "辰", "辰": "辰",
            "亥": "未", "卯": "未", "未": "未",
            "寅": "戌", "午": "戌", "戌": "戌",
            "巳": "丑", "酉": "丑", "丑": "丑"}
    return map_.get(day_branch_str)

def _yangren_branch(day_stem_str: str) -> str | None:
    """羊刃: 阳干帝旺之支。甲卯 丙午 戊午 庚酉 壬子"""
    map_ = {"甲": "卯", "丙": "午", "戊": "午", "庚": "酉", "壬": "子"}
    return map_.get(day_stem_str)

def _has_branch_in_pillars(branch_str: str, pillars_data: list[dict]) -> bool:
    """检查任意柱是否包含某地支"""
    for p in pillars_data:
        if p.get("branch") == branch_str:
            return True
    return False

def _check_special_combos(day_master_stem: str, day_master_wuxing: str,
                          pillars_data: list[dict],
                          interactions: dict,
                          gender: str,
                          harmful_shishen: list[str],
                          pattern: str) -> list[str]:
    """检测特殊干支组合，标注权威出处"""

    combos = []
    all_tg_names = set()
    all_hidden_tg_names = set()
    all_hidden_levels: dict[str, str] = {}  # {十神: 藏干等级}

    for p in pillars_data:
        if p.get("ten_god"):
            all_tg_names.add(p["ten_god"])
        for hs_name in p.get("hidden_ten_gods", []):
            all_hidden_tg_names.add(hs_name)
            if hs_name not in all_hidden_levels:
                all_hidden_levels[hs_name] = "藏"

    all_names = all_tg_names | all_hidden_tg_names

    # ── 1. 正财合日主（男）/ 正官合日主（女）→ 感情被动 ──
    # 来源：《渊海子平·论妻妾》"正财合身，妻妾有情"
    for inter in interactions.get("tiangan", []):
        if inter["type"] == "天干五合":
            participants = inter["participants"]
            if day_master_stem in participants:
                other = participants[0] if participants[1] == day_master_stem else participants[1]
                for p in pillars_data:
                    if p["stem"] == other:
                        if gender == "男" and p.get("ten_god") == "正财":
                            combos.append(f"正财合身（{day_master_stem}{other}合）→ 重情顾家，感情被动接受，对配偶大方。"
                                          "《渊海子平》：「正财合身，妻妾有情」")
                            break
                        elif gender == "女" and p.get("ten_god") == "正官":
                            combos.append(f"正官合身（{day_master_stem}{other}合）→ 感情偏被动，被追求方，重名节。"
                                          "《渊海子平》：「正气官星，女子贵之」")
                            break

    # ── 2. 食神制七杀 → 权威 ──
    # 来源：《渊海子平·论偏官》"有制伏则为偏官，无制伏则为七杀"
    # 约束：食神或七杀至少有一个透干，避免藏干中普遍存在的弱信号
    shishen_tougan = any(
        p.get("ten_god") == "食神" and p.get("source") == "stem"
        for p in pillars_data
    )
    qisha_tougan = any(
        p.get("ten_god") in ("偏官", "七杀") and p.get("source") == "stem"
        for p in pillars_data
    )
    has_qisha = "偏官" in all_names or "七杀" in all_names
    if (shishen_tougan or qisha_tougan) and "食神" in all_names and has_qisha:
        combos.append("食神制七杀→ 七杀有制化为权，胆识谋略兼备，能化压力为动力，有领导潜质。"
                      "《渊海子平》：「有制伏则为偏官，无制伏则为七杀」")

    # ── 3. 偏印格 + 偏印为忌 → 内外矛盾 ──
    if "偏印" in pattern and "偏印" in harmful_shishen:
        combos.append("偏印格且偏印为忌→ 外表善交但内心疏离孤僻，社交自如但独处时沉入自己的世界。"
                      "《渊海子平》：「倒食者，偏印也，损食神」")

    # ── 4. 伤官见官 → 不守常规、反叛权威 ──
    # 来源：《渊海子平·论伤官》"伤官见官，为祸百端"
    if "伤官" in all_names and "正官" in all_names:
        combos.append("伤官见官→ 不喜约束，反叛权威，思维跳脱常规，适合自由职业。"
                      "《渊海子平》：「伤官见官，为祸百端」——官星受克，仕途多阻，宜换赛道")

    # ── 5. 食伤生财 → 以技艺才华生财 ──
    # 来源：《渊海子平·论食神》"财厚食丰、优游自足"
    has_shishang = "食神" in all_names or "伤官" in all_names
    has_cai = "正财" in all_names or "偏财" in all_names
    if has_shishang and has_cai:
        combos.append("食伤生财→ 以才华技艺求财，创意致富型，善于把自己的能力变现。"
                      "《渊海子平》：「食神生财，富贵自天排」")

    # ── 6. 官印相生 → 规矩守序 ──
    # 来源：《三命通会·论官》"官星得印，文贵之格"
    has_guan = "正官" in all_names or "偏官" in all_names or "七杀" in all_names
    has_yin = "正印" in all_names or "偏印" in all_names
    if has_guan and has_yin:
        combos.append("官印相生→ 规矩守序，尊重权威，有责任感和学识支撑，适合体制内发展。"
                      "《三命通会》：「官星得印，文贵之格，主学而优则仕」")

    # ── 7. 伤官配印 → 天才型 ──
    # 来源：《渊海子平·论伤官》"伤官佩印，贵不可言"
    if "伤官" in all_names and ("正印" in all_names or "偏印" in all_names):
        combos.append("伤官配印→ 才华横溢且有深厚学问为根基，天才型人物，不鸣则已一鸣惊人。"
                      "《渊海子平》：「伤官佩印，贵不可言」")

    # ── 8. 财官双美 → 名利双收倾向 ──
    # 来源：《三命通会·论财官》"财官双美，富贵两全"
    if has_cai and has_guan:
        # 天干位同时有财有官才触发
        tg_cai = any("财" in (p.get("ten_god") or "") for p in pillars_data if p.get("source") == "stem")
        tg_guan = any(("官" in (p.get("ten_god") or "") or "杀" in (p.get("ten_god") or ""))
                      for p in pillars_data if p.get("source") == "stem")
        if tg_cai and tg_guan:
            combos.append("财官双美（天干透财透官）→ 名利心强，追求世俗成就，有富贵潜质。"
                          "《三命通会》：「财官双美，富贵两全」")

    # ── 9. 羊刃驾杀 → 果敢勇猛 ──
    # 来源：《渊海子平·论羊刃》"羊刃驾杀，威镇边疆"
    yr_branch = _yangren_branch(day_master_stem)
    if yr_branch and _has_branch_in_pillars(yr_branch, pillars_data) and \
       ("偏官" in all_names or "七杀" in all_names):
        combos.append("羊刃驾杀→ 刚猛果敢，执行力极强，不惧挑战，适合军警/运动/竞争性行业。"
                      "《渊海子平》：「羊刃驾杀，威镇边疆」")

    # ── 10. 比劫夺财 → 钱财易散 ──
    # 来源：《渊海子平·论比肩》"比劫夺财，财来财去"
    has_bijie = "比肩" in all_names or "劫财" in all_names
    if has_bijie and has_cai:
        combos.append("比劫夺财→ 钱财易散，朋友借贷/合伙须谨慎，赚钱辛苦但花钱爽快。"
                      "《渊海子平》：「比肩分夺、财临沐浴桃花」")

    # ── 11. 财破印 → 现实大于理想 ──
    # 来源：《渊海子平·论财星》"财星破印，贪财坏印"
    if has_cai and has_yin:
        # 财在干印在支，或财藏支印透干，均为财破印
        tg_cai_pillars = [p for p in pillars_data if p.get("source") == "stem" and "财" in (p.get("ten_god") or "")]
        tg_yin_pillars = [p for p in pillars_data if p.get("source") == "stem" and "印" in (p.get("ten_god") or "")]
        if tg_cai_pillars and tg_yin_pillars:
            combos.append("财破印（财星印星同透天干）→ 现实利益与学业/理想冲突，为现实可能舍原则。"
                          "《渊海子平》：「贪财坏印，见利忘义」——需注意价值观摇摆")

    # ── 12. 杀印相生 → 压力化为动力 ──
    # 来源：《三命通会·论七杀》"杀印相生，文武兼备"
    if has_qisha and "正印" in all_names:
        combos.append("杀印相生→ 压力化为动力，困难越大成长越快，有权威且知进退。"
                      "《三命通会》：「杀逢印化，功名显达」")

    # ── 13. 桃花入命（本地计算，不依赖 spirits 模块）──
    # 来源：《渊海子平》桃花煞
    day_branch = pillars_data[2].get("branch", "") if len(pillars_data) > 2 else ""
    taohua = _taohua_branch(day_branch)
    if taohua and _has_branch_in_pillars(taohua, pillars_data):
        position = ""
        for p in pillars_data:
            if p.get("branch") == taohua:
                position = p["pillar_type"]
                break
        if position == "日柱":
            combos.append(f"桃花坐日支（{taohua}在日柱）→ 配偶颜值高，自身人缘好异性缘旺。"
                          "《渊海子平》桃花：主酒色性欲，亦主人缘才艺")
        elif position in ("年柱", "月柱"):
            combos.append(f"桃花在{position}→ 早年人缘好，异性关注度高，有吸引力。")

    # ── 14. 华盖入命 ──
    # 来源：《三命通会》华盖：主孤独、清高、艺术、宗教
    huagai = _huagai_branch(day_branch)
    if huagai and _has_branch_in_pillars(huagai, pillars_data):
        combos.append(f"华盖入命（{huagai}）→ 有精神追求，喜独处钻研，偏冷门/玄学/艺术天赋。"
                      "《三命通会》：「华盖者，喻如宝盖，主孤独清高」")

    # ── 15. 官杀混杂 ──
    # 来源：《渊海子平·论官杀》"官杀混杂，心性不专"
    has_zhengguan_tg = any(p.get("ten_god") == "正官" and p.get("source") == "stem" for p in pillars_data)
    has_qisha_tg = any(p.get("ten_god") in ("偏官", "七杀") and p.get("source") == "stem" for p in pillars_data)
    if has_zhengguan_tg and has_qisha_tg:
        combos.append("官杀混杂（正官七杀同透天干）→ 性格矛盾，优柔与果敢并存，时而规矩时而叛逆。"
                      "《渊海子平》：「官杀混杂，心性不专，事多反复」")

    # ── 16. 伤官伤尽 ──
    # 来源：《渊海子平·论伤官》"伤官伤尽，反为清贵"
    has_shang_tg = any(p.get("ten_god") == "伤官" and p.get("source") == "stem" for p in pillars_data)
    has_zhengguan_any = "正官" in all_tg_names or "正官" in all_hidden_tg_names
    if has_shang_tg and not has_zhengguan_any:
        combos.append("伤官伤尽（伤官透干+全局无正官）→ 才华可尽情发挥不受羁绊，反为清贵。"
                      "《渊海子平》：「伤官伤尽，反为清贵之格」")

    # ── 17. 财多身弱 ──
    # 来源：《渊海子平》"财多身弱，富屋贫人"
    cai_count_all = sum(1 for p in pillars_data if "财" in (p.get("ten_god") or ""))
    cai_count_all += sum(1 for p in pillars_data for h in p.get("hidden_ten_gods", []) if "财" in h)
    if cai_count_all >= 3:
        combos.append(f"财星旺盛（{cai_count_all}个）→ 若身弱则为'富屋贫人'，对财富渴望强但难以掌控；若身强则为财旺身强，能担大财。"
                      "《渊海子平》：「财多身弱，富屋贫人」")

    # ── 18. 食神太过 ──
    # 来源：《渊海子平》"食多变伤，好逸恶劳"
    shi_count_all = sum(1 for p in pillars_data if p.get("ten_god") == "食神")
    shi_count_all += sum(1 for p in pillars_data for h in p.get("hidden_ten_gods", []) if h == "食神")
    if shi_count_all >= 3:
        combos.append(f"食神过旺（{shi_count_all}个）→ 食多变伤，想法多执行少，好逸恶劳但创意无穷。"
                      "《渊海子平》：「食神太过，化为伤官，好逸恶劳」")

    # ── 19. 印星重重 ──
    # 来源：《渊海子平》"印多则愚，依赖性强"
    yin_count_all = sum(1 for p in pillars_data if "印" in (p.get("ten_god") or ""))
    yin_count_all += sum(1 for p in pillars_data for h in p.get("hidden_ten_gods", []) if "印" in h)
    if yin_count_all >= 3:
        combos.append(f"印星重重（{yin_count_all}个）→ 若为喜用则学富五车；若为忌则印多则愚，依赖性强缺乏主见。"
                      "《渊海子平》：「印多则愚，依赖性强」")

    # ── 20. 食伤泄秀太过 ──
    # 来源：《渊海子平》"食伤泄身太过，精神外驰"
    shishang_count_all = sum(1 for p in pillars_data if p.get("ten_god") in ("食神", "伤官"))
    shishang_count_all += sum(1 for p in pillars_data for h in p.get("hidden_ten_gods", []) if h in ("食神", "伤官"))
    if shishang_count_all >= 3:
        combos.append(f"食伤泄秀（{shishang_count_all}个）→ 才华外溢，表达欲强，但泄身太过则精神外驰、思虑过度。"
                      "《渊海子平》：「食伤泄秀，聪明外露；太过则华而不实」")

    # ═══ B. 干支特点 ═══

    # ── 21. 天干三朋 ──
    # 来源：《三命通会》"天干三朋，气势雄壮"
    stem_counts = {}
    for p in pillars_data:
        s = p.get("stem", "")
        if s:
            stem_counts[s] = stem_counts.get(s, 0) + 1
    for stem, cnt in stem_counts.items():
        if cnt >= 3 and stem != day_master_stem:
            combos.append(f"天干{stem}三朋（{stem}×{cnt}）→ 某一行天干成势，气势雄壮，性格偏重该行特质。"
                          "《三命通会》：「天干三朋，气势雄壮，非寻常人也」")
            break

    # ── 22. 地支三会/三合 ──
    # 来源：《三命通会》论三合三会
    all_branches = [p.get("branch", "") for p in pillars_data]
    sanhui = {"寅卯辰": "木", "巳午未": "火", "申酉戌": "金", "亥子丑": "水"}
    for chars, wx in sanhui.items():
        if all(b in all_branches for b in [chars[0], chars[1], chars[2]]):
            combos.append(f"地支{chars}三会{wx}局→ 五行{wx}成势，性格中{wx}的特质被充分放大。"
                          f"《三命通会》：三会{wx}局，一气成势，禀性专一")
            break

    # ── 23. 四库全 ──
    # 来源：《三命通会》"辰戌丑未全，格局宏大"
    siku = {"辰", "戌", "丑", "未"}
    branches_set = set(all_branches)
    if siku.issubset(branches_set):
        combos.append("辰戌丑未四库俱全→ 格局宏大，心性沉稳厚重，包容力极强。"
                      "《三命通会》：「辰戌丑未全，乃帝王之基」")
    elif len(siku & branches_set) >= 3:
        missing = siku - branches_set
        combos.append(f"四库得其三（缺{','.join(missing)}）→ 沉稳中有灵动，厚积薄发型。")

    # ── 24. 四正全 ──
    # 来源：《三命通会》"子午卯酉全，桃花旺盛"
    sizheng = {"子", "午", "卯", "酉"}
    if sizheng.issubset(branches_set):
        combos.append("子午卯酉四正俱全→ 桃花人气旺，性格鲜明，四处有缘。"
                      "《三命通会》：「子午卯酉全，桃花遍地」")

    # ── 25. 四生全 ──
    # 来源：《三命通会》"寅申巳亥全，奔波劳碌"
    sisheng = {"寅", "申", "巳", "亥"}
    if sisheng.issubset(branches_set):
        combos.append("寅申巳亥四生俱全→ 驿马逢生，好动不喜静，一生多奔波变动。"
                      "《三命通会》：「寅申巳亥全，奔波劳碌」")

    # ═══ C. 五行调候 ═══

    # ── 26. 五行缺一 ──
    # 来源：《穷通宝鉴》调候法
    all_wuxing_set = set()
    for p in pillars_data:
        all_wuxing_set.add(p.get("stem_wuxing", ""))
        all_wuxing_set.add(p.get("branch_wuxing", ""))
    all_wuxing_set.discard("")
    five = {"木", "火", "土", "金", "水"}
    missing_wx = five - all_wuxing_set
    if len(missing_wx) == 1:
        mx = list(missing_wx)[0]
        # 五行缺一的现代解读（基于经典五行特质推断，非古籍原文）：
        # 木主仁→决断/条理 火主礼→热情/社交 土主信→稳定/责任
        # 金主义→原则/执行 水主智→灵动/适应
        implications = {"木": "决断力偏弱或思维跳跃", "火": "热情不足或社交收敛",
                        "土": "稳定性或责任感偏弱", "金": "原则性或执行力偏弱",
                        "水": "灵动性或适应力偏弱"}
        combos.append(f"五行缺{mx}→ {implications.get(mx, '该行特质偏弱')}。"
                      f"《穷通宝鉴》：缺{mx}则需大运流年补足")

    # ── 27. 寒暖燥湿 ──
    # 来源：《穷通宝鉴》调候用神
    cold_branches = {"亥", "子", "丑", "寅"}  # 冬+初春
    hot_branches = {"巳", "午", "未"}          # 夏
    n_cold = sum(1 for b in all_branches if b in cold_branches)
    n_hot = sum(1 for b in all_branches if b in hot_branches)
    if n_cold >= 3:
        combos.append(f"命局偏寒（{n_cold}个寒支）→ 性格偏内敛保守，喜火暖局。"
                      "《穷通宝鉴》：金水伤官喜见官，寒局需火调候")
    elif n_hot >= 3:
        combos.append(f"命局偏燥（{n_hot}个暖支）→ 性格偏急躁热烈，喜水润局。"
                      "《穷通宝鉴》：火土燥烈，需水润泽方能成器")

    # ── 28. 水火既济 ──
    # 来源：《滴天髓》"水火既济，文明之象"
    n_shui = sum(1 for p in pillars_data if p.get("stem_wuxing") == "水" or p.get("branch_wuxing") == "水")
    n_huo = sum(1 for p in pillars_data if p.get("stem_wuxing") == "火" or p.get("branch_wuxing") == "火")
    if n_shui >= 2 and n_huo >= 2 and abs(n_shui - n_huo) <= 1:
        combos.append("水火既济→ 智慧与热情并重，思维活跃且行动有力。"
                      "《滴天髓》：「水火既济，文明之象」")

    # ── 29. 金水相涵 ──
    if day_master_wuxing in ("金", "水") and n_shui >= 2:
        jin_count_wx = sum(1 for p in pillars_data if p.get("stem_wuxing") == "金" or p.get("branch_wuxing") == "金")
        if jin_count_wx >= 2:
            combos.append("金水相涵→ 聪明灵秀，思维缜密，有知性美。"
                          "《滴天髓》：「金水相涵，秀气内敛」")

    # ═══ D. 特殊格局 ═══

    # ── 30-34. 专旺格（五行各一）──
    # 来源：《渊海子平》外十八格 + 《三命通会》专旺五格
    zhuanwang_check = {"寅卯辰": ("曲直格（木专旺）", "木", "仁慈正直，坚韧不拔"),
                       "巳午未": ("炎上格（火专旺）", "火", "热情奔放，磊落光明"),
                       "申酉戌": ("从革格（金专旺）", "金", "刚毅果断，义薄云天"),
                       "亥子丑": ("润下格（水专旺）", "水", "智慧深广，度量宽宏")}
    # 专旺需地支成会局 + 日主五行匹配
    for sanhui_str, (ge_name, wx_, desc_) in zhuanwang_check.items():
        chars = [sanhui_str[0], sanhui_str[1], sanhui_str[2]]
        if all(b in all_branches for b in chars) and day_master_wuxing == wx_:
            combos.append(f"{ge_name}→ {desc_}，五行{wx_}极致纯粹，意志坚定不妥协。"
                          f"《渊海子平》：{ge_name}，外十八格之一")
            break

    # 辰戌丑未全 + 日主土 = 稼穑格
    if siku.issubset(branches_set) and day_master_wuxing == "土":
        # 避免重复（已在上面的四库全中检测）
        if not any("稼穑格" in c for c in combos):
            combos.append("稼穑格（土专旺）→ 稳重诚信，敦厚至诚，如大地承载万物。"
                          "《渊海子平》：稼穑格，外十八格之一")

    # ── 35-37. 从格检测 ──
    # 来源：《渊海子平》"弃命从财/从杀"
    # 从格需要日主极弱（分数很低），此处做轻量检测
    cai_tougan_count = sum(1 for p in pillars_data if "财" in (p.get("ten_god") or "") and p.get("source") == "stem")
    sha_tougan_count = sum(1 for p in pillars_data if p.get("ten_god") in ("偏官", "七杀") and p.get("source") == "stem")
    shishang_tougan_count = sum(1 for p in pillars_data if p.get("ten_god") in ("食神", "伤官") and p.get("source") == "stem")
    if cai_tougan_count >= 2 and cai_count_all >= 4:
        combos.append("财星成势（透干2+，全局4+）→ 若日主极弱，可能为从财格，重物质善经营。"
                      "《渊海子平》：「弃命从财，须财星成势」")
    if sha_tougan_count >= 2:
        combos.append("七杀成势（透干2+）→ 若日主极弱无根，可能为从杀格，依附强者而贵。"
                      "《渊海子平》：「舍命从杀，须杀星当令」")
    if shishang_tougan_count >= 2 and shishang_count_all >= 4:
        combos.append("食伤成势（透干2+，全局4+）→ 若日主极弱无根，可能为从儿格，才华横溢自由不羁。"
                      "《滴天髓》：「从儿不论身强弱」")

    # ── 38. 金神格 ──
    # 来源：《三命通会》"金神入格，贵显"
    jin_shen_days = {"乙丑", "己巳", "癸酉"}
    day_pillar_str = f"{pillars_data[2].get('stem', '')}{pillars_data[2].get('branch', '')}" if len(pillars_data) > 2 else ""
    if day_pillar_str in jin_shen_days:
        combos.append(f"金神格（{day_pillar_str}日）→ 性格刚强执拗，有成大事的潜质，破而后立。"
                      "《三命通会》：「金神入格，非富即贵」")

    # ── 39. 魁罡格 ──
    # 来源：《三命通会》"魁罡入命，刚强果断"
    kuigang_days = {"庚辰", "庚戌", "壬辰", "戊戌"}
    if day_pillar_str in kuigang_days:
        combos.append(f"魁罡入命（{day_pillar_str}日）→ 刚强果断，不惧权威，宁折不弯，天生反骨。"
                      "《三命通会》：「魁罡者，刚毅果断，不畏强权」")

    # ── 40. 日德格 ──
    # 来源：《三命通会》"日德者，五阳干坐禄"
    ride_days = {"甲寅", "丙辰", "戊辰", "庚辰", "壬戌"}
    if day_pillar_str in ride_days:
        combos.append(f"日德格（{day_pillar_str}日）→ 品性纯良，为人正直，有仁德之心。"
                      "《三命通会》：「日德者，五阳干坐禄，主仁慈」")

    # ── 41. 日贵格 ──
    # 来源：《三命通会》"日贵者，丁酉/丁亥/癸巳/癸卯"
    rigui_days = {"丁酉", "丁亥", "癸巳", "癸卯"}
    if day_pillar_str in rigui_days:
        combos.append(f"日贵格（{day_pillar_str}日）→ 有贵气，举止得体，受人尊敬，自带贵人运。"
                      "《三命通会》：「日贵者，贵人聚于日，主得人敬重」")

    # ═══ E. 神煞人格 ═══

    # ── 42. 天乙贵人 ──
    # 来源：《三命通会》"天乙贵人，逢凶化吉"
    tianyi_map = {
        "甲": "丑未", "乙": "子申", "丙": "亥酉", "丁": "亥酉",
        "戊": "丑未", "己": "子申", "庚": "丑未", "辛": "午寅",
        "壬": "卯巳", "癸": "卯巳",
    }
    tianyi_branches = tianyi_map.get(day_master_stem, "")
    for b in tianyi_branches:
        if _has_branch_in_pillars(b, pillars_data):
            combos.append(f"天乙贵人（{b}）入命→ 自带贵人运，遇难呈祥，为人有贵气。"
                          "《三命通会》：「天乙贵人，逢凶化吉，遇难成祥」")
            break

    # ── 43. 文昌入命 ──
    # 来源：《渊海子平》文昌星
    wenchang_map = {
        "甲": "巳", "乙": "午", "丙": "申", "丁": "酉", "戊": "申",
        "己": "酉", "庚": "亥", "辛": "子", "壬": "寅", "癸": "卯",
    }
    wc = wenchang_map.get(day_master_stem, "")
    if wc and _has_branch_in_pillars(wc, pillars_data):
        combos.append(f"文昌入命（{wc}）→ 好学善思，有学术天赋，考试运佳。"
                      "《渊海子平》：文昌主学业、文书、考试之事")

    # ── 44. 驿马逢冲 ──
    # 来源：《三命通会》驿马
    yima_map = {
        "申": "寅", "子": "寅", "辰": "寅",
        "亥": "巳", "卯": "巳", "未": "巳",
        "寅": "申", "午": "申", "戌": "申",
        "巳": "亥", "酉": "亥", "丑": "亥",
    }
    yima = yima_map.get(day_branch, "")
    if yima and _has_branch_in_pillars(yima, pillars_data):
        # 驿马是否被冲
        yima_chong = False
        for inter in interactions.get("dizhi", []):
            if inter["type"] == "六冲":
                for p_name in inter.get("pillars", []):
                    p_idx = {"年柱": 0, "月柱": 1, "日柱": 2, "时柱": 3}.get(p_name, -1)
                    if p_idx >= 0 and p_idx < len(pillars_data) and pillars_data[p_idx].get("branch") == yima:
                        yima_chong = True
                        break
        if yima_chong:
            combos.append(f"驿马逢冲（{yima}被冲）→ 好动不喜静，奔波劳碌，异地发展或频繁差旅。"
                          "《三命通会》：「驿马逢冲，奔波劳碌」")
        else:
            combos.append(f"驿马入命（{yima}）→ 好动不喜静，喜变换环境，适合流动性职业。"
                          "《三命通会》：「驿马主奔波，不甘现状」")

    # ── 45. 羊刃重重 ──
    # 来源：《渊海子平》"羊刃重重，性格刚烈"
    yr = _yangren_branch(day_master_stem)
    yr_count = sum(1 for p in pillars_data if p.get("branch") == yr)
    if yr_count >= 2:
        combos.append(f"羊刃重重（{yr}×{yr_count}）→ 性格刚烈，不服管束，执行力极强但也易与人冲突。"
                      "《渊海子平》：「羊刃重重，克妻刑子，性格刚烈」")

    # ── 46-47. 孤辰寡宿 ──
    # 来源：《三命通会》孤辰寡宿
    guchen_map = {
        "寅": "巳", "卯": "巳", "辰": "巳",
        "巳": "申", "午": "申", "未": "申",
        "申": "亥", "酉": "亥", "戌": "亥",
        "亥": "寅", "子": "寅", "丑": "寅",
    }
    guasu_map = {
        "寅": "丑", "卯": "丑", "辰": "丑",
        "巳": "辰", "午": "辰", "未": "辰",
        "申": "未", "酉": "未", "戌": "未",
        "亥": "戌", "子": "戌", "丑": "戌",
    }
    gc = guchen_map.get(day_branch, "")
    gs = guasu_map.get(day_branch, "")
    has_gc = gc and _has_branch_in_pillars(gc, pillars_data)
    has_gs = gs and _has_branch_in_pillars(gs, pillars_data)
    if has_gc and has_gs:
        combos.append("孤辰寡宿同现→ 内心孤独感较强，亲情缘薄，但独立性强。"
                      "《三命通会》：「孤辰寡宿，主孤独独立」")
    elif has_gc:
        combos.append("孤辰入命→ 独立性较强，男性更明显，不喜依靠他人。"
                      "《三命通会》：「孤辰者，独立自主，不喜羁绊」")
    elif has_gs:
        combos.append("寡宿入命→ 喜独处，女性更明显，有自己的小世界。"
                      "《三命通会》：「寡宿者，好静恶喧，独善其身」")

    # ── 48. 阴阳差错 ──
    # 来源：《三命通会》"阴阳差错，婚姻不遂"
    yinyang_chacuo_days = {"丙子", "丁丑", "戊寅", "辛卯", "壬辰", "癸巳",
                           "丙午", "丁未", "戊申", "辛酉", "壬戌", "癸亥"}
    if day_pillar_str in yinyang_chacuo_days:
        combos.append(f"阴阳差错日（{day_pillar_str}）→ 感情婚姻易波折，好事多磨，需经营。"
                      "《三命通会》：「阴阳差错，婚姻不遂，好事多磨」")

    # ── 49. 天罗地网 ──
    # 来源：《三命通会》"辰巳为天罗，戌亥为地网"
    tianluo = {"辰", "巳"}
    diwang = {"戌", "亥"}
    has_tl = bool(tianluo & branches_set)
    has_dw = bool(diwang & branches_set)
    if has_tl and has_dw:
        combos.append("天罗地网（辰巳+戌亥）入命→ 人生多困顿，破网则大成，意志坚韧。"
                      "《三命通会》：「天罗地网，主困顿，破网则为贵人」")

    return combos

