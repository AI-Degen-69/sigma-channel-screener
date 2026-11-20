# σ-Channel Screener

Monthly stock screener based on the **Revelio Trading σ-channel strategy** ([video](https://www.youtube.com/watch?v=xhSbYE7X4ZA)).

Buy large-cap stocks only when price drops to an extreme statistical discount on a 2500-day (≈10 year) linear-regression channel — then hold for a reversion to the trend line.

## Rules

| Rule | Detail |
|---|---|
| Universe | US large-cap, market cap > \$50B, 10+ years of history |
| Channel | 2500-day OLS regression on adj-close (population stdev) |
| Entry (S-tier top-10) | At or below **−3σ** |
| Entry (others) | At or below **−4σ** |
| Filters | Slope must be **up** (10y growth); buy-line must be **> 0** |
| Fundamental check | AI-assisted: temporary dip vs permanent damage, bankruptcy risk |
| Take profit | Partial/full at the regression mid-line |
| Sizing | 5–10% per stock; cash is a position |
| Stop-loss | None — sell only if the thesis breaks |

## Quick start

```bash
# Run the monthly screen (uses cached Yahoo data)
python monthly_screener.py

# Force-refresh all price data from Yahoo Finance
python monthly_screener.py --refresh

# Log a paper trade
python monthly_screener.py --paper-buy MCD --note "green light: ..."
python monthly_screener.py --paper-sell META --note "thesis broke"

# View paper-trade ledger
python monthly_screener.py --show-paper
```

### Output

| File | Purpose |
|---|---|
| `screener_latest.md` | Human-readable screen table + AI-check prompts |
| `screener_data.json` | Machine-readable screen data + chart series for the dashboard |
| `index.html` | Interactive local dashboard — current UI, served over HTTP after each run |
| `dashboard.html` | Earlier dashboard version, same data — kept for reference |
| `paper_trades.csv` | Paper-trade ledger (BUY/SELL with price, σ position, thesis note) |

## Dashboard

The dashboard loads `screener_data.json` with `fetch`, which browsers block on `file://` origins, so serve the folder instead of double-clicking the file:

```bash
python -m http.server 8000
# then open http://localhost:8000/index.html
```

`dashboard.html` is the earlier version of the same dashboard (open `http://localhost:8000/dashboard.html`). Features:

- Sortable/filterable table with color-coded σ position, P/E, slope, and 52-week drawdown
- Per-stock σ-band chart (trend line view + daily candlestick view)
- Embedded TradingView live chart
- One-click copy of the AI fundamental-check prompt

## TradingView indicator

`sd_channel_2500.pine` — paste into Pine Editor to overlay the exact same channel on any TradingView daily chart. Math matches `rolling_channel()` in the Python screener.

> **Note:** TradingView uses split-adjusted close (not dividend-adjusted). On dividend payers the bands sit slightly lower than the screener's Yahoo adj-close bands. Non-payers match exactly.

## Strategy verification

`verify_strategy.py` + `VERIFY_REPORT.md` — independent re-implementation and fact-check of the video's four named trades and benchmark claims. See the report for what checks out and what doesn't.

## Dependencies

- Python 3.10+
- NumPy
- Network access to Yahoo Finance (price history)
- Optional: `opencli eastmoney` for live MCap/P-E/P-B quotes

## Disclaimer

This is a paper-trading research tool, not financial advice. Past performance does not guarantee future results. The 899% headline claim from the video is unverifiable — see `VERIFY_REPORT.md` for details.
