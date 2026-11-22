# Task — extract the channel decision into a testable function

## Why

`screen()` in `monthly_screener.py` decides ACTION / WATCH / hold / SKIP inline, so the one
piece of logic this screener exists for cannot be tested without a network fetch. The dashboard
also has no machine-readable verdict to filter on: it re-parses the `note` string.

## Deliverable

Add one pure function to `monthly_screener.py` and make `screen()` use it.

```python
def classify_channel(price, mid, std, low3, low4, slope_up, k):
    """Return {"pos": float, "note": str, "signal": str} for one screened row."""
```

### Rules, in this order

1. `pos = (price - mid) / std` when `std > 0`, else `float("nan")`. Never raise on `std == 0`.
2. `not slope_up` → `note` starts with `SKIP: channel flat/down (no 10y growth)`, `signal` is
   `"skip_flat"`.
3. `low3 <= 0`, or `k == 4 and low4 <= 0` → `note` starts with `SKIP: -3/-4 band below zero`,
   `signal` is `"skip_band"`.
4. `price <= band`, where `band = low3` when `k == 3` and `low4` when `k == 4` → `note` starts
   with `ACTION: at/below -{k}σ`, keeps the existing `(S-tier)` / `(standard)` suffix, `signal`
   is `"action"`.
5. `pos <= -(k - 0.5)` → `note` starts with `WATCH: near -{k}σ`, keeps the existing
   `({pos:+.2f}σ)` part, `signal` is `"watch"`.
6. Otherwise → `note` is exactly `hold/cash - no signal`, `signal` is `"hold"`.

`screen()` must call it for every row that has a channel (`low3` defined) and store the returned
`signal` on the row as `signal=`. The other row fields, the existing `note` text, the printed
markdown, and `screener_data.json` must not change.

## Out of scope

- No changes to `App.tsx`, `index.html`, or the dashboard UI.
- No new dependencies.
- No change to `rolling_channel`, the price cache, or the fetch path.
- Do not commit. Leave the changes in the working tree.

## Gate

```bash
python -m pytest tasks/ab-orchestrator -q
```

All tests pass. Run it from the repo root.

## Notes

- `W`, `SIER_TOP10`, and `k` selection stay where they are. Pass `k` in.
- The note strings are asserted by prefix, so keep the existing wording. One exception: the
  `hold/cash` note is written with a hyphen, not the long dash the old code used.
