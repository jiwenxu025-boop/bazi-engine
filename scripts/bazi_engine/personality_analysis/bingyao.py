"""病药检测 — 十神过大过小诊断"""
from .constants import (
    CAI_STARS, GUAN_STARS, YIN_STARS, SHISHANG_STARS, BIJIE_STARS,
    THRESHOLD_STRONG, THRESHOLD_PRESENT, THRESHOLD_WEAK,
)


def _sum_group(scores, group: tuple[str, ...]) -> float:
    """计算一组十神的加权总分"""
    return sum(scores.get(s, 0) for s in group)

def _is_adjacent(pillars_data: list[dict], shishen_a: str, shishen_b: str) -> bool:
    """检查两个十神是否在相邻柱或同柱出现（贴身关系）"""
    positions: dict[str, list[int]] = {}
    for i, p in enumerate(pillars_data):
        tg = p.get("ten_god")
        if tg:
            positions.setdefault(tg, []).append(i)
        for htg in p.get("hidden_ten_gods", []):
            positions.setdefault(htg, []).append(i)
    pos_a = positions.get(shishen_a, [])
    pos_b = positions.get(shishen_b, [])
    for pa in pos_a:
        for pb in pos_b:
            if abs(pa - pb) <= 1:  # 同柱(差0)或相邻柱(差1)
                return True
    return False

