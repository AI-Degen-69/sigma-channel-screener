"""Monthly screener for the Revelio σ-channel strategy (video xhSbYE7X4ZA).

Rules: 2500-day regression channel, -3σ for S-tier top-10, -4σ for others.
Filters: 10y history, slope up, band > 0. Fundamental check is manual.

Usage:
  python3 monthly_screener.py                 # screen (uses cache), writes screener_latest.md + screener_data.json
  python3 monthly_screener.py --refresh       # force fresh Yahoo download (ignores price cache)
  python3 monthly_screener.py --paper-buy MCD --note "green light: ..."
  python3 monthly_screener.py --paper-sell META --note "..."
  python3 monthly_screener.py --show-paper
"""
import sys, os, time, csv, json, datetime as dt
import urllib.request
import numpy as np

W = 2500
PERIOD1 = 946684800  # 2000-01-01 UTC
UA = {'User-Agent': 'Mozilla/5.0'}
HERE = os.path.dirname(os.path.abspath(__file__))
LEDGER = os.path.join(HERE, "paper_trades.csv")
CACHE_DIR = os.path.join(HERE, ".cache", "prices")
QUOTE_CACHE = os.path.join(HERE, ".cache", "quotes.json")
DATA_JSON = os.path.join(HERE, "screener_data.json")

CANDIDATES = ["AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "BRK-B", "AVGO",
              "TSLA", "JPM", "XOM", "JNJ", "UNH", "COST", "PEP", "NFLX", "MCD",
              "ADBE", "CRM", "ORCL", "AMD", "IBM", "QCOM", "TXN", "LLY", "MRK",
              "ABBV", "KO", "WMT", "HD", "DIS", "NKE", "SBUX", "CAT", "GE",
              "BA", "GS", "MS", "V", "MA", "AMAT", "INTC", "PYPL", "MRVL", "PLTR"]
SIER_TOP10 = {"AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "BRK-B", "AVGO", "TSLA", "JPM"}

QUOTE_TTL = 24 * 3600      # eastmoney quotes: 1 day
PRICE_TTL = 7 * 24 * 3600  # full-history cache: refresh after 7 days (monthly runs refetch only the delta)


def _cache_path(ticker):
    os.makedirs(CACHE_DIR, exist_ok=True)
    return os.path.join(CACHE_DIR, f"{ticker}.json")


def _download(ticker, period1):
    import time as _t, json as _j
    period2 = int(_t.time())
    url = (f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
           f"?period1={period1}&period2={period2}&interval=1d&events=div%7Csplit")
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        d = _j.load(r)
    res = d['chart']['result'][0]
    ts = res['timestamp']
    q = res['indicators']['quote'][0]
    adj = res['indicators'].get('adjclose', [{}])[0].get('adjclose', q['close'])
    out = []
    for i, t in enumerate(ts):
        c = adj[i] if adj[i] is not None else q['close'][i]
        if c is None:
            continue
        day = dt.datetime.fromtimestamp(t, tz=dt.timezone.utc).date().isoformat()
        raw = q['close'][i]
        f = float(c) / float(raw) if raw else 1.0  # put OHLC on the adj-close scale
        o, h, l = q['open'][i], q['high'][i], q['low'][i]
        if o is None or h is None or l is None:
            o = h = l = float(c)
        else:
            o, h, l = round(float(o) * f, 2), round(float(h) * f, 2), round(float(l) * f, 2)
        out.append((day, float(c), o, h, l))
    return out


def _write_cache(path, days, closes, ohl):
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"v": 2, "asof": time.time(), "dates": days,
                   "closes": [float(x) for x in closes],
                   "ohl": [[float(a), float(b), float(c)] for a, b, c in ohl]}, f)


