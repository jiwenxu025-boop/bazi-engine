"""八字性格分析与家境分析引擎

基于《滴天髓》《渊海子平》《穷通宝鉴》《三命通会》原文规则。
每条规则标注来源，实战校准数据标注案例编号。

集成方式：import 后调用 analyze_personality() 和 analyze_family()
"""

from dataclasses import dataclass, field
from .enums import Tiangan, Dizhi, Wuxing


# ═══════════════════════════════════════════════════════════════
# 数据类
# ═══════════════════════════════════════════════════════════════

@dataclass
class PersonalityResult:
    """性格分析结果"""
    day_master_core: str = ""           # 日干核心性格
    strength_label: str = ""            # 身强弱描述
    dominant_ten_god: str = ""          # 最旺十神及其影响
    pattern_influence: str = ""         # 格局对性格的影响
    special_combos: list[str] = field(default_factory=list)  # 特殊组合
    traits: dict = field(default_factory=dict)  # {领域: 描述}
    profile: str = ""                   # 综合性格画像
    stress_profile: dict | None = None  # 抗压画像 (v0.10.0: 三引擎)

    def to_dict(self) -> dict:
        return {
            "day_master_core": self.day_master_core,
            "strength_label": self.strength_label,
            "dominant_ten_god": self.dominant_ten_god,
            "pattern_influence": self.pattern_influence,
            "special_combos": self.special_combos,
            "traits": self.traits,
            "profile": self.profile,
            "stress_profile": self.stress_profile,
        }


@dataclass
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


# ═══════════════════════════════════════════════════════════════
# 性格分析
# ═══════════════════════════════════════════════════════════════

# 日干核心性格表（来源：《滴天髓》原文 + 《穷通宝鉴》实物意象）
# 验证日期: 2026-05-24, 来源: personality-rules.md
DAY_MASTER_PERSONALITY = {
    "甲": {
        "core": "正直刚强，上进心强，仁慈有责任感，领袖风范，如参天大树顶天立地",
        "negative": "固执不灵活，强行干涉他人，自负好大",
        "image": "栋梁之木",
        "key": "甲不离庚——需挫折砥砺方成栋梁。最佳组合：甲+庚+丁",
        "wude": "木主仁，恻隐之心，恬静清高。太过则折，执拗性偏",
    },
    "乙": {
        "core": "温和柔巧，灵活变通，适应性强，韧性十足，善于借力依附强者",
        "negative": "敏感多疑，三心二意，缺乏主见，有心机",
        "image": "藤萝花草",
        "key": "藤萝系甲——依附强者方得长青。喜丙丁火制杀，喜甲木为靠",
        "wude": "木主仁（偏柔），恻隐之心，人物清秀",
    },
    "丙": {
        "core": "热情外扬，光明磊落，不畏强权，如太阳普照四方",
        "negative": "性急莽撞，不擅收敛，过于张扬，急躁骄傲",
        "image": "太阳之火",
        "key": "逢辛反怯——丙辛合化水，英雄难过美人关。壬水辅丙方显光芒",
        "wude": "火主礼，辞让恭敬，言语辞急，意速心焦。太过则性躁",
    },
    "丁": {
        "core": "敏锐细腻，外柔内刚，忠诚持久，如灯烛之光绵延不绝",
        "negative": "多愁善感，过于细腻",
        "image": "灯烛之光",
        "key": "旺而不烈，衰而不穷——持久力强。需甲木为燃料方可长明",
        "wude": "火主礼（偏柔），文明之象，内心有锋芒",
    },
    "戊": {
        "core": "厚重信实，沉稳可靠，诚实守信，如高山城墙不可撼动",
        "negative": "固执保守，缺乏灵活性，过于沉稳变通不足",
        "image": "城墙高山",
        "key": "怕冲宜静——寅申冲/辰戌冲则惹事。需水润+木疏",
        "wude": "土主信，敦厚至诚，度量宽厚。太过则愚朴固执",
    },
    "己": {
        "core": "包容力强，善于调和，恋家重情，是天生的和事佬",
        "negative": "多虑阴湿，易纠结，缺乏决断",
        "image": "田园湿土",
        "key": "不愁木盛不畏水狂——抗压包容。能晦火润金，滋养万物",
        "wude": "土主信（偏柔），敦厚包容，重情义",
    },
    "庚": {
        "core": "果断刚硬，执行力强，讲义气，原则性强不妥协，如刀斧般锋利",
        "negative": "不善变通，易刚直伤人，内心急躁，有攻击性",
        "image": "刀斧顽铁",
        "key": "庚不离丁——需丁火锻炼方成利器。最佳组合：庚+丁+甲",
        "wude": "金主义，仗义疏财，刚毅有决。太过则好斗贪欲",
    },
    "辛": {
        "core": "精致锐利，追求完美，细腻有审美，有商业头脑",
        "negative": "多愁善感，娇气挑剔，过于注重细节",
        "image": "珠玉首饰",
        "key": "怕土多被埋——才华需展现平台。喜水淘洗显光泽",
        "wude": "金主义（偏柔），精致秀气，自尊心强",
    },
    "壬": {
        "core": "聪明灵活，志向远大，行动力强，善交际豪放，如江河奔腾不息",
        "negative": "过旺则如洪水泛滥，难以约束，行事太任性",
        "image": "江河湖海",
        "key": "刚中之德，周流不滞——流动性强，适应各种环境",
        "wude": "水主智，足智多谋，机关深远。太过则诡诈狠戾",
    },
    "癸": {
        "core": "内敛深沉，聪慧敏感，观察入微，心思缜密，适应力极强",
        "negative": "多心眼，城府较深，过于隐忍",
        "image": "雨露溪流",
        "key": "至阴至柔，渗透力极强——以柔克刚。遇戊合化火则被降服",
        "wude": "水主智（偏柔），直觉力强，第六感敏锐",
    },
}

