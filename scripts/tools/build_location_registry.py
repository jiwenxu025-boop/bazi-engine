"""Build the runtime location registry from AreaCity level-3 and geo CSV files."""

import argparse
import csv
import hashlib
import json
import math
import sys
from pathlib import Path

_GCJ_A = 6378245.0
_GCJ_EE = 0.00669342162296594323


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _transform_lat(longitude: float, latitude: float) -> float:
    value = -100.0 + 2.0 * longitude + 3.0 * latitude + 0.2 * latitude**2
    value += 0.1 * longitude * latitude + 0.2 * math.sqrt(abs(longitude))
    value += (20.0 * math.sin(6.0 * longitude * math.pi) + 20.0 * math.sin(2.0 * longitude * math.pi)) * 2 / 3
    value += (20.0 * math.sin(latitude * math.pi) + 40.0 * math.sin(latitude / 3 * math.pi)) * 2 / 3
    value += (160.0 * math.sin(latitude / 12 * math.pi) + 320 * math.sin(latitude * math.pi / 30)) * 2 / 3
    return value


def _transform_lon(longitude: float, latitude: float) -> float:
    value = 300.0 + longitude + 2.0 * latitude + 0.1 * longitude**2
    value += 0.1 * longitude * latitude + 0.1 * math.sqrt(abs(longitude))
    value += (20.0 * math.sin(6.0 * longitude * math.pi) + 20.0 * math.sin(2.0 * longitude * math.pi)) * 2 / 3
    value += (20.0 * math.sin(longitude * math.pi) + 40.0 * math.sin(longitude / 3 * math.pi)) * 2 / 3
    value += (150.0 * math.sin(longitude / 12 * math.pi) + 300.0 * math.sin(longitude / 30 * math.pi)) * 2 / 3
    return value


def _gcj02_to_wgs84(longitude: float, latitude: float) -> tuple[float, float]:
    if not (72.004 <= longitude <= 137.8347 and 0.8293 <= latitude <= 55.8271):
        return longitude, latitude
    delta_lat = _transform_lat(longitude - 105.0, latitude - 35.0)
    delta_lon = _transform_lon(longitude - 105.0, latitude - 35.0)
    rad_lat = latitude / 180.0 * math.pi
    magic = 1 - _GCJ_EE * math.sin(rad_lat) ** 2
    sqrt_magic = math.sqrt(magic)
    delta_lat = delta_lat * 180.0 / ((_GCJ_A * (1 - _GCJ_EE)) / (magic * sqrt_magic) * math.pi)
    delta_lon = delta_lon * 180.0 / (_GCJ_A / sqrt_magic * math.cos(rad_lat) * math.pi)
    return longitude - delta_lon, latitude - delta_lat


def _load_coordinates(path: Path) -> dict[str, tuple[float, float] | None]:
    coordinates: dict[str, tuple[float, float] | None] = {}
    with path.open(encoding="utf-8-sig", newline="") as source:
        for row in csv.DictReader(source):
            raw = row["geo"].strip()
            if not raw or raw == "EMPTY":
                coordinates[row["id"]] = None
                continue
            longitude, latitude = (float(value) for value in raw.split())
            coordinates[row["id"]] = _gcj02_to_wgs84(longitude, latitude)
    return coordinates


def _path_parts(row: dict, rows_by_id: dict[str, dict]) -> list[str]:
    parts: list[str] = []
    current: dict | None = row
    while current:
        full_name = current["ext_name"].strip()
        if full_name and (not parts or parts[-1] != full_name):
            parts.append(full_name)
        current = rows_by_id.get(current["pid"])
    return list(reversed(parts))


def build_registry(area_path: Path, geo_path: Path, output_path: Path, version: str) -> dict:
    csv.field_size_limit(2_000_000_000)
    with area_path.open(encoding="utf-8-sig", newline="") as source:
        source_rows = list(csv.DictReader(source))
    rows_by_id = {row["id"]: row for row in source_rows}
    coordinates = _load_coordinates(geo_path)

    records = []
    skipped_fillers = 0
    for row in source_rows:
        level = int(row["deep"])
        if level not in (1, 2) or row["id"].startswith("91"):
            continue
        parent = rows_by_id.get(row["pid"])
        if level == 2 and parent and row["name"] == parent["name"] and row["ext_name"] == parent["ext_name"]:
            skipped_fillers += 1
            continue

        parts = _path_parts(row, rows_by_id)
        coordinate = coordinates.get(row["id"])
        longitude, latitude = coordinate if coordinate else (None, None)
        records.append({
            "id": row["id"],
            "name": row["name"],
            "full_name": row["ext_name"],
            "province": parts[0] if parts else "",
            "path": " ".join(parts),
            "longitude": round(longitude, 6) if longitude is not None else None,
            "latitude": round(latitude, 6) if latitude is not None else None,
            "level": level,
            "pinyin": row["pinyin"],
        })

    records.sort(key=lambda item: int(item["id"]))
    metadata = {
        "schema_version": 1,
        "registry_version": f"cn-divisions-{version}",
        "source_project": "xiangyuecn/AreaCity-JsSpider-StatsGov",
        "source_release": version,
        "source_license": "MIT",
        "area_csv_sha256": _sha256(area_path),
        "geo_csv_sha256": _sha256(geo_path),
        "source_coordinate_system": "GCJ-02",
        "stored_coordinate_system": "WGS84 approximate inverse transform",
        "record_count": len(records),
        "coordinate_count": sum(record["longitude"] is not None for record in records),
        "missing_coordinate_count": sum(record["longitude"] is None for record in records),
        "skipped_structural_fillers": skipped_fillers,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="\n") as output:
        output.write(json.dumps(metadata, ensure_ascii=False, separators=(",", ":")) + "\n")
        for record in records:
            output.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")
    return metadata


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--areas", required=True, type=Path)
    parser.add_argument("--geo", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--version", required=True)
    args = parser.parse_args()
    metadata = build_registry(args.areas, args.geo, args.output, args.version)
    print(json.dumps(metadata, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    sys.exit(main())
