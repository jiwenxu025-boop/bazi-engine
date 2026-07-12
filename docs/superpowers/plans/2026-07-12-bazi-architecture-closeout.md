# Bazi Architecture Closeout Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Finish the architecture refactor closeout by aligning docs, reducing stage-test duplication, adding a public `build_chart()` regression test, and recording current lint debt without changing prediction rules.

**Architecture:** Keep `build_chart()` as the public factory and keep extracted `_compute_*_stage()` helpers as orchestration boundaries in `scripts/bazi_engine/chart.py`. Tests should verify deterministic output shape and key fields, not freeze long narrative text. Lint debt is documented separately from rule or orchestration changes.

**Tech Stack:** Python 3.13, pytest, ruff, FastAPI, existing `bazi_engine` modules.

---

### Task 1: Align Architecture Documentation

**Files:**
- Modify: `docs/architecture.md`
- Read: `scripts/bazi_engine/chart.py`

- [ ] **Step 1: Update core-flow wording**

Revise the `Core Flow` section so it lists the extracted stages now present in `build_chart()`: shell/input state, four pillars, hidden stems/nayin, palace origins, nayin relations, yongshen, tiaohou/health, ten gods, pattern, void gods, dayun, dayun modulation, interactions, spirits, optional liunian, changsheng, life stage, personality/family, palace stars, body-use.

- [ ] **Step 2: Replace stale recommendation**

Replace the old “Recommended next extraction” paragraph with a “Current orchestration status” paragraph that says these stages are now helper boundaries and that the next structural work should focus on moving cohesive helpers to modules only when there is a concrete maintenance need.

- [ ] **Step 3: Verify docs-only change**

Run:

```powershell
git diff -- docs/architecture.md
```

Expected: only architecture documentation changes.

- [ ] **Step 4: Commit**

Run:

```powershell
git add docs/architecture.md docs/superpowers/plans/2026-07-12-bazi-architecture-closeout.md
git commit -m "docs: close out bazi architecture plan"
```

Expected: one docs-only commit.

### Task 2: Reduce Stage-Test Setup Duplication

**Files:**
- Modify: `scripts/tests/test_chart_stages.py`

- [ ] **Step 1: Add reusable chart setup helpers**

Add focused helpers near the top of `test_chart_stages.py`:

```python
def _case_a_chart():
    return _init_chart_shell(...)

def _prepare_case_a_through_spirits():
    chart = _case_a_chart()
    ...
    return chart, start_age, all_branches, branch_labels

def _prepare_case_a_through_liunian(liunian_range=(2023, 2024)):
    chart, start_age, _, _ = _prepare_case_a_through_spirits()
    _compute_liunian_stage(...)
    return chart, start_age
```

Use the exact existing `案例A` birth data and existing helper calls.

- [ ] **Step 2: Replace repeated setup in late-stage tests**

Refactor the liunian, changsheng, life-stage, personality/family, palace-star, and body-use tests to use these helpers. Keep assertions unchanged except where local variables become unnecessary.

- [ ] **Step 3: Run stage tests**

Run:

```powershell
cd C:\Users\21469\bazi-engine\scripts
python -m pytest tests/test_chart_stages.py -q
```

Expected: all stage tests pass.

- [ ] **Step 4: Run full tests**

Run:

```powershell
cd C:\Users\21469\bazi-engine\scripts
python -m pytest tests/ -q
```

Expected: full suite passes with the existing skip count.

- [ ] **Step 5: Commit**

Run:

```powershell
git add scripts/tests/test_chart_stages.py
git commit -m "test: share bazi chart stage fixtures"
```

Expected: one test-only commit.

### Task 3: Add Public `build_chart()` Regression Test

**Files:**
- Modify: `scripts/tests/test_chart_stages.py`

- [ ] **Step 1: Add import**

Import `build_chart` from `bazi_engine.chart`.

- [ ] **Step 2: Add regression test**