# 格局性格表（双面：喜用面 / 忌神面）
# 来源：《渊海子平》+《三命通会》，修正：现实校验
PATTERN_PERSONALITY = {
    "正官格": {
        "喜用": "正直负责、有原则有底线，适合需要公信力的工作",
        "忌神": "保守刻板、压力大不敢越雷池，被规则束缚了自己",
    },
    "七杀格": {
        "喜用": "果断有魄力、敢拼敢闯、有领导力，适合竞争型行业",
        "忌神": "叛逆好斗、容易被针对、人际关系紧张、压力伤身",
    },
    "正印格": {
        "喜用": "温和有礼、有学习天赋、内心有独立精神世界",
        "忌神": "学习需要自发驱动，被动灌输无效；依赖性强、缺乏主动性",
    },
    "偏印格": {
        "喜用": "思维独特，善于钻研冷门领域，专业深度可以弥补人缘不足",
        "忌神": "孤僻冷漠、不合群、人情味薄、容易自我封闭",
    },
    "食神格": {
        "喜用": "温和宽厚、有才华懂享受、人缘好、适合创意审美类工作",
        "忌神": "好逸恶劳、理想空想、博而不精、缺乏执行力",
    },
    "伤官格": {
        "喜用": "才华横溢、不拘一格、创造力强、口才出众",
        "忌神": "桀骜不驯、受不了约束、容易得罪人、不适合体制内",
    },
    "正财格": {
        "喜用": "务实稳重、对钱敏感、适合需要耐心积累的职业",
        "忌神": "过于抠门、只看眼前利益、缺乏冒险精神",
    },
    "偏财格": {
        "喜用": "有商业头脑、善于捕捉机会、人缘广、财运起伏中求胜",
        "忌神": "投机心强、大手大脚、容易因财惹事",
    },
    "建禄格": {
        "喜用": "独立自主、靠自己的本事吃饭、有创业基因",
        "忌神": "不喜约束、难与人合作、容易单打独斗",
    },
    "羊刃格": {
        "喜用": "刚强果断、执行力极强、能成大事",
        "忌神": "过于激进、容易冲动伤人、赚快钱亏大钱",
    },
}

# 十神性格表（来源：《渊海子平》论性情 + 十神性情体系）
SHISHEN_PERSONALITY = {
    "正印": ("仁慈宽厚，爱读书思考，淡泊名利，有爱心与包容",
             "懒散依赖，缺乏主见，好面子，保守不进取"),
    "偏印": ("精明干练，逻辑思维强，善于创新与偏门学问，洞察力强",
             "孤独冷漠，自私多疑，人情味薄，有城府心机"),
    "正官": ("正直负责，循规蹈矩，光明磊落，自制力强，重名誉",
             "刻板保守，胆小怕事，优柔寡断，心理压力大"),
    "偏官": ("豪爽侠义，有胆略魄力，敢做敢为，精明果断，有领导力",
             "偏激叛逆，霸道残酷，急躁好斗，报复心强"),
    "七杀": ("豪爽侠义，有胆略魄力，敢做敢为，精明果断，有领导力",
             "偏激叛逆，霸道残酷，急躁好斗，报复心强"),
    "食神": ("温和宽厚，心宽体胖，有口福，乐观有人缘，有艺术审美力",
             "好逸恶劳，理想空想，兴趣广泛但博而不精"),
    "伤官": ("聪明绝顶，才华横溢，多才多艺，创造力强，口才出众",
             "桀骜不驯，任性放肆，争强好胜，尖酸刻薄"),
    "正财": ("勤劳节俭，踏实可靠，擅长理财，对家庭负责，重视结发之情",
             "吝啬小气，过于重利，缺乏进取，懦弱无能"),
    "偏财": ("慷慨大方，有商业头脑，乐观开朗，善于把握机会，人缘好",
             "虚浮奢侈，好色风流，用情不专，投机心强"),
    "比肩": ("稳健刚毅，意志坚定，重情义，有主见不摇摆",
             "孤僻固执，自尊过强，与家人关系需用心经营，不善合作"),
    "劫财": ("热诚坦直，坚韧不拔，讲义气，奋斗不屈",
             "盲目冲动，蛮横霸道，好色贪财，惹是生非"),
}


def _count_ten_gods(pillars_data: list[dict]) -> dict[str, dict]:
    """统计每个十神出现次数、是否透干、宫位分布"""
    counts: dict[str, dict] = {}
    for p in pillars_data:
        tg_name = p.get("ten_god")
        if tg_name is None:
            continue
        if tg_name not in counts:
            counts[tg_name] = {"count": 0, "tougan": False, "pillars": []}
        counts[tg_name]["count"] += 1
        counts[tg_name]["pillars"].append(p["pillar_type"])
        if p.get("source") == "stem":
            counts[tg_name]["tougan"] = True
    return counts


def _get_hidden_ten_gods_flat(pillars_data: list[dict]) -> list[str]:
    """提取所有藏干十神（扁平列表）"""
    result = []
    for p in pillars_data:
        for hs_name in p.get("hidden_ten_gods", []):
            result.append(hs_name)
    return result


def _find_dominant_shishen(pillars_data: list[dict],
                           harmful_shishen: list[str]) -> tuple[str, bool, str]:
    """找出最旺十神，返回 (十神名, 是否喜用, 性格描述)"""
    all_counts: dict[str, int] = {}
    tougan_set: set[str] = set()
    for p in pillars_data:
        tg_name = p.get("ten_god")
        if tg_name:
            all_counts[tg_name] = all_counts.get(tg_name, 0) + 1
            if p.get("source") == "stem":
                tougan_set.add(tg_name)
        for hs_name in p.get("hidden_ten_gods", []):
            all_counts[hs_name] = all_counts.get(hs_name, 0) + 1

    if not all_counts:
        return ("", True, "")

    candidates = [(n, c, n in tougan_set) for n, c in all_counts.items()]
    candidates.sort(key=lambda x: (x[2], x[1]), reverse=True)
    dominant = candidates[0][0]

    is_fav = dominant not in harmful_shishen

    personality_entry = SHISHEN_PERSONALITY.get(dominant)
    if personality_entry:
        desc = personality_entry[0] if is_fav else personality_entry[1]
    else:
        desc = ""

    return (dominant, is_fav, desc)


