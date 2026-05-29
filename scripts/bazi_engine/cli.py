"""命令行入口 — 八字排盘快速输出"""

import argparse
from .chart import build_chart
from .enums import Tiangan, Dizhi, Shishen


def format_chart(chart) -> str:
    """格式化 BaziChart 为完整技术文本（本地保留用）"""
    _ensure_dayun_interpretations(chart)
    return _format_chart_internal(chart, practical=False)


def _ensure_dayun_interpretations(chart):
    """懒加载大运LLM解读：首次访问时才调用API"""
    if chart.dayun_interpretations is None and chart.dayun_modulations:
        from .llm_review import enrich_dayun_interpretations
        chart.dayun_interpretations = enrich_dayun_interpretations(chart)


def format_chart_practical(chart) -> str:
    """格式化 BaziChart 为实用解读文本（对外发布用，无技术推导）"""
    _ensure_dayun_interpretations(chart)
    return _format_chart_internal(chart, practical=True)


def _format_chart_internal(chart, practical: bool = False) -> str:
    """内部格式化函数"""
    lines = []
    p = lines.append

    p(f"╔══════════════════════════════════╗")
    p(f"║  八字分析: {chart.name}  ({chart.gender})" + " " * (20 - len(chart.name)) + "║")
    p(f"╚══════════════════════════════════╝")
    p("")

    if practical:
        # ===== 实用模式：只输出白话解读 =====

        # 四柱简表（仅干支）
        p("┌────────┬────────┬────────┬────────┐")
        p(f"│  年柱   │  月柱   │  日柱   │  时柱   │")
        p("├────────┼────────┼────────┼────────┤")
        p(f"│{chart.year.stem.value}{chart.year.branch.value:3}    │{chart.month.stem.value}{chart.month.branch.value:3}    │{chart.day.stem.value}{chart.day.branch.value:3}    │{chart.hour.stem.value}{chart.hour.branch.value:3}    │")
        p("└────────┴────────┴────────┴────────┘")
        p("")

        # 日主一句话
        day_wx = chart.day_master.wuxing.value
        yy = chart.day_master.yinyang
        strength = chart._yongshen_result.get("strength", "中和") if chart._yongshen_result else "中和"
        p(f"  ● 命主：{chart.day_master.value}（{yy}{day_wx}），体质偏{strength}")
        p(f"  ● 性格底色：{_plain_day_master(chart.day_master)}")

        # v0.15.0: 粒度性格特质
        pr = chart.personality_result or {}
        sub_traits = pr.get("sub_traits", [])
        combo_traits = pr.get("combo_traits", [])
        dizhi_traits = pr.get("dizhi_traits", [])
        all_personality = sub_traits + combo_traits + dizhi_traits
        if all_personality:
            p("  ● 性格细节：")
            shown = 0
            shown_names = set()
            # 日支藏干特质优先（底层性格驱动力）
            for st in sub_traits:
                if shown >= 12:
                    break
                if st.get("source_type") and st.get("trait_name", "") not in shown_names:
                    src_tag = f" ({st.get('source_type', '')})"
                    p(f"    ·{st.get('trait_name', '')}：{st.get('description', '')}{src_tag}")
                    shown_names.add(st.get("trait_name", ""))
                    shown += 1
            # 然后十神加权子特质（去重）
            for st in sub_traits:
                if shown >= 12:
                    break
                if not st.get("source_type") and st.get("trait_name", "") not in shown_names:
                    p(f"    ·{st.get('trait_name', '')}：{st.get('description', '')}")
                    shown_names.add(st.get("trait_name", ""))
                    shown += 1
            # 组合特质
            for ct in combo_traits[:4]:
                if shown >= 12:
                    break
                if ct.get("trait", "") not in shown_names:
                    p(f"    ·{ct.get('trait', '')}：{ct.get('description', '')}")
                    shown_names.add(ct.get("trait", ""))
                    shown += 1
            # 地支特质
            for dt in dizhi_traits[:4]:
                if shown >= 12:
                    break
                if dt.get("trait", "") not in shown_names:
                    p(f"    ·{dt.get('trait', '')}：{dt.get('description', '')}")
                    shown_names.add(dt.get("trait", ""))
                    shown += 1
        p("")

        # 格局白话
        p(f"  ● 格局：{chart.pattern}（{_plain_pattern(chart.pattern)}）")
        p("")

        # 宫位叠象 → 白话
        if chart.palace_star_result:
            for entry in chart.palace_star_result.get("entries", []):
                plain = _plain_palace(entry)
                if plain:
                    p(f"  ● {plain}")
            p("")

        # 纳音 → 白话
        if chart.nayin_relations:
            nayin_plain = _plain_nayin(chart.nayin_relations)
            if nayin_plain:
                p(f"  ● 命局走势：{nayin_plain}")
                p("")

        # 大运简表 + 白话
        p(f"  ● 大运（{chart.start_age}岁起运）：")
        for lp in chart.luck_periods:
            p(f"    {lp['大运']}  {lp['年龄']}")
        # 当前大运白话
        current_dayun_plain = _plain_current_dayun(chart)
        if current_dayun_plain:
            p(f"    → {current_dayun_plain}")
        # LLM 大运解读（v0.14.0）
        if chart.dayun_interpretations:
            p("")
            p("  ● 大运解读（AI）：")
            for di in chart.dayun_interpretations:
                # 找到对应的大运干支
                lp = chart.luck_periods[di["index"]] if di["index"] < len(chart.luck_periods) else None
                label = lp["大运"] if lp else f"第{di['index']+1}步"
                p(f"    {label}（{lp['年龄'] if lp else ''}）：{di['interpretation']}")
        p("")

        # 神煞简化 → 白话
        spirit_plain = _plain_spirits(chart.spirits)
        if spirit_plain:
            p(f"  ● {spirit_plain}")
            p("")

        # 虚神 → 白话
        if chart.void_gods:
            for vg in chart.void_gods:
                p(f"  ● {_plain_void_god(vg)}")
            p("")

        # 十二长生 → 白话
        if getattr(chart, 'changsheng_states', None):
            cs_plain = _plain_changsheng(chart)
            if cs_plain:
                for line in cs_plain:
                    p(f"  ● {line}")
                p("")

        # 流年 → 仅预测
        if chart.annual_scans:
            p("  " + "─" * 40)
            p("  逐年要点：")
            for scan in chart.annual_scans:
                p(f"    {scan.year}年（{scan.age}岁）：")
                for ev in scan.events:
                    if ev.prediction:
                        stars = "★" * ev.strength + "☆" * (3 - ev.strength)
                        mag = f" [{ev.magnitude}]" if getattr(ev, 'magnitude', '') else ""
                        p(f"      [{ev.category}] {stars}{mag} {ev.prediction}")
                # 仅输出最高优先级的 practical notes
                for ev in scan.events:
                    for note in ev.notes:
                        if note.startswith("校准") or note.startswith("案例"):
                            p(f"      > {note}")
            p("")

        # 总体一句话
        summary = _plain_summary(chart)
        if summary:
            p("  " + "─" * 40)
            p(f"  总结：{summary}")
            p("")

    else:
        # ===== 完整技术模式 =====
        # 四柱
        p("┌────────┬────────┬────────┬────────┐")
        p(f"│  年柱   │  月柱   │  日柱   │  时柱   │")
        p("├────────┼────────┼────────┼────────┤")
        p(f"│{chart.year.stem.value}{chart.year.branch.value:3}    │{chart.month.stem.value}{chart.month.branch.value:3}    │{chart.day.stem.value}{chart.day.branch.value:3}    │{chart.hour.stem.value}{chart.hour.branch.value:3}    │")
        p(f"│{chart.year.nayin:^8}│{chart.month.nayin:^8}│{chart.day.nayin:^8}│{chart.hour.nayin:^8}│")
        p("├────────┼────────┼────────┼────────┤")
        def _canggan(pillar):
            return "".join(hs.stem.value for hs in pillar.hidden_stems)
        p(f"│ {_canggan(chart.year):5}  │ {_canggan(chart.month):5}  │ {_canggan(chart.day):5}  │ {_canggan(chart.hour):5}  │")
        p("├────────┼────────┼────────┼────────┤")
        def _shishen(pillar):
            if pillar.ten_god:
                return pillar.ten_god.value
            return "日主"
        p(f"│{_shishen(chart.year):^8}│{_shishen(chart.month):^8}│{_shishen(chart.day):^8}│{_shishen(chart.hour):^8}│")
        p("└────────┴────────┴────────┴────────┘")
        p("")

        # 宫位叠象
        if chart.palace_star_result:
            entries = chart.palace_star_result.get("entries", [])
            if entries:
                p("  ── 宫位叠象（星宫同参）──")
                for entry in entries:
                    p(f"    {entry['pillar_type']}（{entry['palace_meaning']}）")
                    p(f"      十神: {entry['occupying_ten_god']}")
                    if entry.get('spirits_at_palace'):
                        p(f"      神煞: {', '.join(entry['spirits_at_palace'])}")
                    if entry.get('layered_interpretation'):
                        p(f"      → {entry['layered_interpretation']}")
                summary = chart.palace_star_result.get("summary", "")
                if summary:
                    p(f"    总论: {summary}")
                p("")

        # 日主 & 格局
        p(f"  日主: {chart.day_master.value} ({chart.day_master.wuxing.value})  阴阳: {chart.day_master.yinyang}")
        if chart.favorable_tags:
            p(f"  喜用: {' '.join(sorted(chart.favorable_tags))}")
        elif chart._yongshen_result:
            yr = chart._yongshen_result
            p(f"  身{yr['strength']}({yr['score']})  "
              f"喜{' '.join(yr['favorable_wuxing'])}  "
              f"忌{' '.join(yr['harmful_wuxing'])}")
        p(f"  格局: {chart.pattern}")
        if chart.pattern_notes:
            p(f"  取格: {'; '.join(chart.pattern_notes)}")
        if chart.minggong_stem:
            p(f"  命宫: {chart.minggong_stem.value}{chart.minggong_branch.value} ({chart.minggong_nayin})")
        if chart.shengong_stem:
            p(f"  身宫: {chart.shengong_stem.value}{chart.shengong_branch.value} ({chart.shengong_nayin})")
        if chart.taiyuan_stem:
            p(f"  胎元: {chart.taiyuan_stem.value}{chart.taiyuan_branch.value} ({chart.taiyuan_nayin})")
        p("")

        # 纳音生克链
        if chart.nayin_relations:
            p("  纳音生克链:")
            for nr in chart.nayin_relations:
                aup_tag = f"[{nr.auspiciousness}]" if nr.auspiciousness else ""
                p(f"    {aup_tag} {nr.relation_type}: {nr.from_pillar}({nr.from_nayin}) → {nr.to_pillar}({nr.to_nayin})")
                if nr.chain_order:
                    p(f"      链序: {nr.chain_order}")
                if nr.interpretation:
                    p(f"      → {nr.interpretation}")
            p("")

        # 大运
        p(f"  大运: {chart.start_age}岁起运, {chart.dayun_direction_str}")
        for lp in chart.luck_periods:
            p(f"    {lp['大运']}  {lp['年龄']}")
        if chart.dayun_interpretations:
            p("")
            p("  [大运 LLM 解读]")
            for di in chart.dayun_interpretations:
                lp = chart.luck_periods[di["index"]] if di["index"] < len(chart.luck_periods) else None
                label = lp["大运"] if lp else f"第{di['index']+1}步"
                p(f"    {label}  {lp['年龄'] if lp else ''}")
                p(f"      → {di['interpretation']}")
        p("")

        # 神煞
        if chart.spirits:
            p("  神煞:")
            for s in chart.spirits:
                p(f"    [{s.category}] {s.name} → {s.pillar} ({s.source})")
            p("")

        # 虚神
        if chart.void_gods:
            p("  虚神（月令藏干不透者）:")
            for vg in chart.void_gods:
                fav_str = ""
                if vg.is_favorable is True:
                    fav_str = " [喜用]"
                elif vg.is_favorable is False:
                    fav_str = " [忌神]"
                p(f"    {vg.hidden_stem.value}（{vg.level}，十神：{vg.ten_god.value}）{fav_str}")
                p(f"      → {vg.interpretation}")
            p("")

        # 干支关系
        if chart.tiangan_interactions:
            p("  天干关系:")
            for inter in chart.tiangan_interactions:
                p(f"    {inter.inter_type}: {'+'.join(p.value for p in inter.participants)} → {inter.result}  [{'+'.join(inter.pillar_labels)}]")
            p("")
        if chart.dizhi_interactions:
            p("  地支关系:")
            for inter in chart.dizhi_interactions:
                p(f"    {inter.inter_type}: {'+'.join(p.value for p in inter.participants)} → {inter.result}  [{'+'.join(inter.pillar_labels)}]")
                for note in inter.notes:
                    p(f"      ⚠ {note}")
            p("")

        # 流年
        if chart.annual_scans:
            p("  " + "─" * 50)
            p("  流年扫描:")
            for scan in chart.annual_scans:
                sb_info = f"  [{scan.sb_relation}]" if scan.sb_relation else ""
                p(f"    {scan.year}年({scan.liunian_stem.value}{scan.liunian_branch.value})  {scan.age}岁  大运{scan.dayun_stem.value if scan.dayun_stem else '?'}{scan.dayun_branch.value if scan.dayun_branch else '?'}{sb_info}")
                if scan.dayun_weight_note:
                    p(f"      ⚖ {scan.dayun_weight_note}")
                for ev in scan.events:
                    stars = "★" * ev.strength + "☆" * (3 - ev.strength)
                    mag = f" [{ev.magnitude}]" if getattr(ev, 'magnitude', '') else ""
                    p(f"      [{ev.category}] {stars}{mag} {'+'.join(ev.triggers)}")
                    if ev.prediction:
                        p(f"          → {ev.prediction}")
                    for note in ev.notes:
                        p(f"          > {note}")
            p("")

        # 十二长生
        if getattr(chart, 'changsheng_states', None):
            p("  " + "─" * 50)
            p("  十二长生状态（日主对照各地支）:")
            pillar_states = [cs for cs in chart.changsheng_states if cs.subject == "日主" and cs.year is None and cs.pillar_label in ("年柱", "月柱", "日柱", "时柱")]
            if pillar_states:
                p("    四柱:")
                for cs in pillar_states:
                    note = f"  ⚡{cs.special_note}" if cs.special_note else ""
                    p(f"      {cs.pillar_label}{cs.branch.value} → {cs.state}（{cs.interpretation}）{note}")
            dayun_states = [cs for cs in chart.changsheng_states if cs.subject == "大运"]
            if dayun_states:
                p("    大运:")
                for cs in dayun_states:
                    note = f"  ⚡{cs.special_note}" if cs.special_note else ""
                    p(f"      {cs.branch.value} → {cs.state}（{cs.interpretation}）{note}")
            jue_states = [cs for cs in chart.changsheng_states if cs.special_note == "绝处逢生"]
            if jue_states:
                p("    特殊:")
                for cs in jue_states:
                    p(f"      ⚡ {cs.pillar_label}{cs.branch.value} 绝处逢生 —— {cs.interpretation}")
            p("")

    # v0.15.0: 粒度性格特质（技术模式完整输出）
    pr_full = chart.personality_result or {}
    sub_traits_full = pr_full.get("sub_traits", [])
    combo_traits_full = pr_full.get("combo_traits", [])
    dizhi_traits_full = pr_full.get("dizhi_traits", [])
    if sub_traits_full or combo_traits_full or dizhi_traits_full:
        p("  ──────────────────────────────────────────────────")
        p("  粒度性格特质：")
        if sub_traits_full:
            p("    [十神子特质]")
            for st in sub_traits_full:
                src_type = st.get("source_type", "")
                if src_type:
                    # 日支藏干源：显示来源
                    p(f"      ·{st.get('trait_name', '')}：{st.get('description', '')}  ← {src_type}")
                elif st.get("score"):
                    # 十神加权源：显示分数
                    p(f"      ·{st.get('trait_name', '')}：{st.get('description', '')}  ({st.get('score', '')}分)")
                else:
                    p(f"      ·{st.get('trait_name', '')}：{st.get('description', '')}")
        if combo_traits_full:
            p("    [十神组合特质]")
            for ct in combo_traits_full:
                p(f"      ·{ct.get('trait', '')}：{ct.get('description', '')}  [{ct.get('combo', '')}]")
        if dizhi_traits_full:
            p("    [地支关系→性格]")
            for dt in dizhi_traits_full:
                pillars = dt.get("involved_pillars", [])
                pillar_tag = f" ({', '.join(pillars)})" if pillars else ""
                p(f"      ·{dt.get('trait', '')}：{dt.get('description', '')}  ← {dt.get('relation', '')}{pillar_tag}")
        p("")

    # 警告（两种模式都显示）
    if chart.warnings:
        p("  ⚠ 注意事项:")
        for w in chart.warnings:
            p(f"    ⚠ {w}")

    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════