def fetch(ticker, force=False):
    """Daily adj-close + adjusted OHLC since 2000. Cached; monthly reruns fetch only the delta.
    Returns (dates, closes, ohl) with ohl None when only a pre-v2 cache is available."""
    ticker = ticker.upper()
    path = _cache_path(ticker)
    cached = None
    if not force and os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as f:
                cached = json.load(f)
        except Exception:
            cached = None
    if cached and cached.get("v") == 2 and cached.get("ohl"):
        dates = np.array(cached["dates"])
        closes = np.array(cached["closes"], dtype=float)
        ohl = np.array(cached["ohl"], dtype=float)
        if time.time() - cached.get("asof", 0) < PRICE_TTL:
            return dates, closes, ohl
        # Incremental: fetch from last cached day forward, merge.
        p1 = int(dt.datetime.fromisoformat(cached["dates"][-1]).replace(tzinfo=dt.timezone.utc).timestamp())
        try:
            new = _download(ticker, p1)
            by_day = {d: (c, o, h, l) for d, c, (o, h, l) in
                      zip(cached["dates"], cached["closes"], cached["ohl"])}
            by_day.update({d: (c, o, h, l) for d, c, o, h, l in new})
            days = sorted(by_day)
            closes = np.array([by_day[d][0] for d in days], dtype=float)
            ohl = np.array([by_day[d][1:] for d in days], dtype=float)
            _write_cache(path, days, closes, ohl)
            return np.array(days), closes, ohl
        except Exception as e:
            print(f"  {ticker} delta update failed ({e}); using cache ({len(cached['dates'])} bars)", flush=True)
            return dates, closes, ohl
    # Full download with retries (also used to backfill pre-v2 caches).
    last_err = None
    for k in range(3):
        try:
            bars = _download(ticker, PERIOD1)
            days = [d for d, _, _, _, _ in bars]
            closes = np.array([c for _, c, _, _, _ in bars], dtype=float)
            ohl = np.array([(o, h, l) for _, _, o, h, l in bars], dtype=float)
            _write_cache(path, days, closes, ohl)
            return np.array(days), closes, ohl
        except Exception as e:
            last_err = e
            time.sleep(2 * (k + 1))
    if cached and cached.get("dates"):
        print(f"  {ticker} download failed; using stale cache", flush=True)
        return (np.array(cached["dates"]), np.array(cached["closes"], dtype=float),
                np.array(cached["ohl"], dtype=float) if cached.get("ohl") else None)
    raise RuntimeError(f"{ticker} download failed: {last_err}")


def rolling_channel(closes):
    n = len(closes)
    mid = np.full(n, np.nan); s = np.full(n, np.nan)
    low3 = np.full(n, np.nan); low4 = np.full(n, np.nan); slope = np.full(n, np.nan)
    if n < W:
        return mid, s, low3, low4, slope
    Sx = W * (W - 1) / 2.0
    Sxx = (W - 1) * W * (2 * W - 1) / 6.0
    denom = W * Sxx - Sx * Sx
    y = closes
    Sy = y[0:W].sum(); Sxy = float(np.dot(np.arange(W), y[0:W])); Syy = float(np.dot(y[0:W], y[0:W]))
    for t in range(W - 1, n):
        if t > W - 1:
            y_out = y[t - W]; y_in = y[t]
            Sy, Sxy, Syy = (Sy - y_out + y_in, Sxy - (Sy - y_out) + (W - 1) * y_in,
                            Syy - y_out * y_out + y_in * y_in)
        b = (W * Sxy - Sx * Sy) / denom
        a = (Sy - b * Sx) / W
        m = a + b * (W - 1)
        var = max((Syy - a * Sy - b * Sxy) / W, 0.0)
        mid[t] = m; s[t] = float(np.sqrt(var))
        low3[t] = m - 3 * s[t]; low4[t] = m - 4 * s[t]; slope[t] = b
    return mid, s, low3, low4, slope


def _quote_rows(tickers):
    """One eastmoney batch call; returns {CODE: quote}."""
    import subprocess
    p = subprocess.run(["opencli", "eastmoney", "quote", " ".join(tickers), "-f", "json"],
                       capture_output=True, timeout=60, shell=True)
    j = json.loads(p.stdout.decode("utf-8-sig", errors="replace").strip())
    rows = j if isinstance(j, list) else j.get("data", [])
    return {r["code"].upper(): r for r in rows}