# ── 辅助: 神煞本地计算（避免依赖 spirits 模块）──

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
    stem_counts: dict[str, int] = {}
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
        combos.append(f"孤辰入命→ 独立性较强，男性更明显，不喜依靠他人。"
                      "《三命通会》：「孤辰者，独立自主，不喜羁绊」")
    elif has_gs:
        combos.append(f"寡宿入命→ 喜独处，女性更明显，有自己的小世界。"
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


def analyze_personality(
    day_master_stem: str,
    day_master_wuxing: str,
    day_master_yinyang: str,
    pattern: str,
    strength: str,
    score: float,
    favorable_shishen: list[str],
    harmful_shishen: list[str],
    pillars_data: list[dict],
    interactions: dict,
    gender: str,
) -> PersonalityResult:
    """分析性格

    Args:
        pillars_data: [{pillar_type, stem, branch, ten_god, source, hidden_stems, hidden_ten_gods}, ...]
        interactions: {"tiangan": [...], "dizhi": [...]}
    """
    result = PersonalityResult()

    # ── Step 1: 日干核心性格 ──
    dm_info = DAY_MASTER_PERSONALITY.get(day_master_stem)
    if dm_info:
        result.day_master_core = (
            f"日干{day_master_stem}（{day_master_wuxing}·{day_master_yinyang}）——{dm_info['image']}。\n"
            f"核心：{dm_info['core']}。\n"
            f"注意：{dm_info['negative']}。\n"
            f"特点：{dm_info['key']}。\n"
            f"五德：{dm_info['wude']}。"
        )
    else:
        result.day_master_core = f"日干{day_master_stem}（{day_master_wuxing}·{day_master_yinyang}）"

    # ── Step 2: 身强弱调节 ──
    if "强" in strength:
        result.strength_label = f"身{strength}（{score}分）→ 自信果断，抗压能力强，能担财官，日干正面特征充分展现"
    elif "弱" in strength:
        result.strength_label = f"身{strength}（{score}分）→ 优柔寡断，依赖性强，压力敏感，日干负面特征更明显"
    else:
        result.strength_label = f"身{strength}（{score}分）→ 中和状态，性格特征表现适中"

    # ── Step 3: 最旺十神 ──
    dominant, is_fav, shishen_desc = _find_dominant_shishen(pillars_data, harmful_shishen)
    if dominant:
        fav_label = "喜用" if is_fav else "忌神"
        result.dominant_ten_god = (
            f"最旺十神：{dominant}（{fav_label}）→ {shishen_desc}"
        )

    # ── Step 4: 格局定基调（双面：喜用/忌神）──
    for key, sides in PATTERN_PERSONALITY.items():
        if key in pattern:
            # 判断格局是喜用还是忌神
            pattern_is_fav = key not in harmful_shishen if harmful_shishen else True
            side = "喜用" if pattern_is_fav else "忌神"
            desc = sides.get(side, sides.get("喜用", ""))
            label = "喜用面" if pattern_is_fav else "忌神面（需注意）"
            result.pattern_influence = f"格局{pattern}（{label}）→ {desc}"
            break
    if not result.pattern_influence:
        result.pattern_influence = f"格局{pattern}"

    # ── Step 5: 特殊组合 ──
    result.special_combos = _check_special_combos(
        day_master_stem, day_master_wuxing,
        pillars_data, interactions, gender,
        harmful_shishen, pattern,
    )

    # ── Step 6: 分领域性格（6维度，每维5+分支，标注出处）──

    dm_core = dm_info["core"] if dm_info else ""
    dm_neg = dm_info["negative"] if dm_info else ""
    is_strong = "强" in strength
    is_weak = "弱" in strength

    # 预计算常用判断
    all_tg_names_set = set(p.get("ten_god", "") for p in pillars_data)
    all_hidden_tg_set = set()
    for p in pillars_data:
        for h in p.get("hidden_ten_gods", []):
            all_hidden_tg_set.add(h)
    all_names_combined = all_tg_names_set | all_hidden_tg_set

    has_shishang = "食神" in all_names_combined or "伤官" in all_names_combined
    has_yin = "正印" in favorable_shishen or "偏印" in favorable_shishen or "正印" in harmful_shishen or "偏印" in harmful_shishen
    has_cai_star = any("财" in (p.get("ten_god") or "") for p in pillars_data)
    has_guan_star = any(("官" in (p.get("ten_god") or "") or "杀" in (p.get("ten_god") or "")) for p in pillars_data)
    bijie_count = sum(1 for p in pillars_data
                      if p.get("ten_god") in ("比肩", "劫财"))
    yin_count = sum(1 for p in pillars_data
                    if p.get("ten_god") in ("正印", "偏印"))
    day_branch = pillars_data[2].get("branch", "") if len(pillars_data) > 2 else ""

    # 检查日支是否被冲/合
    day_branch_chong = False
    day_branch_he = False
    for inter in interactions.get("dizhi", []):
        if "日柱" in inter.get("pillars", []):
            if inter["type"] == "六冲":
                day_branch_chong = True
            elif inter["type"] in ("六合", "三合", "半合"):
                day_branch_he = True

    # 检查正偏财/官混杂
    zhengcai_stems = sum(1 for p in pillars_data if p.get("ten_god") == "正财" and p.get("source") == "stem")
    piancai_stems = sum(1 for p in pillars_data if p.get("ten_god") == "偏财" and p.get("source") == "stem")
    zhengguan_stems = sum(1 for p in pillars_data if p.get("ten_god") == "正官" and p.get("source") == "stem")
    pianguan_stems = sum(1 for p in pillars_data if p.get("ten_god") in ("偏官", "七杀") and p.get("source") == "stem")
    cai_hunza = zhengcai_stems > 0 and piancai_stems > 0
    guan_hunza = zhengguan_stems > 0 and pianguan_stems > 0

    # 伤官见官（含藏干）
    shang_jian_guan = ("伤官" in all_names_combined and "正官" in all_names_combined)

    # 七杀有制
    qisha_youzhi = any("食神制七杀" in c for c in result.special_combos)

    # 华盖
    day_branch_str = day_branch
    has_huagai = bool(_huagai_branch(day_branch_str)) and \
                 _has_branch_in_pillars(_huagai_branch(day_branch_str), pillars_data)

    # 桃花在日支
    taohua = _taohua_branch(day_branch_str)
    has_taohua_rizhi = taohua is not None and any(
        p.get("branch") == taohua and p.get("pillar_type") == "日柱"
        for p in pillars_data
    )

    # 比劫多（3+）
    bijie_duo = bijie_count >= 3

    # 财破印
    cai_po_yin = any("财破印" in c for c in result.special_combos)

    # --- 社交 (6 branches) ---
    # 来源：《滴天髓》十天干性情 + 《渊海子平》十神性情
    if is_strong and has_shishang and day_master_stem in ("壬", "丙", "甲", "庚"):
        # 阳干+食伤社交风格（按五行）
        wx_social_flavors_1 = {
            "水": "如江河豪客，口才出众，朋友遍天下，社交场合如鱼得水",
            "火": "如太阳普照，热情感染四方，走到哪都是焦点",
            "木": "如参天大树，正直可靠，人缘好而不轻浮",
            "金": "如刀剑出鞘，话语有分量，在朋友中自然成为核心",
        }
        wx_f1 = wx_social_flavors_1.get(day_master_wuxing,
                                         "热情开朗，口才出众，社交场合如鱼得水")
        result.traits["社交"] = (
            f"日干{day_master_stem}身强+食伤吐秀→ {wx_f1}。"
            f"《滴天髓》：{day_master_stem}主动外向，食伤泄其精华，人情练达"
        )
    elif is_strong and has_shishang:
        # 按日干五行给出不同的社交风格
        wx_social_flavors = {
            "水": "如江河流淌，话题不断，轻松融入各种圈子",
            "火": "如火焰般温暖明亮，热情感染身边人",
            "木": "如春风拂面，正直温和，人缘自然来",
            "金": "如金石掷地，话语有分量，朋友敬重多于亲近",
            "土": "如大地承载，稳重可靠，慢热但深交持久",
        }
        wx_flavor = wx_social_flavors.get(day_master_wuxing, "善于表达，有亲和力")
        result.traits["社交"] = (
            f"日干{day_master_stem}身强+食伤旺→ {wx_flavor}。"
            "《渊海子平》：食伤旺者善言辞，通人情"
        )
    elif is_strong and has_guan_star and "正官" in [p.get("ten_god") for p in pillars_data]:
        result.traits["社交"] = (
            f"身强+正官在柱→ 社交得体大方，有分寸感，不卑不亢，给人可靠印象。"
            "《渊海子平》：正官者，礼节仪表，不怒自威"
        )
    elif is_strong:
        result.traits["社交"] = (
            f"日干{day_master_stem}身强→ 自信外向，主动社交，人缘不错但交友有选择性。"
        )
    elif has_yin and yin_count >= 2:
        result.traits["社交"] = (
            f"印星旺（{yin_count}个）→ 温和内敛，深交不多但真诚持久，喜安静不喜喧闹。"
            "《渊海子平》：印多者寡言，不喜喧哗"
        )
    else:
        result.traits["社交"] = (
            f"身{strength}→ 社交偏内向，不擅大场合，但小圈子中放得开。"
            "《穷通宝鉴》：弱者内向藏锋，非不能交，视对象而定"
        )

    # --- 感情 (6 branches) ---
    # 来源：《渊海子平》论妻妾 + 《三命通会》论夫妻宫
    has_passive_combo = any("合身" in c for c in result.special_combos)

    if day_branch_chong:
        chong_desc = ""
        for inter in interactions.get("dizhi", []):
            if "日柱" in inter.get("pillars", []) and inter["type"] == "六冲":
                other = [p for p in inter["pillars"] if p != "日柱"]
                chong_desc = f"（日支被{'/'.join(other)}冲）"
                break
        result.traits["感情"] = (
            f"日支（夫妻宫）被冲{chong_desc}→ 感情波动较大，晚婚倾向，需经历磨合方稳定。"
            "《三命通会》：夫妻宫逢冲，婚姻多变，宜晚婚"
        )
    elif day_branch_he:
        result.traits["感情"] = (
            f"日支（夫妻宫）被合→ 配偶缘好，但也易受外界影响，须防第三者介入。"
            "《三命通会》：夫妻宫逢合，姻缘早定但须防争合"
        )
    elif has_passive_combo:
        result.traits["感情"] = (
            "正财/正官合身→ 感情中偏被动，被选择多于主动选择，等待对方推进。"
            "《渊海子平》：合身者被动，待人之求"
        )
    elif ("七杀" in (dominant or "") or "偏官" in (dominant or "")) and is_strong:
        result.traits["感情"] = (
            "七杀旺+身强→ 感情中主动追求，敢爱敢恨，但也容易因强势引发摩擦。"
            "《渊海子平》：七杀主冲动，爱憎分明"
        )
    elif cai_hunza or guan_hunza:
        hun_desc = "正偏财混杂" if cai_hunza else "官杀混杂"
        result.traits["感情"] = (
            f"{hun_desc}→ 感情选择多，易纠结，须明辨真心与诱惑。"
            "《渊海子平》：财官混杂，情路多岐"
        )
    elif has_taohua_rizhi:
        result.traits["感情"] = (
            f"桃花坐日支→ 配偶颜值高，自身异性缘好，感情经历丰富。"
            "《渊海子平》：桃花在日，妻美夫俊"
        )
    else:
        # 基于日支藏干给出个性化描述
        day_hidden = pillars_data[2].get("hidden_ten_gods", []) if len(pillars_data) > 2 else []
        if day_hidden:
            hs_desc = "、".join(day_hidden[:2])
            result.traits["感情"] = (
                f"夫妻宫藏{hs_desc}→ 感情模式受夫妻宫十神影响，"
                f"具体取决于流年桃花引动。{'藏官杀，重责任感' if any('官' in h or '杀' in h for h in day_hidden) else '藏食伤/财星，感情表达较自然'}"
            )
        else:
            result.traits["感情"] = "夫妻宫清纯→ 感情取向明确，不拖泥带水"

    # --- 决策/行事 (6 branches) ---
    # 来源：《渊海子平》论七杀/伤官/印星 + 《滴天髓》
    if qisha_youzhi and shang_jian_guan:
        result.traits["决策"] = (
            "食神制杀+伤官见官→ 既有谋略又敢打破常规，智勇双全且不拘一格，行事出人意表但结果往往漂亮。"
            "《渊海子平》：制杀化权配伤官之奇，非常人也"
        )
    elif qisha_youzhi:
        result.traits["决策"] = (
            "食神制杀→ 胆识谋略兼备，临危不乱，大决策时果敢而有算计，不冲动不怯懦。"
            "《渊海子平》：七杀有制化为权，智勇双全"
        )
    elif ("七杀" in (dominant or "") or "偏官" in (dominant or "")) and is_strong:
        result.traits["决策"] = (
            "身强七杀旺→ 大事果断敢为，不拖泥带水，但有时冲动欠思量。"
            "《渊海子平》：七杀主刚强，势必争先"
        )
    elif shang_jian_guan:
        result.traits["决策"] = (
            "伤官见官→ 不按常理出牌，喜走捷径，常有意外之举，不被规则束缚。"
            "《渊海子平》：伤官者，不拘常法，奇谋迭出"
        )
    elif yin_count >= 3:
        result.traits["决策"] = (
            f"印星过多（{yin_count}个）→ 决策偏保守，需反复斟酌才行动，但一旦决定就不轻易改变。"
            "《渊海子平》：印绶多者，思多行少"
        )
    elif is_strong:
        result.traits["决策"] = (
            "身强→ 有主见，决策较果断，但也会权衡利弊后再出手。"
            "行事风格稳健偏主动"
        )
    else:
        result.traits["决策"] = (
            f"身{strength}→ 决策偏保守，需收集充分信息后才行动，但深思熟虑后少有失误。"
        )

    # --- 内心 (5 branches) ---
    # 来源：《三命通会》华盖 + 《滴天髓》阴阳性情
    if "偏印" in harmful_shishen and "偏印" in pattern:
        result.traits["内心"] = (
            "偏印忌神+偏印格→ 外表自如内心疏离，社交自如但独处时沉入自己的世界，思维异于同龄人。"
            "《渊海子平》：倒食者孤僻，内心另成境界"
        )
    elif has_huagai:
        # 华盖入命，按五行给出不同倾向
        huagai_wx_flavors = {
            "木": "对哲学/生命科学有天然亲近感，喜思考生长与变化之道",
            "火": "对宗教/心灵成长/仪式感有偏向，喜灯火阑珊处的独思",
            "土": "对历史/传统/玄学有天然亲近感，沉稳中藏着对古老智慧的向往",
            "金": "对规则/逻辑/玄理有偏好，刚硬外表下有不可动摇的精神信仰",
            "水": "对玄学/神秘学/潜意识有天然亲近感，智慧深沉如渊",
        }
        wx_flavor = huagai_wx_flavors.get(day_master_wuxing, "对玄学/哲学/艺术有天然亲近感")
        result.traits["内心"] = (
            f"华盖入命→ 内心有独立的精神世界，喜独处钻研，{wx_flavor}。"
            "《三命通会》：「华盖者，主孤独清高，善思悟道」"
        )
    elif bijie_duo:
        result.traits["内心"] = (
            f"比劫多（{bijie_count}个）→ 自我意识强，重视自我感受和立场，内心不易被他人动摇。"
            "《渊海子平》：比劫多者，心志自坚"
        )
    elif cai_po_yin:
        result.traits["内心"] = (
            "财破印→ 内心现实，当理想与现实冲突时倾向于选择眼前利益，但也因此内心常有挣扎。"
            "《渊海子平》：贪财坏印，内心德行与欲望交战"
        )
    elif "印" in pattern:
        result.traits["内心"] = (
            "印星为格→ 内心安稳恬淡，重视精神修养，思虑深远，有自己的精神支撑。"
            "《渊海子平》：印绶者，内心温厚，自信不疑"
        )
    else:
        is_yang = day_master_yinyang == "阳"
        result.traits["内心"] = (
            f"日干{day_master_stem}（{'阳' if is_yang else '阴'}干）→ "
            + ("内心与外表基本一致，直率坦诚，不藏心思。" if is_yang
               else "外表温和内心有主见，外圆内方，不轻易表露真实想法。")
            + ("《滴天髓》：阳干外向表里如一，阴干内敛藏锋不露" if is_yang
               else "《滴天髓》：阴干如珠玉，光芒外露而内里暗藏锋芒")
        )

    # --- 事业倾向 (NEW, 6 branches) ---
    # 来源：《渊海子平》论格局 + 《三命通会》看命口诀
    if "正官" in pattern or "七杀" in pattern:
        if "七杀" in pattern:
            result.traits["事业"] = (
                "七杀格→ 适合竞争性行业（军警/法律/管理），挑战越大越兴奋，能扛高压。"
                "《渊海子平》：七杀主威权，掌生杀之柄"
            )
        else:
            result.traits["事业"] = (
                "正官格→ 适合体制内/大企业/稳定机构，按部就班晋升，重纪律规章。"
                "《渊海子平》：正气官星，宜仕途稳步上升"
            )
    elif "正财" in pattern or "偏财" in pattern:
        result.traits["事业"] = (
            f"{'偏财' if '偏财' in pattern else '正财'}格→ 适合商业/金融/经营类，求财导向，对数字和市场敏感。"
            "《渊海子平》：财格主经营，善于理财"
        )
    elif "食神" in pattern or "伤官" in pattern:
        result.traits["事业"] = (
            f"{'伤官' if '伤官' in pattern else '食神'}格→ 适合技术/艺术/创意领域，靠才华吃饭，不宜受太多约束。"
            "《渊海子平》：食伤格以技艺立身"
        )
    elif "正印" in pattern or "偏印" in pattern:
        result.traits["事业"] = (
            f"{'偏印' if '偏印' in pattern else '正印'}格→ 适合学术/教育/研究/文化领域，以学识立足，厚积薄发。"
            "《渊海子平》：印绶格宜文途，以学养身"
        )
    elif "建禄" in pattern or "羊刃" in pattern:
        result.traits["事业"] = (
            f"{pattern}→ 不喜为他人打工，有创业基因，靠自己的本事吃饭，独立性强。"
            "《三命通会》：建禄羊刃，自立自成"
        )
    else:
        result.traits["事业"] = (
            f"格局{pattern}→ 事业发展路径偏综合型，多领域可发展，具体看大运流年导向。"
        )

    # --- 财富观 (NEW, 6 branches) ---
    # 来源：《渊海子平》论财星 + 《三命通会》论贫富
    has_cai_tougan = any("财" in (p.get("ten_god") or "") and p.get("source") == "stem"
                         for p in pillars_data)
    bijie_duo_cai = bijie_duo and has_cai_star

    if has_cai_tougan and is_strong:
        cai_wei = "偏财" if any(p.get("ten_god") == "偏财" and p.get("source") == "stem"
                              for p in pillars_data) else "正财"
        result.traits["财富观"] = (
            f"{cai_wei}透干+身强→ 擅理财，有赚钱头脑，钱能生钱，不守死工资。"
            "《渊海子平》：财透干逢身强，财为我用"
        )
    elif has_cai_tougan and not is_strong:
        result.traits["财富观"] = (
            "财星透干但身弱→ 想赚钱但难守财，易为财所累，须先补身（增强自身实力）再求财。"
            "《渊海子平》：财多身弱，富屋贫人"
        )
    elif bijie_duo_cai:
        result.traits["财富观"] = (
            "比劫多+财星现→ 钱财易散，合伙须谨慎，适合与人合作求财而非独揽。"
            "《渊海子平》：比劫争财，财来财去，宜合伙分利"
        )
    elif cai_po_yin:
        result.traits["财富观"] = (
            "财破印→ 为钱可能牺牲原则或学业，花钱买心安，须警惕价值观漂移。"
            "《渊海子平》：贪财坏印，利令智昏"
        )
    elif not has_cai_tougan and has_cai_star:
        result.traits["财富观"] = (
            "财藏地支（不透干）→ 闷声发财型，不炫富，财不外露，实际家底比表面看起来厚。"
            "《渊海子平》：财藏地支，财帛不露"
        )
    else:
        result.traits["财富观"] = (
            "财星不显→ 对钱财不执着，够用即安，更看重工作意义和人生体验。"
            "《三命通会》：无财不贪，清贵自守"
        )

    # ── 综合画像 ──
    parts = [f"日主{day_master_stem}（{day_master_wuxing}·{day_master_yinyang}），身{strength}，{pattern}。"]
    if dm_info:
        parts.append(f"核心性格：{dm_info['core']}。")
    if dominant:
        parts.append(f"最突出十神为{dominant}（{'喜用' if is_fav else '忌神'}），{shishen_desc}。")
    if result.special_combos:
        # 挑选2-3个最重要的组合
        key_combos = result.special_combos[:3]
        parts.append("关键组合：" + "；".join(c.split("→")[0] for c in key_combos) + "。")
    parts.append(f"社交{'外向开放' if is_strong else '偏内向收敛'}，"
                 f"决策{'果断' if is_strong else '审慎'}，"
                 f"事业{'求稳' if '官' in pattern or '印' in pattern else '求变' if '杀' in pattern or '伤' in pattern else '平衡'}。")
    result.profile = "".join(parts)

    # ── Step 7: 现实校验 —— 检测矛盾、修正套路化判断 ──
    _apply_reality_check(result, day_master_stem, day_master_wuxing, strength, score,
                         pattern, pillars_data, interactions, gender,
                         harmful_shishen, favorable_shishen)

    # ── v0.10.0: 抗压心理画像（三引擎）──
    result.stress_profile = analyze_stress_profile(
        favorable_shishen=favorable_shishen,
        harmful_shishen=harmful_shishen,
        strength=strength,
        pattern=pattern,
        gender=gender,
        pillars_data=pillars_data,
        special_combos=result.special_combos,
    )

    return result


# ═══════════════════════════════════════════════════════════════
# 现实校验层
# ═══════════════════════════════════════════════════════════════

def _apply_reality_check(result: PersonalityResult,
                         day_master_stem: str, day_master_wuxing: str,
                         strength: str, score: float,
                         pattern: str, pillars_data: list[dict],
                         interactions: dict, gender: str,
                         harmful_shishen: list[str], favorable_shishen: list[str]):
    """检测命局矛盾，修正套路化/脸谱化判断。

    核心原则：
    1. 任何十神/格局描述都不能脱离身强弱
    2. 存在对立组合时（如财破印、伤官见官），必须标注矛盾而非单面描述
    3. 大运影响当前性格表现
    4. 现实行为优先于理论标签
    """
    corrections: list[str] = []

    is_weak = "弱" in strength
    is_strong = "强" in strength
    is_neutral = "中和" in strength

    # 快速判断
    all_tg = set(p.get("ten_god", "") for p in pillars_data if p.get("source") == "stem")
    all_hidden = set()
    for p in pillars_data:
        for h in p.get("hidden_ten_gods", []):
            all_hidden.add(h)
    all_combined = all_tg | all_hidden

    has_cai_stem = any("财" in (p.get("ten_god") or "") and p.get("source") == "stem" for p in pillars_data)
    has_yin_stem = any("印" in (p.get("ten_god") or "") and p.get("source") == "stem" for p in pillars_data)
    has_shang = "伤官" in all_combined
    has_guan = "正官" in all_combined
    has_zhengcai = "正财" in all_combined
    has_piancai = "偏财" in all_combined
    shang_jian_guan = has_shang and has_guan
    cai_po_yin = has_cai_stem and has_yin_stem
    bijie_count = sum(1 for p in pillars_data if p.get("ten_god") in ("比肩", "劫财"))
    yin_count = sum(1 for p in pillars_data if p.get("ten_god") in ("正印", "偏印"))

    # ── 规则 1: 财破印 —— 现实利益与学业/理想的冲突 ──
    if cai_po_yin:
        if "正印" in pattern or "偏印" in pattern:
            corrections.append(
                "财破印——虽为印格，但现实中对利益的兴趣 ≥ 对学问的兴趣。"
                "不是不爱学习，是更爱能变现的东西。若做学术，需是自己真心热爱的领域，"
                "否则坚持不下去。"
            )
            # 修正 pattern_influence
            result.pattern_influence = result.pattern_influence.replace(
                "好学深思", "有学习潜力但需要内在动机驱动"
            ).replace("淡泊名利", "内心有清高的一面，但现实诱惑常拉扯")
            # 修正 dominant_ten_god if 正印
            if result.dominant_ten_god and "正印" in result.dominant_ten_god:
                result.dominant_ten_god = result.dominant_ten_god.replace(
                    "爱读书思考", "有学习天赋，但需自发兴趣驱动，被动灌输无效"
                ).replace("淡泊名利", "精神追求与物质欲望并存")

    # ── 规则 2: 身弱 —— 所有正面特质打折扣 ──
    if is_weak and score < 1.0:
        corrections.append(
            f"身极弱（{score}分）——理想中的性格特质因能量不足而难以充分发挥。"
            "表现出的状态：容易累、容易纠结、想得多做得少、需要外界推一把。"
            "这不是懒或性格缺陷，是能量层面的客观限制。补身（增强实力、积累学历/技能）后会有质的飞跃。"
        )
        # 调整 strength_label
        result.strength_label += (
            "。现实中容易表现为：专注力不够持久、对压力敏感、做事需要外力推动。"
            "能量积累（学历/技能/身体）是性格发挥的前提，在这之前不要苛责自己。"
        )

    # ── 规则 3: 伤官见官 —— 不服管、不走寻常路 ──
    if shang_jian_guan:
        if "正印" in pattern:
            corrections.append(
                "伤官见官+正印格——表面文静听话，内心极其有自己的想法。"
                "不是叛逆张扬型的反叛，而是'你说的我都听着，但我该怎么做还怎么做'。"
                "不适合高度规则化、层级森严的环境，适合有自主空间的工作。"
            )
        elif "正官" in pattern:
            corrections.append(
                "伤官见官+官格——内心有强烈的反规则冲动，但又不得不在规则内行事。"
                "这种矛盾会带来内耗：做自己想做的不敢，做别人要求的又不甘。"
                "解决方案是找到合规范围内的创新空间。"
            )

    # ── 规则 4: 比劫多 —— 朋友的影响 ──
    if bijie_count >= 3:
        if is_weak:
            corrections.append(
                "比劫多（朋友/同辈多）——社交圈对她的影响很大，容易因为朋友的事分心或破财。"
                "帮朋友前先掂量自己的能力和精力"
            )
        else:
            corrections.append(
                "比劫多——社交圈广，朋友多且能在关键时刻帮忙。适合团队合作。"
            )

    # ── 规则 5: 印星重但身弱 —— 依赖性强 ──
    if yin_count >= 3 and is_weak:
        corrections.append(
            "印星重重但身弱——需要依靠却得到的帮助不够（印多而不生身=湿木不生火）。"
            "现实中表现为：有贵人/长辈/导师的潜在帮助，但真正关键时还得靠自己。"
            "建议主动筛选真正能帮到你的人，不要被动等待。"
        )

    # ── 规则 6: 阴干+身弱 —— 内敛的表达方式 ──
    if day_master_stem in ("乙", "丁", "己", "辛", "癸") and is_weak:
        corrections.append(
            "阴干身弱——不是真的内向或社恐，是在不熟的人面前会自动收敛。"
            "小圈子或对信任的人会很放得开。需要的是安全感，不是社交训练。"
        )

    # ── 规则 7: 财星透干+身弱 —— 对钱的态度 ──
    if has_cai_stem and is_weak:
        corrections.append(
            "财星透干但身弱——想赚钱但能量撑不起野心，容易'富屋贫人'（看起来有赚钱机会但实际到手的少）。"
            "先投资自己（技能/学历/身体），等身变强了再追求财富，否则容易被钱反噬。"
        )

    # ── 规则 8: 格局与行为的偏差 ──
    if "正印" in pattern and is_weak and has_shang:
        corrections.append(
            "正印格+伤官——传统认知的'乖乖女'标签不适合她。"
            "她有独立的精神世界和创造力，只是不轻易对外展示。"
            "找到能发挥她创造力的出口，比规规矩矩走寻常路更适合。"
        )

    # 将修正注入 result
    result.special_combos.append("── 现实校验（防止脸谱化）──")
    for c in corrections:
        result.special_combos.append(c)

    # ── 重写 profile 为实用版本 ──
    dm_info = DAY_MASTER_PERSONALITY.get(day_master_stem, {})
    dm_core_short = dm_info.get("core", "").split("，")[0] if dm_info else ""
    dm_image = dm_info.get("image", "") if dm_info else ""

    # 基础画像
    strength_word = "偏弱" if is_weak else "偏强" if is_strong else "中和"
    profile_parts = [
        f"日主{day_master_stem}（{day_master_wuxing}·{strength_word}），{dm_image}。",
        f"核心：{dm_core_short}。" if dm_core_short else "",
    ]

    # 加入最重要的1-2条现实校验
    key_corrections = [c for c in corrections if not c.startswith("印星重") and not c.startswith("阴干身弱")]
    if key_corrections:
        # 取最短最重要的一条
        best = min(key_corrections, key=len)
        profile_parts.append(best.split("——")[-1] if "——" in best else best)

    result.profile = "".join(profile_parts)


# ═══════════════════════════════════════════════════════════════
# 家境分析
# ═══════════════════════════════════════════════════════════════

FAMILY_LEVELS = {
    "宽裕": "家境宽裕",
    "普通": "家境普通",
    "紧张": "家境紧张",
}


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

    # 年支藏比肩 + 偏财不显 → 父亲财务问题（校准: 案例A）
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
                relation_notes.append(f"年支月支相害→ 父亲与祖辈关系不和")
            elif inter["type"] == "六冲":
                relation_notes.append(f"年柱月柱相冲→ 离祖成家，祖辈与父母辈关系紧张")
            elif inter["type"] == "相刑":
                relation_notes.append(f"年柱月柱相刑→ 祖辈与父母辈有矛盾摩擦")

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

    # 正财合日主 → 家庭资源倾斜（校准: 案例A）
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
            health_notes.append(f"父星坐羊刃—《渊海子平》：财坐刃，父有损伤")
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
    # 年伤月劫 → 寒门
    if "伤" in str(year_tg_name) and "劫" in str(month_tg_name):
        ft_notes.append("年伤月劫—《滴天髓》：出身寒窘，创业之命")
    elif "伤" in str(year_tg_name):
        ft_notes.append("年柱伤官—《渊海子平》：祖业凋零，需靠自己")
    # 月柱七杀 → 早年艰苦
    if "七杀" in str(month_tg_name) or "偏官" in str(month_tg_name):
        ft_notes.append("月柱七杀—《渊海子平》：早年艰苦，家境不丰")
    # 年柱正官/正印
    if str(year_tg_name) == "正官":
        ft_notes.append("年柱正官—《三命通会》：出身正统，有家规")
    if str(year_tg_name) == "正印":
        ft_notes.append("年柱正印—《三命通会》：书香门第，得祖萌")
    # 月令判断
    from .enums import Dizhi as _Dizhi
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
                from .ten_gods import wuxing_sheng, wuxing_ke
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


def analyze_stress_profile(
    favorable_shishen: list[str],
    harmful_shishen: list[str],
    strength: str,
    pattern: str,
    gender: str,
    pillars_data: list[dict],
    special_combos: list[str],
) -> dict:
    """抗压心理画像——三引擎架构（v0.10.0）

    引擎一：压力源定位（官杀扫描）
    引擎二：防御机制分类（A比劫硬刚 / B杀印相生 / C食伤制杀）
    引擎三：崩溃临界点（七杀攻身 / 财破印生杀）
    """
    is_strong = "强" in strength

    # ── 统计十神分布 ──
    all_shishen = []
    for p in pillars_data:
        if p.get("ten_god"):
            all_shishen.append(p["ten_god"])
        for h in (p.get("hidden_ten_gods") or []):
            all_shishen.append(h)

    has_zhengguan = "正官" in all_shishen
    has_qisha = "偏官" in all_shishen or "七杀" in all_shishen
    has_zhengyin = "正印" in all_shishen
    has_pianyin = "偏印" in all_shishen
    has_shishen = "食神" in all_shishen
    has_shangguan = "伤官" in all_shishen
    has_bijian = "比肩" in all_shishen
    has_jiecai = "劫财" in all_shishen
    has_zhengcai = "正财" in all_shishen
    has_piancai = "偏财" in all_shishen

    guan_count = sum(1 for s in all_shishen if s in ("正官", "偏官"))
    sha_count = sum(1 for s in all_shishen if s == "偏官")
    yin_count = sum(1 for s in all_shishen if s in ("正印", "偏印"))
    shishang_count = sum(1 for s in all_shishen if s in ("食神", "伤官"))
    bijie_count = sum(1 for s in all_shishen if s in ("比肩", "劫财"))

    # ════════════════════════════════════════
    # 引擎一：压力源定位
    # ════════════════════════════════════════
    if sha_count >= 2 or (has_qisha and guan_count >= 3):
        pressure_type = "七杀主导型"
        pressure_desc = (
            f"压力以突发性、高强度、生存级危机为主。"
            f"命局七杀{'多重' if sha_count >= 2 else '透出'}，"
            f"长期处于警觉/应激状态，对潜在威胁极度敏感，安全感基线偏低。"
            f"{'官多化杀——体制内规则性压力也转化为心理上的生存焦虑。' if guan_count >= 3 else ''}"
        )
    elif has_zhengguan and guan_count >= 2:
        pressure_type = "正官主导型"
        pressure_desc = (
            "压力以体制化、规则性、慢性积累为主。"
            "对权威、规范、社会评价敏感，压力来自KPI/长辈期许/社会角色期待。"
            "有底线思维，守规矩，但长期处于'达标焦虑'中。"
        )
    elif has_qisha and guan_count == 1:
        pressure_type = "隐性七杀型"
        pressure_desc = (
            "表面压力不大，但潜意识中有未解决的恐惧源。"
            "七杀藏而不透→压力是慢性背景噪音，特定流年引动时集中爆发。"
        )
    else:
        pressure_type = "低官杀型"
        pressure_desc = (
            "命局官杀不显，日常心理压力较低。"
            "缺乏外部压力驱动，自驱力需靠食伤(兴趣)或印星(求知)来补充。"
            "优点是心态松弛，缺点是紧迫感不足、容易拖延。"
        )

    # ════════════════════════════════════════
    # 引擎二：防御机制分类
    # ════════════════════════════════════════
    combo_str = " ".join(special_combos)
    defense_mode = ""
    defense_desc = ""

    # C: 食伤制杀（优先级最高——主动反击型）
    if ("食神制七杀" in combo_str or "食神制杀" in combo_str or
        (has_shishen and has_qisha)):
        defense_mode = "C：火力反击型（食伤制杀）"
        defense_desc = (
            "遇到压力直接反击——用才华、语言、或破格行动去消灭压力源。"
            "思维敏捷，擅长在绝境中找到非对称破局点。"
            "极度慕强，只服比自己更强的人。弱点：情绪上头时可能过度反击、破坏关系。"
        )
    # B: 杀印相生（逻辑降维型）
    elif ("杀印相生" in combo_str or
          (has_qisha and (has_zhengyin or has_pianyin) and yin_count >= 1)):
        defense_mode = "B：逻辑降维型（杀印相生）"
        defense_desc = (
            "遇到绝境不靠体力靠脑力——用深度学习、技术钻研、规则利用来吸收压力。"
            "越是在高压环境下，思维越清晰冷静。"
            "将每一次危机转化为经验值和知识储备。弱点：过度依赖理性，情感表达受阻。"
        )
    # A: 比劫硬刚（身强+比劫）
    elif is_strong and bijie_count >= 2:
        defense_mode = "A：物理硬刚型（身强+比劫抗杀）"
        defense_desc = (
            "遇到高压不妥协、不拐弯。靠意志力、体能、或拉拢同伴去硬拼。"
            "极度固执，宁折不弯，遇强则强。"
            "优势是执行力超强，劣势是不善迂回——硬扛不过时容易突然崩溃。"
        )
    # 混合/弱防御
    elif not is_strong and guan_count >= 2 and yin_count == 0 and shishang_count == 0:
        defense_mode = "无有效防御（⚠ 脆弱型）"
        defense_desc = (
            "面对压力缺乏有效的心理防御工具——无印星化解，无食伤反击，无比劫硬抗。"
            "容易陷入深度焦虑，遭遇挫折后恢复周期长。"
        )
    else:
        # 模糊型
        defense_mode = "混合型"
        if is_strong:
            defense_desc = "身强有一定抗压底子，但缺乏突出的防御专长。压力下倾向于'先扛再说'，建议有意识培养印星（学习/规划）或食伤（表达/创作）作为减压出口。"
        else:
            defense_desc = "身偏弱但有一定缓冲机制。压力下倾向于回避或依赖他人。建议强化比劫（运动/社交）或印星（阅读/冥想）来建立主动抗压能力。"

    # ════════════════════════════════════════
    # 引擎三：崩溃临界点
    # ════════════════════════════════════════
    crash_points = []

    # 规则1：七杀攻身（身极弱+无印+无食伤）
    if (not is_strong and has_qisha and guan_count >= 2
        and yin_count == 0 and shishang_count == 0):
        crash_points.append({
            "trigger": "七杀攻身（纯肉身挨打型）",
            "mechanism": (
                "身弱+官杀旺+无印无食伤→面对压力无任何化解或反击工具，"
                "属于'纯肉身挨打'状态。极易陷入深度焦虑、讨好型人格、"
                "遇到重大挫折后可能彻底摆烂或产生自我毁灭倾向。"
            ),
            "prevention": (
                "必须后天建立防御：①培养一项需要深度专注的技能（印星替代）；"
                "②坚持高强度体育锻炼（比劫替代）；③远离PUA型环境和人物。"
            ),
        })

    # 规则2：财破印生杀
    if (has_zhengcai or has_piancai) and (has_zhengyin or has_pianyin) and has_qisha:
        crash_points.append({
            "trigger": "财破印生杀（逻辑崩盘型）",
            "mechanism": (
                "原局印星（理智/信仰/原则）是抵御七杀（危机）的防火墙。"
                "但财星（欲望/利益/情欲）会击碎印星，并源源不断给七杀供弹。"
                "典型场景：因贪婪（钱/色/捷径）放弃原则→防线瞬间决堤→危机全面失控。"
            ),
            "prevention": (
                "核心红线：面临高回报诱惑时必须回归原则性判断（印星），"
                "不要用'这次例外'破坏自己的底层逻辑。建立'诱惑审查清单'："
                "这件事是否在消耗我的核心防御？"
            ),
        })

    # ── 组装输出 ──
    daily_psyche = (
        f"压力类型：{pressure_type}。{pressure_desc}"
    )
    extreme_response = (
        f"防御模式：{defense_mode}。{defense_desc}"
    )
    prevention_text = (
        "；".join([cp["prevention"] for cp in crash_points])
        if crash_points
        else "当前命局防御体系完整，未检测到系统性崩溃临界点。压力管理重点：维持现有防御机制的有效运转，避免长期透支。"
    )

    return {
        "pressure_type": pressure_type,
        "pressure_source": pressure_desc,
        "defense_mode": defense_mode,
        "defense_desc": defense_desc,
        "crash_points": crash_points,
        "daily_psyche": daily_psyche,
        "extreme_response": extreme_response,
        "prevention": prevention_text,
    }


def build_pillars_data_for_analysis(chart) -> list[dict]:
    """从 BaziChart 提取分析所需的四柱数据"""
    from .ten_gods import get_ten_god
    pillars = [chart.year, chart.month, chart.day, chart.hour]
    result = []
    for p in pillars:
        data = {
            "pillar_type": p.pillar_type,
            "stem": p.stem.value,
            "branch": p.branch.value,
            "ten_god": p.ten_god.value if p.ten_god else None,
            "source": "stem" if p.pillar_type != "日柱" else "day_master",
            "hidden_stems": [{"stem": hs.stem.value, "level": hs.level} for hs in p.hidden_stems],
            "hidden_ten_gods": [],
            "stem_wuxing": p.stem.wuxing.value,
            "branch_wuxing": p.branch.wuxing.value,
            "nayin": p.nayin,
        }
        # 藏干十神
        for hs in p.hidden_stems:
            tg = get_ten_god(chart.day_master, hs.stem)
            if tg:
                data["hidden_ten_gods"].append(tg.value)
        result.append(data)
    return result
