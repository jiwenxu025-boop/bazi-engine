"""排盘与择日的节气、夜子时和60甲子边界回归。"""

from datetime import date

from bazi_engine.date_picker import _day_ganzhi, _month_dz, _xun_index
from bazi_engine.dayun import compute_jiaoyun_detail, compute_start_age_exact
from bazi_engine.enums import Dizhi, Tiangan, dizhi_by_index, tiangan_by_index
from bazi_engine.liunian.scanner import scan_years
from bazi_engine.pillars import build_four_pillars, compute_day_pillar, compute_month_pillar


def test_month_pillar_uses_jieqi_and_twelve_month_offset():
    assert compute_month_pillar(Tiangan.癸, 1, 1, gregorian_year=2024)[:2] == (Tiangan.甲, Dizhi.子)
    assert compute_month_pillar(Tiangan.癸, 1, 7, gregorian_year=2024)[:2] == (Tiangan.乙, Dizhi.丑)
    assert compute_month_pillar(Tiangan.甲, 12, 10, gregorian_year=2024)[:2] == (Tiangan.丙, Dizhi.子)


def test_build_four_pillars_passes_year_to_month_calculation():
    pillars = build_four_pillars(2024, 1, 1, 12)
    assert pillars["month"] == (Tiangan.甲, Dizhi.子)


def test_night_zi_uses_next_day_for_day_and_hour_pillars():
    pillars = build_four_pillars(2024, 5, 10, 23)
    next_day_stem, next_day_branch, _ = compute_day_pillar(2024, 5, 11)

    assert pillars["day"][:2] == (next_day_stem, next_day_branch)
    assert pillars["hour_zi_flag"] == "夜子时"
    assert any("夜子时" in warning for warning in pillars["warnings"])


def test_date_picker_uses_shared_day_and_jieqi_rules():
    assert _day_ganzhi(date(2007, 8, 26)) == compute_day_pillar(2007, 8, 26)[:2]
    assert _month_dz(date(2024, 1, 1)) == Dizhi.子
    assert _month_dz(date(2024, 1, 7)) == Dizhi.丑


def test_xun_index_is_correct_for_every_valid_sexagenary_day():
    for index in range(60):
        assert _xun_index(tiangan_by_index(index), dizhi_by_index(index)) == index // 10


def test_jiaoyun_detail_preserves_a_fractional_start_age():
    from datetime import datetime

    birth = datetime(2007, 8, 26, 20)
    exact, _warnings = compute_start_age_exact(birth, "逆排")
    detail, _warnings = compute_jiaoyun_detail(birth, "逆排")

    assert exact % 1 != 0
    assert detail["start_age_exact"] == round(exact * 12) / 12


def test_annual_scan_does_not_assign_dayun_before_or_during_jiaoyun_year():
    scans = scan_years(
        Tiangan.甲, Dizhi.子, Dizhi.子, Dizhi.寅, Dizhi.卯, "男",
        start_age=3,
        start_age_exact=3.5,
        luck_pillars=[(Tiangan.乙, Dizhi.丑)],
        birth_date=date(2020, 1, 1),
        start_year=2022,
        end_year=2024,
    )

    assert scans[0].dayun_stem is None
    assert "未交大运" in scans[0].dayun_weight_note
    assert scans[1].dayun_stem is None
    assert "本年交运" in scans[1].dayun_weight_note
    assert scans[2].dayun_stem == Tiangan.乙