Add a test that disables LLM/fusion via `monkeypatch`, calls:

```python
chart = build_chart("案例A", "男", 2007, 8, 26, 20, liunian_range=(2023, 2024))
data = chart.to_dict()
```

Assert stable top-level output:

```python
assert data["name"] == "案例A"
assert data["four_pillars"]["year"]["stem"] == "丁"
assert data["four_pillars"]["day"]["stem"] == "壬"
assert len(data["luck_pillars"]) == 8
assert len(data["annual_scans"]) == 2
assert len(data["changsheng"]) == 14
assert data["personality"]
assert data["family"]
assert len(data["palace_star"]["entries"]) == 4
assert data["body_use"]["body_count"] == 1
assert data["body_use"]["use_count"] == 2
```

- [ ] **Step 3: Run target test**

Run:

```powershell
cd C:\Users\21469\bazi-engine\scripts
python -m pytest tests/test_chart_stages.py::test_build_chart_returns_full_analysis_shape_for_known_case -q
```

Expected: the new regression test passes.

- [ ] **Step 4: Run full tests**

Run:

```powershell
cd C:\Users\21469\bazi-engine\scripts
python -m pytest tests/ -q
```

Expected: full suite passes.

- [ ] **Step 5: Commit**

Run:

```powershell
git add scripts/tests/test_chart_stages.py
git commit -m "test: cover build chart full output shape"
```

Expected: one test commit.

### Task 4: Record Existing Lint Debt

**Files:**
- Create or modify: `docs/lint-debt.md`

- [ ] **Step 1: Capture current targeted lint output**

Run:

```powershell
cd C:\Users\21469\bazi-engine
python -m ruff check scripts --select F821,F601,B023 --statistics
```

Expected: current known baseline is 26 errors: 16 `B023`, 8 `F601`, 2 `F821`.

- [ ] **Step 2: Write lint-debt document**

Create `docs/lint-debt.md` with the current command, counts, and policy:

- `F821` can hide runtime errors and should be fixed first.
- `F601` repeated dictionary keys may hide overwritten rules and should be reviewed case-by-case.
- `B023` loop-variable capture can be behavioral and should be fixed with targeted tests where needed.
- Do not mix these fixes with rule refactors.

- [ ] **Step 3: Verify docs change**

Run:

```powershell
git diff -- docs/lint-debt.md
```

Expected: lint-debt documentation only.

- [ ] **Step 4: Commit**

Run:

```powershell
git add docs/lint-debt.md
git commit -m "docs: record bazi lint debt baseline"
```

Expected: one docs commit.

### Task 5: Final Verification

**Files:**
- No planned modifications.

- [ ] **Step 1: Run compile check**

Run:

```powershell
cd C:\Users\21469\bazi-engine\scripts
python -m compileall bazi_engine -q
```

Expected: exit code 0.

- [ ] **Step 2: Run full test suite**

Run:

```powershell
cd C:\Users\21469\bazi-engine\scripts
python -m pytest tests/ -q
```

Expected: full suite passes.

- [ ] **Step 3: Run API smoke**

Run a local uvicorn `/api/health` and `/api/chart` smoke with `BAZI_LLM_REVIEW=0`, `BAZI_AI_ENABLED=0`, and `BAZI_FUSION_ENGINE=0`. Use `liunian_from=2023&liunian_to=2024`.

Expected: health is `ok`, annual scans count is 2, changsheng count is 14, personality/family/palace/body-use are present.

- [ ] **Step 4: Re-run targeted lint baseline**

Run:

```powershell
cd C:\Users\21469\bazi-engine
python -m ruff check scripts --select F821,F601,B023 --statistics
```

Expected: still 26 known errors unless Task 4 intentionally only documented them.

- [ ] **Step 5: Inspect status**

Run:

```powershell
git status --short
git log --oneline -10
```

Expected: clean working tree and recent closeout commits visible.
