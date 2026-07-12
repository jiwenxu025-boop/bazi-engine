# Bazi Engine Architecture

## Purpose

This project is a rule-first Bazi chart engine with optional LLM assistance. The rule engine owns deterministic chart calculation and event signal detection. LLM code is an auxiliary review and explanation layer, not the source of core chart facts.

## Runtime Entry Points

- `scripts/bazi_engine/api.py`
  - FastAPI application.
  - Serves `/api/health`, `/api/chart`, `/api/chart/stream`, `/api/batch`, `/api/date-pick`, chat endpoints, admin endpoints, and feedback endpoints.
  - Mounts the static frontend at the end of the file so API routes take priority.
- `scripts/bazi_engine/cli.py`
  - Command-line entry point.
  - Calls `build_chart()` and formats either technical or practical text output.
- `frontend/`
  - Static browser UI.
  - Calls `/api/chart/stream` for streamed chart generation, `/api/chat` for follow-up chat, and `/api/personality/fusion/stream` for personality fusion output.

## Core Flow

```text
API / CLI / frontend
  -> build_chart()
    -> compute four pillars
    -> attach hidden stems, ten gods, nayin, minggong, shengong, taiyuan
    -> evaluate yongshen, tiaohou, pattern, health profile
    -> compute dayun and dayun modulation
    -> detect tiangan/dizhi interactions and spirits
    -> optionally scan liunian years
    -> analyze personality, family, palace stars, body-use
    -> BaziChart.to_dict()
```

`scripts/bazi_engine/chart.py` is currently the main orchestration layer. `BaziChart` is the shared in-memory chart object. `build_chart()` is intentionally treated as the public factory contract for API, CLI, and tests.

## Domain Modules

- `pillars.py`
  - Year, month, day, and hour pillar calculation.
- `ten_gods.py`
  - Ten-god relation calculation.
- `pattern.py`
  - Pattern selection and pattern validation.
- `yongshen.py`
  - Strength and favorable/harmful element or ten-god recommendation.
- `tiaohou.py`
  - Seasonal climate analysis, false-generation checks, and health profile helpers.
- `dayun.py`
  - Luck direction, luck pillar generation, start-age calculation, and `DayunModulator`.
- `interactions.py`
  - Heavenly-stem and earthly-branch interactions, tomb clashes, and related modifiers.
- `spirits.py`
  - Spirit detection.
- `personality_analysis/`
  - Personality and family analysis from chart-derived structured data.
- `liunian/`
  - Annual event scanning subsystem.

## Liunian Subsystem

`scripts/bazi_engine/liunian/scanner.py` owns the yearly scan loop.

For each year it:

1. Computes the annual pillar.
2. Selects the active dayun.
3. Runs event detectors from `liunian/events/`.
4. Applies ten-god notes, personality notes, life-stage adjustments, conflict checks, dayun modulation, and sui-yun clash handling.
5. Optionally builds LLM review contexts for boundary cases.
6. Returns `AnnualScan` records.

Event detectors are intentionally split by category:

- `taohua.py`
- `xuesheng.py`
- `hunjia.py`
- `shiye.py`
- `caiyun.py`
- `jiankang.py`
- `banqian.py`
- `zhuangtai.py`
- `renji.py`
- `guanfei.py`

The shared signal model lives in `liunian/signal.py`: `ScoreAccumulator`, `EventSignal`, and `AnnualScan`.

## LLM Boundaries

LLM integration appears in three places:

- `llm_review.py`
  - Reviews boundary annual signals and enriches dayun interpretations.
- `personality_fusion.py`
  - Produces optional fusion-style personality narrative output.
- `chat.py`
  - Handles paid/free follow-up chat.

LLM calls should remain optional. Core chart calculation, four pillars, dayun, pattern, yongshen, and rule-level event signals must remain runnable without network access or API keys.

## Deployment

- `Procfile`
  - Runs `uvicorn` from the `scripts` directory and uses the platform `PORT` value, defaulting to `8080`.
- `Dockerfile`
  - Copies root requirements, `scripts/`, and `frontend/`.
  - Sets `FRONTEND_DIR=/app/frontend` and `BAZI_PUBLIC=true`.
  - Exposes and serves port `7860`.

## Testing Strategy

