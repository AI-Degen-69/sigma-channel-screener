# Verification: Revelio Trading σ-channel strategy (video xhSbYE7X4ZA)

Video: "The simple stock investing strategy that beats the market" / re-titled
"Buy stocks only when they hit this line (+899%)" — Revelio Trading.

Claimed rules (from full transcript):
- Watchlist: market cap > $50B, US primary listing, 10+ years history, refresh yearly
- Indicator: TradingView Standard Deviation Channel, length 2500 daily (~10y),
  lower deviations -3 and -4, regression line = take-profit
- Entry: top-10 "S-tier" at -3σ; others at -4σ or lower
- Filters: channel must slope up; -3/-4 line must be > 0; else skip
- Fundamental check (AI-assisted): temporary reason? bankruptcy risk? Re-check ~quarterly;
  only reason to sell at loss = thesis breaks
- No stop-loss; take at least partial profit at regression line
- Sizing 5-10% per stock, ~10-20 stocks, cash allowed when nothing qualifies
- Claimed results (own investments, NOT a backtest, ~11y from 2016):
  $10k -> $99,900 strategy vs $73,100 Nasdaq vs $44,900 S&P 500, dividends included;
  one negative year (2022, smaller loss); lower max drawdown; beats Nasdaq every year
  on return/drawdown, loses to S&P in 3 of 11 years by small margin

## How I verified

Re-implemented the indicator from scratch (no TradingView):
rolling 2500-trading-day linear regression on Yahoo Finance **adj-close**
(total-return) dailies from 2000, recomputed at each date (no lookahead —
matches his "replay function" warning). Signal = close < mid - k*std,
slope > 0, band > 0. Code: `verify_strategy.py`, results: `verify_results.json`.
Recent cross-checks via `opencli eastmoney kline/quote` (US tickers work).

## What checks out (tick-level)

1. **MCD call — exact to the cent.** Video: "McDonald's ... at $230.94".
   My data: MCD closed **$230.94 on 2026-09-30**, position **-5.45σ** (below -4).
   MCD stayed below -4 from ~Sep 15 to ~Oct 21, then recovered to -2.47σ
   by Nov 19 ($271.82). So the video was recorded around end-Sep/Oct 2026,
   and the -4 reading is confirmed.
2. **META June 2022 — confirmed.** First -4 cross **2022-06-13**
   (close $162.70, -4.18σ). On 2026-06-15: $167.74 at -3.99σ (just above -4).
   "Down more than 40% after entry" confirmed: adverse excursion reached
   about -45% to -56% on early entries before the +70%-in-a-year recovery leg.
3. **MSFT Mar-Aug 2026 — confirmed in shape.** Cross below -3 on **2026-03-27**
   (close $355.33, -3.20σ; he said bought ~$363 intraday). Touch of the
   regression line on **2026-08-03** (close $486.73 = +37% vs his stated +31%;
   gap = intraday vs close / partial-profit timing, same trade).
4. **ADBE vs MCD logic — confirmed.** ADBE -66% from ATH but only **-1.98σ**,
   low-4 line even negative (-$29.70) — i.e. deep ATH drawdown != trend
   discount. MCD was the deeper trend discount. His illustration is real.
5. **Benchmarks — match exactly once the end date is right.** $10k from
   2016-01-04: SPY -> **$45,193** at Oct 1 2026 ($42,916 by Nov 19);
   QQQ -> **$73,107** at Oct 1 2026 ($64,699 by Nov 19).
   His $44,900 / $73,100 = S&P 500 / Nasdaq total-return to **~Oct 1, 2026**.
   (QQQ used as Nasdaq proxy; Nasdaq Composite total-return differs slightly.)

## What does NOT verify / key caveats

1. **The $99,900 head number is unverifiable.** It is his private brokerage
   record, not a published backtest: no trade list, dates, sizes, cash weight,
   fees/taxes. I cannot confirm or refute +899%.
2. **Signals are extremely rare — expect mostly cash.** Month-end scan of 18
   current large caps, 2016-01..2026-10 (129 months): only **37 months** had
   any -3 signal, **11 months** any -4. AAPL/MSFT/NVDA/GOOGL had **zero**
   month-end signals in 10 years (MSFT's Mar 2026 signal was intra-month).
   Signals cluster in crashes (Mar 2020, 2022, 2025 UNH/PEP). A follower
   would sit in cash for years — psychologically hard, and cash drag is
   not in the headline number.
3. **Forward returns in my sample look great but are weak evidence.**
   25 month-end signals: median +11% (3m), +15% (6m), **+59% (12m)**,
   96% positive at 12m; 11/25 touched the mid-line within a year (median
   167 trading days); median worst dip after entry **-13.6%**.
   BUT: N=25, overlapping (META counted 9 times for one episode), monthly
   sampling, 18-stock menu. This is a sanity check, not a backtest.
4. **Survivorship bias flatters everything.** Universe = today's $50B+
   survivors. Bankrupt/delisted former members (the stocks where "is it
   dying?" mattered most) are absent from my scan. His AI bankruptcy filter
   is discretionary and untestable historically.
5. **Parameter fragility.** 2500 days, -3/-4, adj-close vs raw price, and
   TradingView's exact stdev definition all move the lines. My replication
   matches his four anecdotes, but I did not prove it matches his chart
   pixel-for-pixel over 11 years.
6. **Risk reality: -40% to -56% drawdowns on single positions** (META 2022)
   with no stop-loss. At 5-10% sizing that's -2% to -5.6% portfolio pain per
   name — survivable only with his sizing + cash + "strong mindset". Beginners
   copying entries without sizing will feel it very differently.
7. **His own warning is the most important part:** today's channel cannot
   judge past signals (it recalculates as old candles drop out). Any
   "backtest" drawn with today's lines is lookahead-biased. Use replay only.

## Verdict

- **Mechanics: VERIFIED.** All four checkable claims (META -4 Jun 2022,
  MSFT -3 Mar 2026 -> mid-line Aug 2026, MCD below -4 at $230.94, ADBE not
  a signal despite -66% from ATH) reproduce in independent data.
  Benchmarks ($44.9k / $73.1k) match SPY/QQQ total return to ~Oct 1 2026.
- **Edge: PLAUSIBLE but NOT PROVEN.** Deep-trend mean reversion in
  mega-cap survivors bounced hard in 2020/2022/2025; my small sample agrees.
  Whether that compounds to 899% over 11 years after cash drag, missed
  signals, bankrupt-avoidance skill, and taxes depends entirely on the
  undisclosed trade ledger.
- **For a beginner:** treat it as a disciplined watchlist + patience system
  (rare entries, small size, cash OK, sell only if thesis breaks), not as a
  proven 899% machine. Do not run it without the 5-10% sizing rule and the
  quarterly fundamental re-check — those do most of the risk work.

Reproduce: `python3 verify_strategy.py` (needs Python + numpy/pandas,
network to Yahoo Finance). Raw signal table: `verify_results.json`.
