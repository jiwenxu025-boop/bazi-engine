"""Personality fusion package tests."""

from bazi_engine.personality_fusion import build_fusion_data_package


def test_build_fusion_data_package_excludes_unreviewed_sub_traits():
    package = build_fusion_data_package(
        {
            "sub_traits": [
                {"trait_name": "多疑敏感", "description": "desc", "shishen": "偏印", "score": 1},
                {"trait_name": "依赖性强", "description": "desc", "shishen": "偏印", "score": 1},
                {"trait_name": "不善表达情感", "description": "desc", "shishen": "偏印", "score": 1},
                {"trait_name": "保守求稳", "description": "desc", "shishen": "正印", "score": 1},
                {"trait_name": "慷慨大方", "description": "desc", "shishen": "偏财", "score": 1},
            ]
        }
    )

    assert "粒度性格特质" not in package
    for unsafe_trait in ("多疑敏感", "依赖性强", "不善表达情感", "保守求稳", "慷慨大方"):
        assert unsafe_trait not in str(package)


def test_build_fusion_data_package_excludes_unreviewed_sources_and_directives():
    package = build_fusion_data_package(
        {
            "day_master_core": {"五行": "水", "阴阳": "阳", "负面": "诡诈狠戾"},
            "strength_label": "偏强（7.2分）",
            "pattern_validation": {"status": "成格", "note": "压力喂养安全系统"},
            "bingyao_combos": [{"combo": "印重身滞", "directive": "唯一破局：马上行动"}],
            "special_combos": ["克夫倾向", "食神制杀"],
            "sub_traits": [
                {"trait_name": "杀伐决断", "description": "desc", "shishen": "偏官", "score": 8.0},
                {"trait_name": "匠心独运", "description": "desc", "source_type": "月支藏干", "score": 2.5},
            ],
            "combo_traits": [{"trait": "天才型人格", "description": "desc"}],
            "dizhi_traits": [{"trait": "多自刑", "description": "敏感多思"}],
            "weighted_shishen": {"scores": {"偏官": 8.0}},
            "trait_signals": {"决策": {"果断度_七杀": 8.0, "综合倾向": "果断"}},
        },
        family_dict={"childhood": "童年动荡"},
    )

    text = str(package)
    assert package["组合候选"] == [{"名称": "印重身滞", "证据等级": "工程规则候选"}]
    assert package["日主画像"] == {"五行": "水", "阴阳": "阳", "身强弱": "偏强"}
    assert "粒度性格特质" not in package
    assert "全局最高指令" not in package
    assert "马上行动" not in text
    assert "特殊组合" not in text
    assert "天才型人格" not in text
    assert "多自刑" not in text
    assert "童年动荡" not in text


def test_fusion_package_can_use_reviewed_evidence_from_practical_api_payload():
    package = build_fusion_data_package({
        "evidence_view": {
            "status": {"strength": "偏强（7.2分）", "pattern": "偏印格", "pattern_status": "成格"},
            "weighted_scores": [
                {"name": "偏印", "score": 8.0, "level": "较强", "breakdown": {"hidden": 2.0}},
            ],
            "dimensions": {
                "决策": {
                    "summary": "分析后决策",
                    "signals": [
                        {
                            "label": "分析度_印星",
                            "display_label": "信息分析",
                            "kind": "weighted_score",
                            "value": 8.0,
                            "level": "较强",
                        },
                    ],
                },
                "事业": {
                    "summary": "技术/创意",
                    "secondary": "学术/专业",
                    "comparison": "方向接近",
                    "signals": [
                        {"label": "技术_创意", "display_label": "技术创意", "kind": "relative_score", "value": 8.0},
                    ],
                },
            },
        },
    })

    assert package["日主画像"] == {"身强弱": "偏强"}
    assert package["格局状态"] == {
        "证据等级": "传统结构候选",
        "名称": "偏印格",
        "判定": "成格",
        "使用边界": "仍不能单独推导现代人格",
    }
    assert package["十神强度排行"] == [{"十神": "偏印", "工程强度档": "较强"}]
    assert package["六维度信号"]["决策"] == {
        "综合倾向": "分析后决策",
        "强度信号": {"信息分析": "较强"},
    }
    assert package["六维度信号"]["事业"] == {
        "综合倾向": "技术/创意",
        "次要方向": "学术/专业",
        "方向关系": "方向接近",
        "候选方向排序": ["技术创意"],
    }
    assert "8.0" not in str(package)
