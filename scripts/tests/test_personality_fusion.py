"""Personality fusion package tests."""

from bazi_engine.personality_fusion import build_fusion_data_package


def test_build_fusion_data_package_merges_repeated_trait_dimensions():
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

    traits = {
        item["特质"]: item["所属维度"]
        for item in package["粒度性格特质"]["十神加权特质"]
    }
    assert traits["多疑敏感"] == ["内心", "社交", "感情"]
    assert traits["依赖性强"] == ["社交", "内心", "感情"]
    assert traits["不善表达情感"] == ["社交", "内心", "感情"]
    assert traits["保守求稳"] == ["内心", "决策", "感情"]
    assert traits["慷慨大方"] == ["财富观", "感情"]
