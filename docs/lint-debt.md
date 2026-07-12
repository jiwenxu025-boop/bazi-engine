# Bazi Engine Lint Debt Baseline

## Current Targeted Baseline

Command:

```powershell
cd C:\Users\21469\bazi-engine
python -m ruff check scripts --select F821,F601,B023 --statistics
```

Current result:

```text
16 B023 function-uses-loop-variable
 8 F601 multi-value-repeated-key-literal
 2 F821 undefined-name
Found 26 errors.
```

This is existing lint debt and should stay separate from chart-stage refactors and prediction-rule work.

## Fix Order

1. `F821 undefined-name`
   - Highest priority because it can hide runtime crashes.
   - Fix with the smallest local change and a focused test or import smoke.

2. `F601 multi-value-repeated-key-literal`
   - Review case by case because repeated dictionary keys can silently overwrite rule data.
   - Do not assume all duplicates are safe; compare the overwritten value with the intended rule table.

3. `B023 function-uses-loop-variable`
   - Can be behavioral if closures capture the final loop value.
   - Fix with targeted tests where the function is used by rule dispatch or callbacks.

## Policy

- Do not mix lint fixes with prediction threshold changes.
- Do not mix lint fixes with broad architecture moves.
- If a lint fix changes rule output, treat it as a rule change and run the relevant calibration in addition to pytest.
- Keep commits grouped by lint class or by tightly related module.
