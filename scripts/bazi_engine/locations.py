"""Versioned, offline nationwide birth-place registry."""

import json
from dataclasses import dataclass
from pathlib import Path

_DATA_FILE = Path(__file__).with_name("resources") / "cn_divisions.jsonl"


@dataclass(frozen=True)
class CityRecord:
    id: str
    name: str
    full_name: str
    province: str
    path: str
    longitude: float | None
    latitude: float | None
    level: int
    pinyin: str
    timezone_offset_minutes: int = 480

    @property
    def label(self) -> str:
        return self.path or self.full_name

    @property
    def has_coordinates(self) -> bool:
        return self.longitude is not None and self.latitude is not None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "full_name": self.full_name,
            "province": self.province,
            "label": self.label,
            "longitude": self.longitude,
            "latitude": self.latitude,
            "level": self.level,
            "has_coordinates": self.has_coordinates,
            "timezone_offset_minutes": self.timezone_offset_minutes,
        }


def _load_registry() -> tuple[dict, tuple[CityRecord, ...]]:
    metadata: dict | None = None
    records: list[CityRecord] = []
    with _DATA_FILE.open(encoding="utf-8") as source:
        for line_number, line in enumerate(source, start=1):
            payload = json.loads(line)
            if line_number == 1:
                metadata = payload
                continue
            records.append(CityRecord(**payload))
    if not metadata or metadata.get("schema_version") != 1:
        raise RuntimeError("全国出生地数据文件缺少有效元数据")
    record_ids = [record.id for record in records]
    if len(records) != metadata.get("record_count"):
        raise RuntimeError("全国出生地数据文件记录数与元数据不一致")
    if len(record_ids) != len(set(record_ids)):
        raise RuntimeError("全国出生地数据文件包含重复行政代码")
    coordinate_count = sum(record.has_coordinates for record in records)
    if coordinate_count != metadata.get("coordinate_count"):
        raise RuntimeError("全国出生地数据文件坐标统计与元数据不一致")
    return metadata, tuple(records)


REGISTRY_METADATA, CITY_REGISTRY = _load_registry()
REGISTRY_VERSION = str(REGISTRY_METADATA["registry_version"])
_CITY_BY_ID = {city.id: city for city in CITY_REGISTRY}


def _normalize(value: str) -> str:
    return "".join(char for char in value.casefold().strip() if char not in " -_'·")


def _candidate_terms(city: CityRecord) -> tuple[str, ...]:
    return (
        city.id,
        city.name,
        city.full_name,
        city.province,
        city.path,
        city.pinyin,
        city.pinyin.replace(" ", ""),
    )


def _best_named_city(name: str, *, province: str = "") -> CityRecord | None:
    candidates = [
        city for city in CITY_REGISTRY
        if city.name == name and (not province or city.province == province)
    ]
    return min(candidates, key=lambda city: (city.level != 1, city.level, city.id), default=None)


_LEGACY_NAME_ALIASES = {
    "harbin": ("哈尔滨", ""),
    "hohhot": ("呼和浩特", ""),
    "urumqi": ("乌鲁木齐", ""),
    "kashgar": ("喀什", ""),
    "lhasa": ("拉萨", ""),
    "hongkong": ("香港", ""),
    "macau": ("澳门", ""),
    "taipei": ("台北", ""),
    "kaohsiung": ("高雄", ""),
    "taizhouzj": ("台州", "浙江省"),
}


def get_city(city_id: str | None) -> CityRecord | None:
    raw = (city_id or "").strip()
    if not raw:
        return None
    if raw in _CITY_BY_ID:
        return _CITY_BY_ID[raw]

    normalized = _normalize(raw)
    legacy = _LEGACY_NAME_ALIASES.get(normalized)
    if legacy:
        return _best_named_city(legacy[0], province=legacy[1])

    exact_matches = [
        city for city in CITY_REGISTRY
        if any(_normalize(term) == normalized for term in _candidate_terms(city))
    ]
    return min(exact_matches, key=lambda city: (city.level != 1, city.level, city.id), default=None)


def search_cities(query: str, *, limit: int = 12) -> list[CityRecord]:
    normalized = _normalize(query)
    if not normalized:
        return [city for city in CITY_REGISTRY if city.level == 1][:limit]

    matches: list[tuple[int, int, str, CityRecord]] = []
    for city in CITY_REGISTRY:
        terms = tuple(_normalize(term) for term in _candidate_terms(city))
        if normalized in terms:
            match_rank = 0
        elif any(term.startswith(normalized) for term in terms):
            match_rank = 1
        elif any(normalized in term for term in terms):
            match_rank = 2
        else:
            continue
        matches.append((match_rank, city.level, city.pinyin, city))
    matches.sort(key=lambda item: (item[0], item[1], item[2], item[3].id))
    results = [item[3] for item in matches]
    legacy = _LEGACY_NAME_ALIASES.get(normalized)
    if legacy:
        legacy_city = _best_named_city(legacy[0], province=legacy[1])
        if legacy_city:
            results = [legacy_city, *(city for city in results if city.id != legacy_city.id)]
    return results[:limit]
