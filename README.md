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
```

### Output

| File | Purpose |
|---|---|
| `screener_data.json` | Screen data + chart series for the dashboard |
| `index.html` / `src/` | Dashboard (React 19 + Tailwind CSS v4 + Vite) |

## Dashboard

The dashboard is the React 19 + TypeScript + Tailwind CSS v4 app in `src/`, served by Vite from `index.html` with canonical `shadcn/ui` components (`nova` preset). It must run through Vite — `index.html` loads TypeScript and TSX sources directly, so a plain static file server only shows a blank page.

Vite serves the repository-root `screener_data.json`, so `python monthly_screener.py --refresh` is picked up without copying any file.

```bash
# Install dependencies
pnpm install

# Start development server
pnpm dev              # http://localhost:5173

# Build and preview production release
pnpm build
pnpm preview
```

### Key Features
- **4-Card KPI Header:** Total screened universe, action signals (S-Tier ≤ −3σ / Standard ≤ −4σ), radar watch, and deepest discount leader.
- **Sortable & Filterable Table:** Instant ticker search, signal/tier tabs, slope toggles, and σ discount rank.
- **Dual Visual Inspection:** Custom canvas σ-regression channel & candlestick view alongside live interactive TradingView chart.
- **One-Click AI Strategy Prompt:** Pre-populated fundamental verification prompt ready for LLM sanity checks.

## Dependencies

- Python 3.10+
- NumPy
- Node.js 20+ and pnpm (modern dashboard only)
- Network access to Yahoo Finance (price history)
- Optional: `opencli eastmoney` for live MCap/P-E/P-B quotes

## Disclaimer

This is a research tool, not financial advice. Past performance does not guarantee future results. The 899% headline claim from the video is unverifiable.