# 实用模式辅助函数：技术术语 → 白话解读
# ═══════════════════════════════════════════════════════════════

def _plain_day_master(stem) -> str:
    m = {
        "甲": "正直向上、有原则，像大树一样靠得住",
        "乙": "柔韧善变通、适应力强，像藤蔓一样会借力",
        "丙": "热情开朗、光明正大，像太阳一样照耀别人",
        "丁": "敏锐细腻、外柔内刚，像烛火一样持久有温度",
        "戊": "敦厚稳重、讲信用，像城墙一样可靠",
        "己": "温和包容、细腻周到，像田园一样滋养人",
        "庚": "刚毅果断、不怒自威，像刀剑一样干脆利落",
        "辛": "灵秀精致、追求完美，像珠宝一样有品味",
        "壬": "智慧豁达、胸怀宽广，像江河一样流动不居",
        "癸": "细腻内敛、聪慧含蓄，像春雨一样润物无声",
    }
    return m.get(stem.value if hasattr(stem, 'value') else stem, "性格复杂")


def _plain_pattern(pattern: str) -> str:
    m = {
        "正印格": "温和有礼的外表下是独立的精神世界。有学习天赋但需要自发兴趣驱动，被动灌输无效。适合需要深度思考而非重复劳动的工作",
        "偏印格": "思维独特，善于钻研别人不碰的领域。人缘不是优势，但专业深度可以弥补",
        "正官格": "守规矩有原则，适合需要公信力的工作。但内心可能有反叛的一面",
        "偏官格": "有魄力敢竞争，适合挑战性行业。压力大是常态，需要学会减压",
        "正财格": "务实稳重，对钱敏感，适合需要耐心积累的职业",
        "偏财格": "有商业头脑，善于捕捉机会。财运起伏大，不宜把所有鸡蛋放一个篮子",
        "食神格": "有才华懂享受生活，适合需要创意和审美的领域",
        "伤官格": "才华横溢但受不了束缚。适合自由职业或创业，别去体制内找难受",
        "建禄格": "独立自主，靠自己的本事吃饭。不给别人打工的基因",
        "羊刃格": "个性刚强有冲劲，能成事但也容易得罪人。需要学会刹车",
    }
    return m.get(pattern, "格局复杂，需结合具体命局分析")