def detect_bingyao_combos(
    weighted_scores,
    strength: str,
    pattern: str,
    pillars_data: list[dict],
) -> list[dict]:
    """检测病药组合，返回按优先级排序的全局指令列表。

    Returns:
        [{"combo": "伤官见官", "priority": 1, "directive": "...", "evidence": {...}}, ...]
    """
    scores = weighted_scores
    combos: list[dict] = []

    shang_guan = scores.get("伤官", 0)
    shi_shen = scores.get("食神", 0)
    zheng_guan = scores.get("正官", 0)
    qi_sha = scores.get("偏官", scores.get("七杀", 0))
    pian_yin = scores.get("偏印", 0)
    zheng_yin = scores.get("正印", 0)
    zheng_cai = scores.get("正财", 0)
    pian_cai = scores.get("偏财", 0)

    cai_total = _sum_group(scores, CAI_STARS)
    guan_total = _sum_group(scores, GUAN_STARS)
    yin_total = _sum_group(scores, YIN_STARS)
    shishang_total = _sum_group(scores, SHISHANG_STARS)
    bijie_total = _sum_group(scores, BIJIE_STARS)

    is_weak = "弱" in strength

    # ── 1. 伤官见官：真我洁癖 vs 秩序需要 ──
    if shang_guan >= THRESHOLD_PRESENT and zheng_guan >= THRESHOLD_PRESENT:
        combos.append({
            "combo": "伤官见官",
            "priority": 1,
            "directive": (
                "【强制约束】：伤官见官——'真我洁癖'撞上'秩序需要'。底层矛盾不是叛逆vs服从，"
                "而是'宁可得罪人也不委屈自己'（伤官）和'没规则我不安心'（正官）两股驱动力在打架。"
                "结果就是：在一个需要按规矩来的地方，你偏要指出规矩有多蠢。"
                "解析重点：1. 建议走凭硬技术说话、自由度高的职业——独立开发者/顾问/创意总监，不是因为你不好管，是因为你的创造力在层级结构里是浪费；"
                "2. 你不是不会来事，你是不屑——但这会让该给你机会的人变成你的敌人。学会用利益语言（财）或共情话术（印）包装你的真实想法，不是圆滑，是战术。"
            ),
            "evidence": {"伤官": shang_guan, "正官": zheng_guan},
        })

    # ── 2. 食神制杀 / 伤官驾杀：创造本能 × 生存应激 ──
    if qi_sha >= THRESHOLD_STRONG and shishang_total >= THRESHOLD_PRESENT:
        combo_name = "食神制杀" if shi_shen >= shang_guan else "伤官驾杀"
        combos.append({
            "combo": combo_name,
            "priority": 1,
            "directive": (
                "【强制约束】：食伤制杀——'创造本能'驾驭'生存应激'。你对无聊零容忍（食伤），"
                "又持续处于高压警觉状态（七杀）。两股力一合：危机中你是战神，平淡中你是麻烦制造机。"
                "解析重点：1. 解决棘手问题的能力是顶尖的——别人崩溃你反而兴奋，这是天赋不是诅咒；"
                "2. 适合开拓荒地/接手烂摊子/高风险高回报的赛道——你需要在有压力的环境中才能不无聊；"
                "3. 但常态期你会下意识制造摩擦来获取刺激——不是故意的，是你的神经系统需要'敌人'才能高效运转。"
                "学会在和平期用高强度运动/竞技/创作来替代职场冲突。"
            ),
            "evidence": {"七杀": qi_sha, "食伤": shishang_total, "食神": shi_shen, "伤官": shang_guan},
        })

    # ── 3. 比劫夺财：归属焦虑 × 欲望引擎 ──
    if (
        bijie_total >= THRESHOLD_STRONG
        and cai_total < THRESHOLD_PRESENT
        and guan_total < THRESHOLD_PRESENT
    ):
        combos.append({
            "combo": "比劫夺财",
            "priority": 2,
            "directive": (
                "【强制约束】：比劫夺财——'归属焦虑'透支了'欲望引擎'。你不是贪财，你是靠'跟别人比较'来定位自己（比劫），"
                "但你的欲望和资源（财）被这种比较消耗得干干净净。"
                "绝对禁止输出'适合合伙做生意'。解析重点：1. 最容易发生合伙纠纷/借钱不还/冲动消费——不是运气差，是你用花钱和帮别人来买'自己人'的感觉；"
                "2. 破局不是更努力地社交，是建立壁垒——用官杀（进大平台/拿硬资质）或用食伤（技术创新打出差异化），让自己不再需要跟所有人比较；"
                "3. 立刻停止无效社交——你以为在维护关系，其实在维护焦虑。"
            ),
            "evidence": {"比劫": bijie_total, "财星": cai_total, "官杀": guan_total},
        })

    # ── 4. 财多身弱：外部反馈过载 ──
    if cai_total >= THRESHOLD_STRONG and is_weak and cai_total > yin_total:
        combos.append({
            "combo": "财多身弱",
            "priority": 1,
            "directive": (
                "【强制约束】：财多身弱——'外部反馈过载'。你不是贪，是你的欲望引擎（财）马力太足，"
                "但你的神经带宽（身）根本处理不了这么多信号。每件事看起来都是机会，"
                "每条反馈都让你想调整方向，最后就是全开了叉全关了。"
                "解析重点：1. 不是机会不够多，是太多了——你需要的不是更多信息，是关掉90%的目标；"
                "2. 做减法是最难的事（因为你每砍一个都觉得在亏），但不砍就是全线瘫痪；"
                "3. 必须借助外部力量分担——团队/搭档不是可选项，是生存必需品。单打独斗对你来说就是慢性休克。"
            ),
            "evidence": {"财星": cai_total, "印星": yin_total, "比劫": bijie_total, "身强弱": strength},
        })

    # ── 5. 杀印相生：控制焦虑 → 战略武器 ──
    if guan_total >= THRESHOLD_STRONG and yin_total >= THRESHOLD_PRESENT:
        adjacent = (
            _is_adjacent(pillars_data, "偏官", "偏印") or
            _is_adjacent(pillars_data, "偏官", "正印") or
            _is_adjacent(pillars_data, "七杀", "偏印") or
            _is_adjacent(pillars_data, "七杀", "正印") or
            _is_adjacent(pillars_data, "正官", "偏印") or
            _is_adjacent(pillars_data, "正官", "正印")
        )
        if adjacent:
            combos.append({
                "combo": "杀印相生",
                "priority": 1,
                "directive": (
                    "【强制约束】：杀印相生——'控制焦虑'被炼成了'战略武器'。你的潜意识把每次压力都当成'需要被理解和掌控的复杂系统'——"
                    "别人的高压是崩溃，你的高压是升级。"
                    "解析重点：1. 隐忍力和战略定力是你的核心武器——不是你能扛，是你会把压力转化为理解框架，然后反制；"
                    "2. 在层级分明的大组织中成长路径最清晰——大公司/体制/专业机构，不是因为你喜欢官僚，是因为你把规则当武器而不是桎梏；"
                    "3. 唯一的陷阱：你以为自己在扛，其实是在消耗。需要找印星（贵人/学历/制度规则）来分摊——不是硬扛，是借力。"
                ),
                "evidence": {"七杀": qi_sha, "印星": yin_total, "贴身": adjacent},
            })

    # ── 6. 枭神夺食：安全系统绞杀创造本能 ──
    if pian_yin >= THRESHOLD_STRONG and shi_shen >= THRESHOLD_PRESENT:
        combos.append({
            "combo": "枭神夺食",
            "priority": 1,
            "directive": (
                "【强制约束】：枭神夺食——'安全系统'在绞杀'创造本能'。这不仅是表达障碍，"
                "是你的底层安全程序（偏印）把你的快乐和创造力（食神）识别成了威胁。"
                "于是你越想安全，越不能快乐；越不能快乐，越觉得不安全——死循环。"
                "请用温和、共情的语调。解析重点：1. 不是你没有创造力，是你不敢释放——因为每一次表达都可能被批评；"
                "2. 容易陷入自我怀疑和被害感的漩涡——不是你敏感，是安全系统在误报；"
                "3. 唯一破局：用偏财（真实的利益刺激/物理环境切换/完全不动脑的体力消耗）来切掉安全系统的过度运转。"
                "不是想通了再行动，是先动起来让大脑没空瞎想。"
            ),
            "evidence": {"偏印": pian_yin, "食神": shi_shen},
        })

    # ── 7. 印重身滞：安全系统过载 ──
    # 印星过旺（≥8.0）→ 必须先理解所有变量才敢行动 → 永远在准备
    if yin_total >= 8.0 and yin_total >= max(scores.values(), default=0):
        combos.append({
            "combo": "印重身滞",
            "priority": 1,
            "directive": (
                "【强制约束】：印重身滞——'安全系统过载'。你的大脑把所有事都当成需要先完全理解才能启动的研究课题。"
                "结果就是：每个细节都想通了，第一步还没迈出去。缺的不是学习能力，是从'理解'到'执行'的切换勇气。"
                "解析重点：1. 唯一破局：先做再改——每天一件小事，不管对错先做完，比想通一百个方案有用；"
                "2. 适合理论+实操结合的职业——技术咨询/产品策划/教育设计，不是纯学术（太寂寞）也不是纯执行（太无聊）；"
                "3. 不要相信自己的意志力——你太擅长给自己找合理的不行动理由。用deadline/搭档监督/付费对赌这种外部约束。"
            ),
            "evidence": {"印星": yin_total, "食伤": shishang_total},
        })

    # ── 8. 财破印：欲望引擎 vs 安全系统 ──
    # 财星≥5 且 印星≥3 且 财>印 → 等不了结果 vs 没理解不敢动
    if cai_total >= 5.0 and yin_total >= THRESHOLD_PRESENT and cai_total > yin_total:
        combos.append({
            "combo": "财破印",
            "priority": 2,
            "directive": (
                "【强制约束】：财破印——'欲望引擎'在瓦解'安全系统'。这不是贪财vs爱学习，"
                "是两套认知模式的内部战争：财让你问'做这个有什么用、多久见效'，"
                "印让你想'我还没理解透、还没准备好'。结果就是：每件事都学到能交付就停，从不真正精通。"
                "换赛道的频率比任何同行都快，因为新赛道的反馈最直接，深耕的回报太慢了。"
                "解析重点：1. 你的问题不是缺乏专注力，是'等不了——你需要看到即时的外部反馈（数据/钱/认可）才能确认自己走在正确的路上；"
                "2. 破局不是强迫自己'坐得住'，是把深耕包装成一组短期可交付的里程碑——每两周看到一次成果，就不需要换赛道；"
                "3. 时刻提醒自己：你过去那些'觉得没用了就放弃'的东西，只差最后20%就能变成不可替代的优势。"
            ),
            "evidence": {"财星": cai_total, "印星": yin_total},
        })

    # ── 9. 食伤过旺泄身：创造本能耗干自己 ──
    # 食伤≥8.0 且 身弱 → 不输出会死但精力撑不住
    if shishang_total >= 8.0 and is_weak:
        combos.append({
            "combo": "食伤过旺泄身",
            "priority": 1,
            "directive": (
                "【强制约束】：食伤过旺泄身——'不输出会死'但身体跟不上。你的创造本能（食伤）马力全开，"
                "但你的精力银行（日主）存款太少。想做的事比能做的事多十倍，"
                "每次灵感来了就冲，冲到一半没电了，换下一个灵感——burnout循环。"
                "解析重点：1. 不是为了少做事而做减法——是每一件未完之事都在后台消耗你的注意力；"
                "2. 必须建立'一次只做一件事直到交付'的铁律——不是靠意志力，是靠物理限制（只保留一个项目的工具/文件/窗口）；"
                "3. 体力锻炼不是可选项——你是脑力过载型，唯一的刹车是身体疲劳。每天运动一小时，是为了让大脑停下来。"
            ),
            "evidence": {"食伤": shishang_total, "食神": shi_shen, "伤官": shang_guan, "身强弱": strength},
        })

    # ── 10. 官杀混杂：两套标准互搏 ──
    # 正官≥3.0 且 七杀≥3.0 → 自我要求内部分裂
    if zheng_guan >= 3.0 and qi_sha >= 3.0:
        combos.append({
            "combo": "官杀混杂",
            "priority": 2,
            "directive": (
                "【强制约束】：官杀混杂——你在用两套互相矛盾的标准要求自己。"
                "正官让你追求'对'——符合规则的、稳妥的、被认可的。"
                "七杀让你追求'强'——竞争取胜的、抢占先机的、不被淘汰的。"
                "两套系统同时在跑：一边想按规则慢慢来，一边怕来不及被人超越。"
                "结果就是对任何选择都不满意——选了安全的就觉得没出息，选了冒险的又睡不着觉。"
                "解析重点：1. 这不是选择困难症，是两套评估体系在同时打分——必须先意识到'不是选项有问题，是你的尺子有两把'；"
                "2. 不同人生阶段用不同的尺子——成长期听七杀（敢冲），稳定期听正官（守城），别让它们同时投票；"
                "3. 找一个外部裁判——导师/上司/合伙人——把两套标准的决策权外包一部分出去。"
            ),
            "evidence": {"正官": zheng_guan, "七杀": qi_sha},
        })

    # ── 排序：priority 升序（1最先），同 priority 按影响分数降序 ──
    _STRENGTH_MAP = {"强": 0.8, "偏强": 0.6, "中和": 0.5, "偏弱": 0.4, "弱": 0.2}
    def _sort_key(c):
        ev = c.get("evidence", {})
        nums = []
        for v in ev.values():
            if isinstance(v, (int, float, bool)):
                nums.append(float(v))
            elif isinstance(v, str) and v in _STRENGTH_MAP:
                nums.append(_STRENGTH_MAP[v])
        score_sum = sum(nums)
        return (c["priority"], -score_sum)

    combos.sort(key=_sort_key)
    return combos

