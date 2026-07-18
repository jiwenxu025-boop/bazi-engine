"""Calibration dataset-contract regression tests."""

import pytest

from bazi_engine.calibration import CalibrationStore, CaseRecord, RuleStat


def test_case_record_round_trips_holdout_evidence():
    record = CaseRecord(
        name="holdout-case",
        gender="男",
        birth={"year": 1990, "month": 1, "day": 2, "hour": 3},
        events={2024: "事业"},
        dataset="holdout",
        source_ref="匿名访谈记录#42",
        source_confidence="本人确认",
        event_details={2024: {"direction": "负面", "note": "被动离职"}},
        negative_years=[2022, 2023],
    )

    restored = CaseRecord.from_dict(record.to_dict())

    assert restored.dataset == "holdout"
    assert restored.event_details[2024]["direction"] == "负面"
    assert restored.negative_years == [2022, 2023]
    assert restored.holdout_validation_issues() == []


def test_holdout_readiness_reports_missing_evidence(tmp_path):
    store = CalibrationStore(tmp_path / "calibration_store.json")
    store.add_case(
        "incomplete-holdout",
        "女",
        {"year": 1992, "month": 4, "day": 5, "hour": 6},
        {2024: "财运"},
        dataset="holdout",
    )

    report = store.holdout_readiness_report()

    assert report["total"] == 1
    assert report["ready"] == 0
    assert "incomplete-holdout" in report["issues"]


def test_locked_holdout_cannot_be_overwritten_or_used_in_development_report(tmp_path):
    store = CalibrationStore(tmp_path / "calibration_store.json")
    evidence = {
        "dataset": "holdout",
        "source_ref": "匿名访谈记录#43",
        "source_confidence": "本人确认",
        "event_details": {2024: {"direction": "正面"}},
    }
    store.add_case(
        "locked-holdout", "男", {"year": 1990, "month": 1, "day": 2, "hour": 3},
        {2024: "事业"}, **evidence,
    )
    store.record_signal("locked-holdout", 2024, "事业", "正面", "升职", True)

    with pytest.raises(ValueError, match="不可覆盖"):
        store.add_case(
            "locked-holdout", "男", {"year": 1990, "month": 1, "day": 2, "hour": 3},
            {2024: "事业"}, notes="rewritten", **evidence,
        )
    with pytest.raises(ValueError, match="不可修改事件"):
        store.update_events("locked-holdout", {2025: "财运"})

    assert store.get_known_events("locked-holdout") is None
    assert store.get_signal_agreement_report(dataset="development")["total"] == 0
    assert store.get_signal_agreement_report(dataset="holdout")["agreement_rate"] == 1.0


def test_rule_stats_expose_agreement_rate_not_accuracy_label():
    stat = RuleStat(rule="test-rule", category="事业", verified=3, total=4)

    assert stat.agreement_rate == 0.75
    assert "agreement_rate" in stat.to_dict()
    assert "accuracy" not in stat.to_dict()