def _plain_palace(entry: dict) -> str:
    """宫位叠象 → 一句话大白话"""
    pillar = entry.get("pillar_type", "")
    tg = entry.get("occupying_ten_god", "")
    spirits = entry.get("spirits_at_palace", [])
    spirit_str = "、" .join(spirits) if spirits else ""

    base = {
        "年柱": "原生家庭",
        "月柱": "父母和事业环境",
        "日柱": "婚姻和中年",
        "时柱": "子女和晚年",
    }.get(pillar, pillar)

    tg_plain = {
        "比肩": "普通家庭，不靠祖荫",
        "劫财": "家运有波折，父缘较薄",
        "食神": "家境殷实，不愁吃穿",
        "伤官": "家人有才艺，但家运起伏",
        "偏财": "父亲有经商头脑，但帮助有限",
        "正财": "父亲勤劳持家，家境稳定",
        "偏官": "管教严格，压力大但有出息",
        "正官": "家风端正，走正道",
        "偏印": "家庭偏冷清或非传统",
        "正印": "书香门第，有文化根基",
        "日主": "自身和配偶的内在特质看藏干",
    }.get(tg, "")

    if pillar == "日柱" and tg == "日主":
        hidden = entry.get("layered_interpretation", "")
        return f"婚姻：{hidden}"

    if not tg_plain:
        return ""

    result = f"{base}：{tg_plain}"
    if spirit_str:
        # 只保留对普通人有意义的神煞
        meaningful = [s for s in spirits if s in ("天乙贵人", "文昌", "红鸾", "天喜", "华盖", "驿马", "禄")]
        if meaningful:
            result += f"（{'、'.join(meaningful)}）"
    return result


