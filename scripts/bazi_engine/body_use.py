"""宾主体用分析 + 墓库应期检测

宾主体用: 段建业《段氏理象学》— 比劫/印/食伤为"体"(自身资源), 财/官为"用"(外部追求)
墓库应期: 辰戌丑未逢冲为关键时间节点
"""

from dataclasses import dataclass


@dataclass
class BodyUseResult:
    body_stars: list[str]     # 体神列表 (比劫/印/食伤)
    use_stars: list[str]      # 用神列表 (财/官)
    body_count: int           # 体神数量
    use_count: int            # 用神数量
    balance_note: str         # 体用平衡说明
    mu_ku_signals: list[str]  # 墓库刑冲信号

    def to_dict(self) -> dict:
        return {
            "body_stars": self.body_stars,
            "use_stars": self.use_stars,
            "body_count": self.body_count,
            "use_count": self.use_count,
            "balance_note": self.balance_note,
            "mu_ku_signals": self.mu_ku_signals,
        }


def analyze_body_use(pillars_data: list[dict], interactions: dict,
                     luck_pillars: list, annual_scans) -> BodyUseResult:
    """宾主体用分析 + 墓库应期检测"""
    body = []
    use = []

    for p in pillars_data:
        tg = p.get("ten_god", "")
        if tg in ("比肩", "劫财", "正印", "偏印", "食神", "伤官"):
            body.append(tg)
        elif tg in ("正财", "偏财", "正官", "偏官", "七杀"):
            use.append(tg)

    body_count = len(body)
    use_count = len(use)

    # 体用平衡
    if body_count > use_count + 2:
        balance_note = (
            f"体神({body_count})远多于用神({use_count})——"
            "自身资源充足但外部目标不明确。段建业：「体多用心，需要寻找值得投入的用神方向」"
        )
    elif use_count > body_count + 2:
        balance_note = (
            f"用神({use_count})远多于体神({body_count})——"
            "外部机会多但自身实力跟不上。段建业：「用多体少，先补身体再求财官」"
        )
    elif body_count >= 1 and use_count >= 1:
        balance_note = (
            f"体神({body_count})与用神({use_count})基本平衡——"
            "自身资源与外部追求匹配，适合稳扎稳打。"
        )
    else:
        balance_note = "体用配置偏单一，需结合大运流年看发展方向。"

    # 墓库应期检测: 辰戌丑未逢冲
    mu_ku = {"辰", "戌", "丑", "未"}
    mu_ku_signals = []

    # 原局墓库冲
    for inter in interactions.get("dizhi", []):
        if inter["type"] == "六冲":
            parts = inter.get("participants", [])
            if len(parts) == 2 and set(parts) <= mu_ku:
                mu_ku_signals.append(
                    f"原局{'+'.join(parts)}冲→墓库逢冲，重大转机信号"
                )

    # 流年/大运逢墓库冲
    for scan in annual_scans:
        ln_b = scan.liunian_branch.value
        dn_b = scan.dayun_branch.value if scan.dayun_branch else ""
        if ln_b in mu_ku and dn_b and dn_b in mu_ku and ln_b != dn_b:
            mu_ku_signals.append(
                f"{scan.year}年流年{ln_b}冲大运{dn_b}→墓库应期，关键转折年"
            )

    return BodyUseResult(
        body_stars=body,
        use_stars=use,
        body_count=body_count,
        use_count=use_count,
        balance_note=balance_note,
        mu_ku_signals=mu_ku_signals,
    )
