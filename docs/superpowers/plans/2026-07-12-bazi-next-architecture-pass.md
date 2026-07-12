# Bazi Next Architecture Pass Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stabilize local CI checks, document the remaining `build_chart()` orchestration dependencies, and choose the next safe refactor without changing prediction rules.

**Architecture:** Keep `build_chart()` as the public factory. Treat current rule modules as owned behavior and only improve orchestration visibility. Any later extraction must preserve `BaziChart.to_dict()` output and have a focused test before implementation.

**Tech Stack:** Python 3.13, pytest, ruff, FastAPI, existing `bazi_engine` modules.

---

### Task 1: Restore Local CI Equivalence

**Files:**
- Read: `requirements-dev.txt`
- Read: `scripts/pyproject.toml`
- Modify: none unless checks reveal a real issue

- [ ] **Step 1: Install development checks**

Run from `C:\Users\21469\bazi-engine`:

```powershell
python -m pip install -r requirements-dev.txt
```

Expected: `pytest`, `ruff`, and `pre-commit` are available locally.

- [ ] **Step 2: Run the same lint target as CI**

```powershell
python -m ruff check scripts
```

Expected: either `All checks passed!` or a concrete list of existing lint failures.

- [ ] **Step 3: Run tests after lint**

```powershell
cd C:\Users\21469\bazi-engine\scripts
python -m pytest tests/ -q
```

Expected: test suite remains green. At the time this plan was written, the baseline was `97 passed, 20 skipped`.

### Task 2: Document Remaining `build_chart()` Dependencies

**Files:**
- Modify: `docs/architecture.md`
- Read: `scripts/bazi_engine/chart.py`

- [ ] **Step 1: Identify remaining stages after yongshen**

Read `build_chart()` from the調候 section through the end and list each stage in execution order.

- [ ] **Step 2: Record each stage's inputs and outputs**

Add a section to `docs/architecture.md` named `Build Chart Stage Dependencies` with a table like:

```markdown
| Stage | Inputs | Writes | Downstream users | Refactor risk |
| --- | --- | --- | --- | --- |
| Tiaohou | day master, month branch, day branch, all stems, all branches | `chart.tiaohou_result` | health profile, personality, LLM context | Low |
```

Expected: the table explains why the next extraction should be small and where shared values like `all_stems`, `all_branches`, and `_yongshen_result` are reused.

- [ ] **Step 3: Verify documentation only**

```powershell
git diff -- docs/architecture.md
```

Expected: only documentation changed in this task.

### Task 3: Choose the Next Refactor Candidate

**Files:**
- Read: `docs/architecture.md`
- Read: `scripts/bazi_engine/chart.py`
- Modify: none

- [ ] **Step 1: Compare candidates**

Rank `tiaohou + health`, `ten gods`, `pattern + pattern yongshen`, `dayun modulation`, and `liunian scan` by:

- input clarity
- output clarity
- downstream fan-out
- probability of accidental rule change

- [ ] **Step 2: Select one candidate**

Expected selection unless the dependency table disproves it: `tiaohou + health`, because it has explicit inputs and isolated writes.

- [ ] **Step 3: Stop before implementation**

Do not extract the next stage until a behavior test is written first.

### Task 4: Final Verification and Commit Decision

**Files:**
- Modify only if Task 2 updates documentation

- [ ] **Step 1: Run verification**

```powershell
cd C:\Users\21469\bazi-engine\scripts
python -m pytest tests/ -q
```

Expected: tests pass.

- [ ] **Step 2: Inspect git status**

```powershell
cd C:\Users\21469\bazi-engine
git status --short
```

Expected: either only `docs/architecture.md` plus this plan changed, or no changes if no doc update was needed.

- [ ] **Step 3: Commit only documentation/planning changes**

```powershell
git add docs/architecture.md docs/superpowers/plans/2026-07-12-bazi-next-architecture-pass.md
git commit -m "docs: map remaining bazi chart stages"
```

Expected: commit contains planning and architecture documentation only.
