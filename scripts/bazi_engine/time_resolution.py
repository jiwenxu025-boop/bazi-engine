"""Resolve birth-time inputs into physical and pillar-calculation timelines."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from math import cos, pi, sin

from .locations import CityRecord, get_city

CHINA_STANDARD_TIME_OFFSET_MINUTES = 480
_VALID_TIME_MODES = {"auto", "true_solar", "civil_input"}
_VALID_TIME_ACCURACY = {"minute", "hour", "unknown"}


@dataclass(frozen=True)
class BirthTimeResolution:
    """Separate the moment of birth from the time used to form day/hour pillars."""

    input_civil_dt: datetime
    birth_instant_utc: datetime
    birth_instant_cst: datetime
    pillar_dt: datetime
    requested_time_mode: str
    effective_time_mode: str
    time_accuracy: str
    timezone_offset_minutes: int
    city: CityRecord | None
    longitude: float | None
    longitude_source: str
    equation_of_time_minutes: float
    longitude_correction_minutes: float
    solar_correction_minutes: float

    @property
    def day_pillar_uses_next_date(self) -> bool:
        return self.pillar_dt.hour >= 23

    @property
    def pillar_date_adjusted(self) -> bool:
        return self.pillar_dt.date() != self.input_civil_dt.date()

    def to_report_input(self) -> dict:
        city = self.city.to_dict() if self.city else None
        return {
            "birth_time": self.input_civil_dt.strftime("%Y-%m-%d %H:%M"),
            "time_accuracy": self.time_accuracy,
            "requested_time_mode": self.requested_time_mode,
            "effective_time_mode": self.effective_time_mode,
            "city": city,
            "timezone_offset_minutes": self.timezone_offset_minutes,
            "birth_instant_utc": self.birth_instant_utc.strftime("%Y-%m-%d %H:%M"),
            "pillar_time": self.pillar_dt.strftime("%Y-%m-%d %H:%M"),
            "longitude": self.longitude,
            "longitude_source": self.longitude_source,
            "equation_of_time_minutes": round(self.equation_of_time_minutes, 2),
            "longitude_correction_minutes": round(self.longitude_correction_minutes, 2),
            "solar_correction_minutes": round(self.solar_correction_minutes, 2),
            "day_pillar_uses_next_date": self.day_pillar_uses_next_date,
        }

    def to_preview(self) -> dict:
        return {
            "effective_time_mode": self.effective_time_mode,
            "input_time": self.input_civil_dt.strftime("%Y-%m-%d %H:%M"),
            "pillar_time": self.pillar_dt.strftime("%Y-%m-%d %H:%M"),
            "solar_correction_minutes": round(self.solar_correction_minutes, 2),
            "day_pillar_uses_next_date": self.day_pillar_uses_next_date,
            "city": self.city.to_dict() if self.city else None,
        }


def equation_of_time_minutes(local_dt: datetime) -> float:
    """NOAA's standard equation-of-time approximation (minutes)."""
    day_of_year = local_dt.timetuple().tm_yday
    local_hours = local_dt.hour + local_dt.minute / 60
    gamma = 2 * pi / 365 * (day_of_year - 1 + (local_hours - 12) / 24)
    return 229.18 * (
        0.000075
        + 0.001868 * cos(gamma)
        - 0.032077 * sin(gamma)
        - 0.014615 * cos(2 * gamma)
        - 0.040849 * sin(2 * gamma)
    )


def resolve_birth_time(
    *,
    year: int,
    month: int,
    day: int,
    hour: int,
    minute: int = 0,
    city_id: str | None = None,
    longitude: float | None = None,
    timezone_offset_minutes: int | None = None,
    requested_time_mode: str = "auto",
    time_accuracy: str = "minute",
) -> BirthTimeResolution:
    """Resolve user input without treating a city-less time as a precise location."""
    if requested_time_mode not in _VALID_TIME_MODES:
        raise ValueError("时间模式必须是 auto、true_solar 或 civil_input")
    if time_accuracy not in _VALID_TIME_ACCURACY:
        raise ValueError("出生记录精度必须是 minute、hour 或 unknown")
    if timezone_offset_minutes is not None and not -720 <= timezone_offset_minutes <= 840:
        raise ValueError("时区偏移必须在 -720 到 840 分钟之间")
    if longitude is not None and not -180 <= longitude <= 180:
        raise ValueError("经度必须在 -180 到 180 度之间")

    city = get_city(city_id)
    if city_id and city is None:
        raise ValueError("所选城市不在当前离线城市清单中，请重新选择或使用未知城市")

    input_civil_dt = datetime(year, month, day, hour, minute)
    timezone_offset = timezone_offset_minutes
    if timezone_offset is None:
        timezone_offset = city.timezone_offset_minutes if city else CHINA_STANDARD_TIME_OFFSET_MINUTES

    effective_longitude = longitude if longitude is not None else (city.longitude if city else None)
    longitude_source = (
        "manual"
        if longitude is not None
        else ("city_registry" if city and city.longitude is not None else "unknown")
    )
    if requested_time_mode == "auto":
        effective_time_mode = "true_solar" if effective_longitude is not None else "civil_input"
    else:
        effective_time_mode = requested_time_mode
    if effective_time_mode == "true_solar" and effective_longitude is None:
        raise ValueError("真太阳时需要选择内置城市或填写手动经度")

    birth_instant_utc = input_civil_dt - timedelta(minutes=timezone_offset)
    birth_instant_cst = birth_instant_utc + timedelta(minutes=CHINA_STANDARD_TIME_OFFSET_MINUTES)
    eot = 0.0
    longitude_correction = 0.0
    solar_correction = 0.0
    pillar_dt = input_civil_dt
    if effective_time_mode == "true_solar":
        eot = equation_of_time_minutes(input_civil_dt)
        timezone_meridian = timezone_offset / 60 * 15
        longitude_correction = (effective_longitude - timezone_meridian) * 4
        solar_correction = eot + longitude_correction
        pillar_dt = input_civil_dt + timedelta(minutes=solar_correction)

    return BirthTimeResolution(
        input_civil_dt=input_civil_dt,
        birth_instant_utc=birth_instant_utc,
        birth_instant_cst=birth_instant_cst,
        pillar_dt=pillar_dt,
        requested_time_mode=requested_time_mode,
        effective_time_mode=effective_time_mode,
        time_accuracy=time_accuracy,
        timezone_offset_minutes=timezone_offset,
        city=city,
        longitude=effective_longitude,
        longitude_source=longitude_source,
        equation_of_time_minutes=eot,
        longitude_correction_minutes=longitude_correction,
        solar_correction_minutes=solar_correction,
    )
