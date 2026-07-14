"""Shared chat test fixtures."""


def chart_data_with_current_dayun():
    return {
        "name": "案例A",
        "gender": "男",
        "birth": "2007-08-26 20:00",
        "day_master": {"stem": "壬", "wuxing": "水", "yinyang": "阳"},
        "pattern": "偏印格",
        "yongshen": {
            "strength": "强",
            "score": 5.5,
            "favorable": ["伤官", "偏官"],
            "harmful": ["偏印"],
        },
        "dayun": {
            "direction": "逆排",
            "start_age": 6,
            "periods": [
                {"order": 1, "age": "6-15岁", "stem": "丁", "branch": "未"},
                {"order": 2, "age": "16-25岁", "stem": "丙", "branch": "午"},
                {"order": 3, "age": "26-35岁", "stem": "乙", "branch": "巳"},
                {"order": 4, "age": "36-45岁", "stem": "甲", "branch": "辰"},
            ],
        },
        "annual_scans": [
            {"year": 2024, "age": 17, "liunian": "甲辰", "dayun": "丙午", "events": []},
            {"year": 2025, "age": 18, "liunian": "乙巳", "dayun": "丙午", "events": []},
            {"year": 2026, "age": 19, "liunian": "丙午", "dayun": "丙午", "events": []},
        ],
    }