def _plain_nayin(relations) -> str:
    """纳音 → 一句话白话"""
    chains = [r for r in relations if "链" in r.relation_type]
    good = [r for r in relations if r.auspiciousness in ("大吉", "吉")]
    bad = [r for r in relations if r.auspiciousness in ("大凶", "凶")]

    parts = []
    if chains:
        for c in chains:
            if "顺生" in c.relation_type:
                parts.append("一生为家庭付出较多，比较辛苦")
            elif "逆生" in c.relation_type:
                parts.append("晚年运势好，晚年能享福")
            elif "顺克" in c.relation_type:
                parts.append("自己掌控力强，能成事")
            elif "逆克" in c.relation_type:
                parts.append("人生起落较大，需稳扎稳打")
    if not parts and good:
        parts.append("运势根基较好")
    if not parts and bad:
        parts.append("运势根基需要后天努力弥补")
    if not parts:
        parts.append("运势平顺，无功无过")

    return "；".join(parts)


def _plain_current_dayun(chart) -> str:
    """当前大运白话"""
    from datetime import date
    today = date.today()
    age = today.year - chart.birth_dt.year
    if (today.month, today.day) < (chart.birth_dt.month, chart.birth_dt.day):
        age -= 1
    if age < chart.start_age:
        return f"尚未起运，{chart.start_age}岁开始交运"

    # 找当前大运
    idx = max(0, (age - chart.start_age) // 10)
    if idx >= len(chart.luck_pillars):
        return ""
    tg, dz = chart.luck_pillars[idx]
    # 查十二长生
    from ._constants import SHIER_CHANGSHENG
    table = SHIER_CHANGSHENG.get(chart.day_master, {})
    state = table.get(dz, "")
    state_plain = {
        "长生": "运势起步，适合学习新东西",
        "沐浴": "桃花旺，注意感情波动",
        "冠带": "运势上升，形象提升",
        "临官": "运势高峰期，事业有成",
        "帝旺": "运势顶峰，但需防得意忘形",
        "衰": "运势转弱，低调行事",
        "病": "注意身体，减少折腾",
        "死": "运势低迷，耐心等待",
        "墓": "能量封存期，需主动突破",
        "绝": "运势低谷，熬过去就是新生",
        "胎": "暗中酝酿，不宜冒进",
        "养": "慢慢积累，蓄势待发",
    }.get(state, "")
    return f"当前{tg.value}{dz.value}运（{state}：{state_plain}）"


def _plain_spirits(spirits) -> str:
    """神煞 → 白话（只保留对普通人有实际影响的）"""
    if not spirits:
        return ""
    meaningful = {
        "天乙贵人": "命带贵人，遇困难有人帮",
        "文昌": "学业运好，适合读书考试",
        "红鸾": "感情运旺，婚恋机会多",
        "天喜": "喜事多，感情/家庭有好事",
        "华盖": "喜欢独处钻研，有精神追求",
        "驿马": "一生多走动，适合外地发展",
        "禄": "有稳定收入来源，不愁吃穿",
        "桃花": "异性缘旺，需注意感情选择",
        "羊刃": "个性刚强，注意冲动和意外伤害",
        "寡宿": "喜欢安静独处，婚姻需多沟通",
        "学堂": "学习能力强，考试运好",
        "福星贵人": "福气好，遇事能化险为夷",
        "太极贵人": "有悟性，适合钻研型工作",
    }
    found = []
    for sp in spirits:
        name = getattr(sp, 'name', '')
        if name in meaningful and meaningful[name] not in found:
            found.append(meaningful[name])
    if found:
        return f"关键特质：{'；'.join(found[:5])}"  # 最多5条
    return ""


def _plain_void_god(vg) -> str:
    """虚神 → 白话"""
    tg_plain = {
        "正官": "规则和约束", "偏官": "压力和挑战",
        "正财": "稳定收入", "偏财": "意外之财",
        "正印": "学习和贵人", "偏印": "冷门学问",
        "食神": "才华和享受", "伤官": "叛逆和创新",
        "比肩": "同辈和朋友", "劫财": "竞争和花费",
    }.get(vg.ten_god.value, vg.ten_god.value)

    if vg.is_favorable:
        return f"潜在优势：在{tg_plain}方面有隐藏的天赋或机遇，关键时刻会遇到贵人"
    elif vg.is_favorable is False:
        return f"潜在压力：在{tg_plain}方面内心有焦虑，遇到相关年份容易爆发"
    return f"隐藏特质：在{tg_plain}方面有未展现的一面"


def _plain_changsheng(chart) -> list[str]:
    """十二长生 → 白话列表"""
    result = []
    # 日柱状态
    table = None
    from ._constants import SHIER_CHANGSHENG
    table = SHIER_CHANGSHENG.get(chart.day_master)
    if table:
        day_state = table.get(chart.day.branch, "")
        state_plain = {
            "长生": "内在生命力旺盛", "沐浴": "感情生活丰富",
            "冠带": "自我成长能力强", "临官": "自信有主见",
            "帝旺": "精力充沛但需防透支", "衰": "体力容易透支",
            "病": "需注意身体健康", "死": "容易消极悲观",
            "墓": "喜欢独处和积累", "绝": "需要外界推动力",
            "胎": "想法多但行动力弱", "养": "慢慢积累才有收获",
        }.get(day_state, "")
        if state_plain:
            result.append(f"自身状态：{state_plain}")

    # 当前大运状态
    from datetime import date
    today = date.today()
    age = today.year - chart.birth_dt.year
    if (today.month, today.day) < (chart.birth_dt.month, chart.birth_dt.day):
        age -= 1
    if age >= chart.start_age and chart.luck_pillars:
        idx = max(0, (age - chart.start_age) // 10)
        if idx < len(chart.luck_pillars):
            _, dz = chart.luck_pillars[idx]
            state = table.get(dz, "") if table else ""
            phase = {
                "长生": "正处于上升起步期",
                "冠带": "正处于成长加速期",
                "临官": "正处于人生黄金期",
                "帝旺": "正处于巅峰期，注意高峰后回落",
                "衰": "正处于调整期，不要勉强",
                "病": "正处于休整期，健康第一",
                "死": "正处于低谷期，熬过去就好",
                "墓": "正处于积累期，厚积薄发",
                "绝": "正处于转折期，旧的不去新的不来",
                "胎": "正处于酝酿期，别急",
                "养": "正处于蓄力期，慢慢来",
            }.get(state, "")
            if phase:
                result.append(f"当前阶段：{phase}")

    return result


def _plain_summary(chart) -> str:
    """一页纸总结"""
    parts = []

    # 性格
    parts.append(_plain_day_master(chart.day_master))

    # 格局方向
    pattern_plain = _plain_pattern(chart.pattern)
    if pattern_plain:
        parts.append(pattern_plain)

    # 当前大运
    from datetime import date
    today = date.today()
    age = today.year - chart.birth_dt.year
    if (today.month, today.day) < (chart.birth_dt.month, chart.birth_dt.day):
        age -= 1
    if age >= chart.start_age and chart.luck_pillars:
        idx = max(0, (age - chart.start_age) // 10)
        if idx < len(chart.luck_pillars):
            tg, dz = chart.luck_pillars[idx]
            parts.append(f"当前{tg.value}{dz.value}大运（{age}岁）")

    # 纳音链一句话
    if chart.nayin_relations:
        chains = [r for r in chart.nayin_relations if "链" in r.relation_type]
        for c in chains:
            if "逆生" in c.relation_type:
                parts.append("晚年运势好")
            elif "顺生" in c.relation_type:
                parts.append("一生需要多付出")

    # 今年关键信号
    if chart.annual_scans:
        for scan in chart.annual_scans:
            if scan.year == today.year:
                high = [e for e in scan.events if e.strength >= 2]
                if high:
                    cats = list(set(e.category for e in high))
                    parts.append(f"今年重点：{'、'.join(cats)}")
                break

    return "。".join(parts) + "。"


def main():
    parser = argparse.ArgumentParser(description="八字排盘引擎")
    parser.add_argument("--name", required=True, help="姓名")
    parser.add_argument("--gender", required=True, choices=["男", "女"])
    parser.add_argument("--year", type=int, required=True)
    parser.add_argument("--month", type=int, required=True)
    parser.add_argument("--day", type=int, required=True)
    parser.add_argument("--hour", type=int, required=True, help="24小时制 (0-23)")
    parser.add_argument("--day-pillar", nargs=2, metavar=("STEM", "BRANCH"),
                        help="日柱覆盖 (如: 壬 辰)")
    parser.add_argument("--liunian", type=str, help="流年范围 (如: 2023-2030)")
    parser.add_argument("--favorable", nargs="*", default=None,
                        help="喜用十神 (如: 正印 比肩)")
    parser.add_argument("--json", action="store_true", help="JSON 格式输出")
    parser.add_argument("--calibrate", action="store_true",
                        help="从校准数据库加载已知事件")
    parser.add_argument("--calibrate-report", action="store_true",
                        help="输出校准对比报告")
    parser.add_argument("--practical", action="store_true",
                        help="实用模式：仅输出白话解读，无技术推导（对外发布用）")
    parser.add_argument("--family-level", choices=["宽裕", "普通", "紧张"],
                        help="已知家境水平（用于校准引擎推断）")
    parser.add_argument("--father-job", type=str, help="父亲职业")
    parser.add_argument("--mother-job", type=str, help="母亲职业")
    parser.add_argument("--hour-confirmed", action="store_true", default=False,
                        help="出生时辰是否经用户确认（默认否）")

    args = parser.parse_args()

    override = tuple(args.day_pillar) if args.day_pillar else None
    ln_range = None
    if args.liunian:
        parts = args.liunian.split("-")
        ln_range = (int(parts[0]), int(parts[1]))

    favorable_set = set(args.favorable) if args.favorable else None

    # 家境上下文
    family_context = None
    if args.family_level:
        family_context = {"economic_level": args.family_level}
        if args.father_job:
            family_context["father_occupation"] = args.father_job
        if args.mother_job:
            family_context["mother_occupation"] = args.mother_job

    chart = build_chart(
        name=args.name,
        gender=args.gender,
        year=args.year,
        month=args.month,
        day=args.day,
        hour=args.hour,
        day_pillar_override=override,
        liunian_range=ln_range,
        favorable=favorable_set,
        calibrate=args.calibrate,
        family_context=family_context,
        hour_confirmed=args.hour_confirmed,
    )

    # 保存家境上下文到校准库
    if args.calibrate and family_context:
        try:
            from .calibration import get_store
            store = get_store()
            store.set_family_context(args.name, family_context)
        except Exception:
            pass

    if args.json:
        import json
        print(json.dumps(chart.to_dict(), ensure_ascii=False, indent=2))
    elif args.practical:
        print(format_chart_practical(chart))
    else:
        print(format_chart(chart))

    if args.calibrate_report:
        from .calibration import get_store
        store = get_store()
        report = store.compare_with_chart(args.name, chart)
        acc = store.get_accuracy_report()
        if report:
            print("\n  ── 校准对比 ──")
            for r in report:
                s = "✓" if r["status"] == "match" else "✗"
                print(f"  {s} {r['year']} [{r['category']}] {r['note']}")
            print(f"\n  准确率: {acc.get('accuracy', 0)*100:.0f}% ({acc['match']}/{acc['total']})")
            for cat, v in acc.get("by_category", {}).items():
                print(f"    {cat}: {v['accuracy']*100:.0f}% ({v['match']}/{v['total']})")


if __name__ == "__main__":
    main()
