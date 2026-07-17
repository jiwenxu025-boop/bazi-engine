from bazi_engine.enums import Dizhi
from bazi_engine.interactions import Interaction
from bazi_engine.personality_analysis.traits import _compute_dizhi_traits


def _pillars(*branches: str) -> list[dict]:
    labels = ("年柱", "月柱", "日柱", "时柱")
    return [
        {"pillar_type": label, "branch": branch}
        for label, branch in zip(labels, branches, strict=False)
    ]


def test_dizhi_traits_read_interaction_participants() -> None:
    interactions = {
        "dizhi": [
            Interaction(
                inter_type="六冲",
                participants=(Dizhi.子, Dizhi.午),
                pillar_labels=("年柱", "月柱"),
            ).to_dict(),
            Interaction(
                inter_type="自刑",
                participants=(Dizhi.辰,),
                pillar_labels=("日柱", "时柱"),
            ).to_dict(),
        ]
    }

    results = _compute_dizhi_traits(
        interactions,
        _pillars("子", "午", "辰", "辰"),
    )
    by_relation = {result["relation"]: result for result in results}

    assert "子午六冲" in by_relation
    assert by_relation["子午六冲"]["involved_pillars"] == ["年柱", "月柱"]
    assert "辰自刑" in by_relation
    assert by_relation["辰自刑"]["involved_pillars"] == ["日柱", "时柱"]
    assert "多自刑" in by_relation


def test_distinct_self_punishment_branches_do_not_count_as_multiple() -> None:
    results = _compute_dizhi_traits(
        {"dizhi": []},
        _pillars("辰", "午"),
    )

    assert all(result["relation"] != "多自刑" for result in results)


def test_legacy_branches_field_remains_supported() -> None:
    interactions = {
        "dizhi": [
            {
                "type": "六冲",
                "branches": ["卯", "酉"],
                "pillars": ["年柱", "月柱"],
            },
            {
                "type": "自刑",
                "branches": ["亥"],
                "pillars": ["日柱", "时柱"],
            },
        ]
    }

    results = _compute_dizhi_traits(
        interactions,
        _pillars("卯", "酉", "亥", "亥"),
    )
    relations = {result["relation"] for result in results}

    assert {"卯酉六冲", "亥自刑", "多自刑"} <= relations
