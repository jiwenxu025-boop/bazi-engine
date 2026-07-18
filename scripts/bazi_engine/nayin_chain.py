"""Compatibility helpers for raw pillar Nayin labels.

Derived Nayin chains previously generated claims about wealth, ancestors, and
life outcomes. Those claims are disabled until their sources and counterexamples
are reviewed. Raw Nayin labels remain available on each pillar.
"""

from dataclasses import dataclass

from .enums import Wuxing


def nayin_to_wuxing(nayin_name: str) -> Wuxing | None:
    """Return the Wuxing named by a raw Nayin label, when available."""
    if not nayin_name:
        return None
    return {
        "金": Wuxing.金,
        "木": Wuxing.木,
        "水": Wuxing.水,
        "火": Wuxing.火,
        "土": Wuxing.土,
    }.get(nayin_name[-1])


@dataclass
class NayinRelation:
    """Retained type for callers that only consume serialized relations."""

    relation_type: str
    from_pillar: str
    to_pillar: str
    from_nayin: str
    to_nayin: str
    chain_order: str = ""
    interpretation: str = ""
    auspiciousness: str = ""

    def to_dict(self) -> dict:
        return {
            "relation_type": self.relation_type,
            "from_pillar": self.from_pillar,
            "to_pillar": self.to_pillar,
            "from_nayin": self.from_nayin,
            "to_nayin": self.to_nayin,
            "chain_order": self.chain_order,
            "interpretation": self.interpretation,
            "auspiciousness": self.auspiciousness,
        }


def find_all_nayin_relations(
    year_nayin: str,
    month_nayin: str,
    day_nayin: str,
    hour_nayin: str,
) -> list[NayinRelation]:
    """Do not generate derived Nayin relationship conclusions."""
    del year_nayin, month_nayin, day_nayin, hour_nayin
    return []
