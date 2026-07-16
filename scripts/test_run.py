"""Manual diagnostic runner. Invoke directly; pytest must not execute it on import."""

import os

from bazi_engine.chart import build_chart


def main() -> None:
    os.environ["BAZI_FUSION_ENGINE"] = "1"
    os.environ["BAZI_LLM_REVIEW"] = "0"

    chart = build_chart("test", "男", 2007, 8, 26, 20, liunian_range=(2023, 2030))
    personality = chart.personality_result
    lines = ["=== profile ===", str(personality.get("profile", "")), "", "=== traits ==="]
    for key, value in personality.get("traits", {}).items():
        lines.append(f"  [{key}] {value}")
    lines.extend(("", "=== day_master_core ===", str(personality.get("day_master_core", ""))[:300], ""))
    lines.append("=== bingyao ===")
    for combo in personality.get("bingyao_combos", []):
        lines.append("  {}: {}".format(combo["combo"], str(combo["directive"])[:200]))
    lines.append("")
    lines.append("=== weighted_shishen top5 ===")
    scores = personality.get("weighted_shishen", {}).get("scores", {})
    for name, score in sorted(scores.items(), key=lambda item: item[1], reverse=True)[:5]:
        lines.append(f"  {name}: {score}")
    yongshen = chart._yongshen_result or {}
    lines.extend((
        "", f"=== pattern: {chart.pattern} ===", "",
        f"=== strength: {yongshen.get('strength', '?')} ({yongshen.get('score', '?')}) ===",
        "fav shishen: {}".format(yongshen.get("favorable", [])),
        "harm shishen: {}".format(yongshen.get("harmful", [])),
    ))
    with open("test_output.txt", "w", encoding="utf-8") as output:
        output.write("\n".join(lines))
    print("Done. See test_output.txt")


if __name__ == "__main__":
    main()