- Unit tests cover core tables, pillar calculation, signal scoring, liunian helpers, solar terms, API import, and token-budget helpers.
- Calibration tests exercise known-case accuracy thresholds when cases execute successfully.
- Tests that depend on a local calibration store should skip when `scripts/data/calibration_store.json` is absent, but core engine tests must continue to run.
- Local `ruff` requires `PYTHONUTF8=1` on Windows when installing `requirements-dev.txt`, because the requirements file contains UTF-8 comments.
- Current lint baseline is not clean. `RUF001`, `RUF002`, and `RUF003` are ignored because Chinese punctuation is intentional in user-facing strings, docstrings, and comments. Remaining lint debt should be handled separately from rule refactors.

Useful commands:

```powershell
cd C:\Users\21469\bazi-engine\scripts
python -m pytest tests/ -q
python -m pytest tests/test_api.py tests/test_token_budget.py -q
```

## Build Chart Stage Dependencies

`build_chart()` is still the main orchestration function. The early shell, pillar, hidden-stem/nayin, palace-origin, nayin-relation, and yongshen stages are already split into helpers. The remaining stages have these dependencies:

| Stage | Inputs | Writes | Downstream users | Refactor risk |
| --- | --- | --- | --- | --- |
| Tiaohou | `chart.day_master`, month/day branches, `all_stems`, `all_branches` | `chart.tiaohou_result` | health profile, liunian scan, personality validation, LLM context | Low |
| Health profile | `chart.tiaohou_result`, `all_branches`, `chart.day_master` | `chart.health_profile` | liunian scan, user output | Low |
| Ten gods | day master, pillar stems, hidden stems | per-pillar `ten_god`, `ten_gods_map` | output serialization, personality/family analysis | Low |
| Pattern | month branch, `all_stems`, day master, yongshen `cong_ge` | `chart.pattern`, `chart.pattern_notes` | pattern yongshen, liunian scan, life-stage, personality/family analysis | Medium |
| Pattern yongshen | `chart.pattern`, day master, existing `_yongshen_result` | `_yongshen_result["pattern_yongshen"]` | output serialization, personality/family analysis | Medium |
| Void gods | day master, month branch, `all_stems`, yongshen favorable ten gods | `chart.void_gods` | output serialization | Low |
| Dayun | year stem, gender, month pillar, birth datetime | direction, luck pillars, start age, luck periods | dayun modulation, liunian scan, life-stage, body-use | Medium |
| Dayun modulation | day master, natal pillars, luck pillars, yongshen favorable/harmful data | `chart.dayun_modulations` | liunian scan, output serialization | Medium |
| Interactions | natal stems/branches with pillar labels | `tiangan_interactions`, `dizhi_interactions`, `tansheng_wangke`, `false_generations` | spirits, liunian scan, personality/family analysis, LLM context | Medium |
| Spirits | day master, year stem, year/day branches, branch labels | `chart.spirits` | palace-star analysis, output serialization | Low |
| Liunian scan | natal branches, gender, start age, luck pillars, known events, yongshen, pattern, tiaohou, dayun modulation, interactions, health profile | `chart.annual_scans` | changsheng, life-stage, body-use, output serialization | High |
| Changsheng | day master, natal branches, luck pillars, annual scans | `chart.changsheng_states` | output serialization | Medium |
| Life stage | override or current age, start age, luck pillars, annual scans, pattern | `chart.life_stage` | output serialization, analysis context | Medium |
| Personality and family | chart-derived pillar data, yongshen, pattern, interactions, tiaohou, family context | `chart.personality_result`, `chart.family_result` | palace/body analysis, output serialization | High |
| Palace stars | analysis pillar data, spirits, day master | `chart.palace_star_result` | output serialization | Medium |
| Body-use | analysis pillar data, interactions, luck pillars, annual scans | `chart.body_use_result` | output serialization | Medium |

Recommended next extraction: combine the Tiaohou and health-profile code into one helper only after adding a behavior test. This stage has explicit inputs, writes isolated chart fields, and feeds later stages without mutating shared rule data.

## Refactoring Rules

- Keep `build_chart()` input and output stable unless API and CLI callers are updated together.
- Split orchestration into stages before moving code across files.
- Do not change prediction thresholds during structural refactors.
- Any rule change needs a failing test or calibration case first.
- After rule changes, run the relevant calibration scripts in addition to pytest.
