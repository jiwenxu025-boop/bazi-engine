"""校准数据库 — 已知事件持久化 + 规则验证统计

CalibrationStore 管理 JSON 格式的校准数据，支持：
- 按案例名查询已知事件（供 build_chart 的 known_events 使用）
- 记录预测 vs 实际，累积规则验证统计
- 新增/更新案例

文件位置：scripts/data/calibration_store.json
"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


def _default_store_path() -> Path:
    """校准数据库默认路径"""
    return Path(__file__).resolve().parent.parent / "data" / "calibration_store.json"


@dataclass
class RuleStat:
    """单条规则的验证统计"""
    rule: str           # 规则名称
    category: str       # 事件类别
    verified: int = 0   # 验证正确的次数
    total: int = 0      # 总验证次数
    source: str = ""    # "calibration" | "textbook"

    @property
    def accuracy(self) -> float | None:
        if self.total == 0:
            return None
        return self.verified / self.total

    def to_dict(self) -> dict:
        return {
            "rule": self.rule,
            "category": self.category,
            "verified": self.verified,
            "total": self.total,
            "accuracy": round(self.accuracy, 2) if self.accuracy is not None else None,
            "source": self.source,
        }


@dataclass
class CaseRecord:
    """单个案例的校准记录"""
    name: str
    gender: str
    birth: dict  # {year, month, day, hour}
    events: dict[int, str] = field(default_factory=dict)  # {year: status}
    verified_signals: list[dict] = field(default_factory=list)
    family_context: dict | None = None  # {economic_level, father_occupation, mother_occupation, notes}
    notes: str = ""

    def to_dict(self) -> dict:
        d = {
            "name": self.name,
            "gender": self.gender,
            "birth": self.birth,
            "events": {str(k): v for k, v in self.events.items()},
            "verified_signals": self.verified_signals,
            "notes": self.notes,
        }
        if self.family_context:
            d["family_context"] = self.family_context
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "CaseRecord":
        events = {int(k): v for k, v in d.get("events", {}).items()}
        return cls(
            name=d["name"],
            gender=d.get("gender", ""),
            birth=d.get("birth", {}),
            events=events,
            verified_signals=d.get("verified_signals", []),
            family_context=d.get("family_context"),
            notes=d.get("notes", ""),
        )


class CalibrationStore:
    """校准数据库管理器"""

    def __init__(self, path: str | Path | None = None):
        self.path = Path(path) if path else _default_store_path()
        self._cases: dict[str, CaseRecord] = {}
        self._rule_stats: dict[str, RuleStat] = {}
        self._loaded = False

    @property
    def cases(self) -> dict:
        self._load()
        return self._cases

    @property
    def rule_stats(self) -> dict:
        self._load()
        return self._rule_stats

    def _load(self):
        """从 JSON 文件加载"""
        if self._loaded:
            return
        if self.path.exists():
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for case_d in data.get("cases", []):
                case = CaseRecord.from_dict(case_d)
                self._cases[case.name] = case
            for rule_d in data.get("rule_stats", []):
                rs = RuleStat(
                    rule=rule_d["rule"],
                    category=rule_d.get("category", ""),
                    verified=rule_d.get("verified", 0),
                    total=rule_d.get("total", 0),
                    source=rule_d.get("source", ""),
                )
                self._rule_stats[rs.rule] = rs
        self._loaded = True

    def save(self):
        """保存到 JSON 文件"""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "version": "0.5.0",
            "updated": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "cases": [c.to_dict() for c in self.cases.values()],
            "rule_stats": [rs.to_dict() for rs in self.rule_stats.values()],
        }
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    # ── 案例管理 ──

    def get_known_events(self, name: str) -> dict[int, str] | None:
        """获取案例的已知事件，供 build_chart 使用。

        Returns: {year: "relationship"/"single"/...} or None
        """
        self._load()
        case = self.cases.get(name)
        if case and case.events:
            return dict(case.events)
        return None

    def add_case(self, name: str, gender: str, birth: dict,
                 events: dict[int, str] | None = None,
                 notes: str = ""):
        """新增或更新案例"""
        self._load()
        case = CaseRecord(
            name=name, gender=gender, birth=birth,
            events=events or {}, notes=notes,
        )
        self._cases[name] = case
        self.save()

    def update_events(self, name: str, events: dict[int, str]):
        """更新案例的已知事件"""
        self._load()
        if name not in self.cases:
            return
        self._cases[name].events.update(events)

    def set_family_context(self, name: str, family_context: dict):
        """设置案例的家境上下文"""
        self._load()
        if name not in self.cases:
            self._cases[name] = CaseRecord(name=name, gender="", birth={})
        self._cases[name].family_context = family_context
        self.save()

    def get_family_context(self, name: str) -> dict | None:
        """获取案例的家境上下文"""
        self._load()
        case = self.cases.get(name)
        return case.family_context if case else None
        self.save()

    def list_cases(self) -> list[dict]:
        """列出所有案例摘要"""
        self._load()
        return [
            {
                "name": c.name,
                "gender": c.gender,
                "birth": c.birth,
                "event_count": len(c.events),
                "signal_count": len(c.verified_signals),
            }
            for c in self.cases.values()
        ]

    # ── 信号验证 ──

    def record_signal(self, name: str, year: int, category: str,
                      predicted: str, actual: str, match: bool):
        """记录一个预测信号与实际结果的对比"""
        self._load()
        if name not in self.cases:
            return
        self._cases[name].verified_signals.append({
            "year": year,
            "category": category,
            "predicted": predicted,
            "actual": actual,
            "match": match,
            "recorded_at": datetime.now().strftime("%Y-%m-%d"),
        })
        self.save()

    # ── 信号对比 ──

    def compare_with_chart(self, name: str, chart) -> list[dict]:
        """将引擎预测与校准记录对比，返回差异报告"""
        self._load()
        case = self._cases.get(name)
        if not case or not case.verified_signals:
            return []

        report = []
        for vs in case.verified_signals:
            yr = vs["year"]
            cat = vs["category"]
            actual = vs["actual"]
            # 找引擎对应该年该类别的预测
            scan_yr = [s for s in chart.annual_scans if s.year == yr]
            if not scan_yr:
                report.append({"year": yr, "category": cat, "status": "no_scan", "actual": actual})
                continue

            ev_cat = [e for e in scan_yr[0].events if e.category == cat]
            if not ev_cat:
                report.append({
                    "year": yr, "category": cat, "status": "no_signal",
                    "predicted": None, "actual": actual,
                    "note": "引擎未检测到该类别信号",
                })
                continue

            ev = ev_cat[0]
            # 判断预测方向与实际是否一致
            # 正面事件(恋爱/高考) + 正面/中性方向 → OK
            # 负面事件(分手/困扰) + 负面方向 → OK
            # 正面事件 + 负面方向 → MISMATCH
            positive_events = {"恋爱", "高考异地", "异性缘大增"}
            negative_events = {"分手", "感情困扰", "人际困扰", "内耗", "学业受阻"}
            neutral_events = {"暂无健康问题"}

            is_positive_actual = actual in positive_events
            is_negative_actual = actual in negative_events

            if ev.direction == "正面" and is_negative_actual:
                match = False
                note = f"引擎判为正面，实际负面({actual})"
            elif ev.direction == "负面" and is_positive_actual:
                match = False
                note = f"引擎判为负面，实际正面({actual})"
            elif ev.direction == "正面" and is_positive_actual:
                match = True
                note = "方向一致"
            elif ev.direction == "负面" and is_negative_actual:
                match = True
                note = "方向一致"
            else:
                match = vs.get("match", True)
                note = "方向中性或无法判定"

            report.append({
                "year": yr, "category": cat,
                "status": "match" if match else "mismatch",
                "predicted": ev.direction,
                "actual": actual,
                "triggers": ev.triggers[:3],
                "note": note,
            })

            # 更新该年份的事件状态
            if cat == "桃花":
                if is_positive_actual:
                    case.events[yr] = "relationship"
                elif is_negative_actual and actual in ("分手",):
                    case.events[yr] = "single"

        self.save()
        return report

    def get_accuracy_report(self) -> dict:
        """生成校准准确率报告"""
        self._load()
        report = {"total": 0, "match": 0, "mismatch": 0, "by_category": {}}
        for case in self._cases.values():
            for vs in case.verified_signals:
                report["total"] += 1
                cat = vs["category"]
                if cat not in report["by_category"]:
                    report["by_category"][cat] = {"match": 0, "total": 0}
                report["by_category"][cat]["total"] += 1
                if vs.get("match", False):
                    report["match"] += 1
                    report["by_category"][cat]["match"] += 1
                else:
                    report["mismatch"] += 1

        if report["total"] > 0:
            report["accuracy"] = round(report["match"] / report["total"], 2)
        for cat in report["by_category"]:
            t = report["by_category"][cat]["total"]
            m = report["by_category"][cat]["match"]
            report["by_category"][cat]["accuracy"] = round(m / t, 2) if t > 0 else 0
        return report

    # ── 规则统计 ──

    def record_rule(self, rule: str, category: str, verified: bool,
                    source: str = "calibration"):
        """记录规则验证结果"""
        self._load()
        if rule not in self.rule_stats:
            self._rule_stats[rule] = RuleStat(rule=rule, category=category, source=source)
        self._rule_stats[rule].total += 1
        if verified:
            self._rule_stats[rule].verified += 1
        self.save()

    def get_rule_stats(self, category: str | None = None) -> list[dict]:
        """获取规则验证统计，可按类别过滤"""
        self._load()
        stats = list(self.rule_stats.values())
        if category:
            stats = [s for s in stats if s.category == category]
        stats.sort(key=lambda s: s.accuracy or 0, reverse=True)
        return [s.to_dict() for s in stats]

    def get_rule_summary(self) -> dict:
        """规则统计总览"""
        self._load()
        stats = list(self.rule_stats.values())
        verified_rules = [s for s in stats if s.total >= 2 and (s.accuracy or 0) >= 1.0]
        pending_rules = [s for s in stats if s.total < 2]
        disputed_rules = [s for s in stats if s.total >= 2 and (s.accuracy or 0) < 1.0]
        return {
            "total_rules": len(stats),
            "verified": len(verified_rules),
            "pending": len(pending_rules),
            "disputed": len(disputed_rules),
            "verified_rules": [s.rule for s in verified_rules],
            "disputed_rules": [s.rule for s in disputed_rules],
        }


# 全局单例
_store: CalibrationStore | None = None


def get_store(path: str | Path | None = None) -> CalibrationStore:
    """获取校准数据库单例"""
    global _store
    if _store is None:
        _store = CalibrationStore(path)
    return _store
