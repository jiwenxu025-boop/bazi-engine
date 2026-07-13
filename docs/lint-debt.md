# Bazi Engine Lint Baseline

## Current Baseline

Command:

```powershell
cd C:\Users\21469\bazi-engine
python -m ruff check scripts --statistics
```

Current result:

```text
All checks passed!
```

The previous targeted debt (`F821`, `F601`, `B023`) has been cleared. `RUF001`, `RUF002`, and `RUF003` remain intentionally ignored because Chinese punctuation is expected in user-facing text, docstrings, and comments.

## Policy

- Do not mix future lint fixes with prediction threshold changes.
- Do not mix future lint fixes with broad architecture moves.
- If a lint fix changes rule output, treat it as a rule change and run the relevant calibration in addition to pytest.
- Keep commits grouped by lint class or by tightly related module.