def live_mcaps(tickers):
    """MCap/P-E/P-B via eastmoney, cached 24h. Missing symbols -> {} (shown as n/a)."""
    if os.path.exists(QUOTE_CACHE) and time.time() - os.path.getmtime(QUOTE_CACHE) < QUOTE_TTL:
        try:
            with open(QUOTE_CACHE, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    out = {}
    try:
        for g in range(0, len(tickers), 15):
            chunk = tickers[g:g + 15]
            try:
                for code, r in _quote_rows(chunk).items():
                    out[code] = dict(mcap=r.get("marketCap"), pe=r.get("peDynamic"),
                                    pb=r.get("priceBook"), price=r.get("price"))
            except Exception as e:
                print(f"  [warn] quote chunk failed ({e})", flush=True)
            time.sleep(0.5)
        os.makedirs(os.path.dirname(QUOTE_CACHE), exist_ok=True)
        with open(QUOTE_CACHE, "w", encoding="utf-8") as f:
            json.dump(out, f)
    except Exception as e:
        print(f"  [warn] live mcap fetch failed ({e})", flush=True)
    print(f"  live quotes: {len(out)}/{len(tickers)} tickers", flush=True)
    return out


def ai_prompt(ticker, price, pos):
    return (f"Fundamental check for {ticker} at ${price:.2f} ({pos:+.2f} σ below trend). "
            f"With web search on, answer ONLY: (1) TEMPORARY recoverable dip or PERMANENT damage? "
            f"Cite the cause + 2-3 recent sources. (2) Bankruptcy/severe distress risk in 12-24 months? "
            f"Cover debt, interest coverage, FCF, maturities, dividend. "
            f"End with GREEN LIGHT or RED LIGHT + one paragraph of reasoning.")


def screen(force=False):
    print("Screening (Yahoo + cached history)...", flush=True)
    quotes = live_mcaps(CANDIDATES)
    rows = []
    for t in CANDIDATES:
        try:
            dates, closes, _ = fetch(t, force=force)
            print(f"  {t}: {len(dates)} days ..{dates[-1]}", flush=True)
        except Exception as e:
            print(f"  {t} FAILED: {e}", flush=True)
            continue
        q = quotes.get(t, {})
        if (q.get("mcap") or 0) < 50e9 and q.get("mcap") is not None:
            continue  # $50B filter (n/a passes; confirm in broker)
        entry = dict(ticker=t, date=dates[-1], price=float(closes[-1]),
                     mcap=q.get("mcap"), pe=q.get("pe"), pb=q.get("pb"), bars=len(dates))
        mid, std, low3, low4, slope = rolling_channel(closes)
        i = len(dates) - 1
        if np.isnan(low3[i]):
            entry["note"] = f"SKIP: only {len(dates)} bars < 2500 (need 10y history)"
            rows.append(entry)
            continue
        pos = (closes[i] - mid[i]) / std[i] if std[i] > 0 else float("nan")
        up = slope[i] > 0
        k = 3 if t in SIER_TOP10 else 4
        band = low3[i] if k == 3 else low4[i]
        off_high = closes[i] / closes[max(0, i - 252):i + 1].max() - 1
        if not up:
            note = "SKIP: channel flat/down (no 10y growth)"
        elif (low3[i] <= 0) or (k == 4 and low4[i] <= 0):
            note = "SKIP: -3/-4 band below zero"
        elif closes[i] <= band:
            note = f"ACTION: at/below -{k}σ ({'S-tier' if k == 3 else 'standard'}) — run AI check, 5-10% size"
        elif pos <= -(k - 0.5):
            note = f"WATCH: near -{k}σ ({pos:+.2f}σ) — prepare thesis"
        else:
            note = "hold/cash — no signal"
        entry.update(mid=float(mid[i]), sd=float(std[i]), low3=float(low3[i]),
                     low4=float(low4[i]), slope_up=bool(up), pos=float(pos),
                     k=k, off52w=float(off_high), note=note)
        rows.append(entry)
    rows.sort(key=lambda r: r.get("pos", 99))
    return rows


CB = 504  # candle window: last ~2 trading years, daily


def chart_series(ticker, dates, closes, ohl, mid, low3, low4, years=6, step=5):
    """Downsampled weekly history for the dashboard (last `years` years),
    plus daily adjusted OHLC + daily bands for the last CB bars (candle view)."""
    n = len(dates)
    idx = list(range(max(0, n - years * 252), n, step))
    if idx[-1] != n - 1:
        idx.append(n - 1)
    def rnd(a, i):
        v = a[i]
        return round(float(v), 2) if not np.isnan(v) else None
    out = dict(ticker=ticker,
               dates=[str(dates[i]) for i in idx],
               close=[round(float(closes[i]), 2) for i in idx],
               mid=[rnd(mid, i) for i in idx],
               low3=[rnd(low3, i) for i in idx],
               low4=[rnd(low4, i) for i in idx],
               candles=None)
    if ohl is not None and len(ohl) == n:
        j = list(range(max(0, n - CB), n))
        out["candles"] = dict(
            dates=[str(dates[i]) for i in j],
            o=[round(float(ohl[i][0]), 2) for i in j],
            h=[round(float(ohl[i][1]), 2) for i in j],
            l=[round(float(ohl[i][2]), 2) for i in j],
            c=[round(float(closes[i]), 2) for i in j],
            mid=[rnd(mid, i) for i in j],
            low3=[rnd(low3, i) for i in j],
            low4=[rnd(low4, i) for i in j])
    return out


def render(rows):
    today = dt.date.today().isoformat()
    L = [f"# Monthly σ-channel screen — {today}", "",
         "Rule: S-tier (top-10) buy at/below -3σ, others at/below -4σ; slope up; band > 0; 2500-day channel.",
         "Fundamental check required before any BUY (see prompts). Size 5-10%, cash is a position.",
         "MCap/P-E/P-B via eastmoney; `n/a` = no quote — confirm $50B+ in your broker.", "",
         "| Ticker | Price | σ pos | Buy line | Slope | MCap | P/E | P/B | 1y off-high | Verdict |",
         "|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        if "pos" not in r:
            mcap = f"${r['mcap'] / 1e9:.0f}B" if r.get("mcap") else "n/a"
            L.append(f"| {r['ticker']} | {r['price']:.2f} | — | — | — | {mcap} | — | — | — | {r['note']} |")
            continue
        buy = f"-{r['k']}σ @ {(r['low3'] if r['k'] == 3 else r['low4']):.2f}"
        mcap = f"${r['mcap'] / 1e9:.0f}B" if r.get("mcap") else "n/a"
        pe = f"{r['pe']:.1f}" if r.get("pe") else "n/a"
        pb = f"{r['pb']:.1f}" if r.get("pb") else "n/a"
        L.append(f"| {r['ticker']} | {r['price']:.2f} | {r['pos']:+.2f}σ | {buy} | "
                 f"{'up' if r['slope_up'] else 'FLAT/DOWN'} | {mcap} | {pe} | {pb} | "
                 f"{r['off52w']:+.1%} | {r['note']} |")
    action = [r for r in rows if r.get("note", "").startswith(("ACTION", "WATCH"))]
    L += ["", f"## Needs your thesis check ({len(action)})", ""]
    if not action:
        L.append("Nothing near a buy line. Stay in cash — that *is* the strategy most months.")
    for r in action:
        L += [f"### {r['ticker']} — {r['note']}",
              f"Price ${r['price']:.2f} on {r['date']}, {r['pos']:+.2f}σ, mid-line target ${r['mid']:.2f} "
              f"(+{r['mid'] / r['price'] - 1:.0%} to regression). 1y off-high {r['off52w']:+.1%}.", "",
              "AI check prompt (paste to your AI with web search on):",
              f"> {ai_prompt(r['ticker'], r['price'], r['pos'])}", "",
              f"Paper log: `python3 monthly_screener.py --paper-buy {r['ticker']} --note \"green light: ...\"`", ""]
    L += ["## Paper-trade ledger",
          "See `paper_trades.csv`. Log every BUY/SELL with price + thesis note; "
          "re-run the AI check quarterly; sell at loss only if the thesis breaks."]
    return "\n".join(L) + "\n"


def ledger_ensure():
    if not os.path.exists(LEDGER):
        with open(LEDGER, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(["date", "ticker", "action", "price", "sd_pos", "note"])


def paper_log(action, ticker, note):
    ticker = ticker.upper()
    dates, closes, _ = fetch(ticker)
    mid, std, low3, *_ = rolling_channel(closes)
    i = len(dates) - 1
    pos = f"{(closes[i] - mid[i]) / std[i]:+.2f}" if not np.isnan(low3[i]) and std[i] else ""
    ledger_ensure()
    with open(LEDGER, "a", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow([dates[i], ticker, action, f"{closes[i]:.2f}", pos, note or ""])
    print(f"Logged {action} {ticker} @ {closes[i]:.2f} ({dates[i]})", flush=True)


def show_paper():
    ledger_ensure()
    with open(LEDGER, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        print('Ledger empty. Log a trade: python3 monthly_screener.py --paper-buy MCD --note "..."')
        return
    print(f"{'date':10} {'ticker':6} {'action':4} {'price':>8} {'sd':>7}  note")
    for r in rows:
        print(f"{r['date']:10} {r['ticker']:6} {r['action']:4} {r['price']:>8} {r['sd_pos']:>7}  {r['note']}")
    print("\nOpen positions vs current price (1 share per BUY assumed):")
    pos = {}
    for r in rows:
        q = 1 if r["action"] == "BUY" else (-1 if r["action"] == "SELL" else 0)
        p = pos.setdefault(r["ticker"], dict(qty=0, cost=0.0))
        p["qty"] += q
        p["cost"] += float(r["price"]) * q
    for t, p in pos.items():
        if p["qty"] <= 0:
            continue
        try:
            _, closes, _ = fetch(t)
            pnl = (closes[-1] - p["cost"] / p["qty"]) / (p["cost"] / p["qty"])
            print(f"  {t}: {p['qty']} sh, avg {p['cost'] / p['qty']:.2f} -> {closes[-1]:.2f} ({pnl:+.1%})")
        except Exception as e:
            print(f"  {t}: price fetch failed ({e})")


if __name__ == "__main__":
    a = sys.argv[1:]
    if "--show-paper" in a:
        show_paper()
    elif "--paper-buy" in a:
        t = a[a.index("--paper-buy") + 1]
        note = a[a.index("--note") + 1] if "--note" in a else ""
        paper_log("BUY", t, note)
    elif "--paper-sell" in a:
        t = a[a.index("--paper-sell") + 1]
        note = a[a.index("--note") + 1] if "--note" in a else ""
        paper_log("SELL", t, note)
    else:
        force = "--refresh" in a
        rows = screen(force=force)
        md = render(rows)
        with open("screener_latest.md", "w", encoding="utf-8") as f:
            f.write(md)
        # Dashboard data: table rows + downsampled band history per ticker.
        charts = {}
        for r in rows:
            if "pos" not in r:
                continue
            try:
                dates, closes, ohl = fetch(r["ticker"])
                mid, _, low3, low4, _ = rolling_channel(closes)
                charts[r["ticker"]] = chart_series(r["ticker"], dates, closes, ohl, mid, low3, low4)
            except Exception as e:
                print(f"  chart series skipped for {r['ticker']}: {e}", flush=True)
        with open(DATA_JSON, "w", encoding="utf-8") as f:
            json.dump({"asof": dt.date.today().isoformat(), "rows": rows, "charts": charts}, f)
        print(md)
        print("Wrote screener_latest.md + screener_data.json", flush=True)
        ledger_ensure()
