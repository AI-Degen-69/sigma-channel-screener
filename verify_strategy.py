"""Verify the Revelio Trading σ-channel strategy (video xhSbYE7X4ZA).
Method: rolling 2500-trading-day linear-regression channel on Yahoo adj-close,
recomputed at each date (no lookahead), signals when close < mid - k*std.
"""
import urllib.request, json, time, datetime as dt
import numpy as np

PERIOD1 = int(dt.datetime(2000,1,1,tzinfo=dt.timezone.utc).timestamp())
PERIOD2 = int(time.time())
W = 2500
UA = {'User-Agent':'Mozilla/5.0'}

TICKERS = ["AAPL","MSFT","NVDA","GOOGL","AMZN","META","BRK-B","AVGO","TSLA","JPM",
           "XOM","JNJ","UNH","COST","PEP","NFLX","MCD","ADBE"]
BENCH = ["SPY","QQQ"]
ALL = TICKERS + BENCH

def fetch(ticker):
    url = (f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
           f"?period1={PERIOD1}&period2={PERIOD2}&interval=1d&events=div%7Csplit")
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        d = json.load(r)
    res = d['chart']['result'][0]
    ts = res['timestamp']
    q = res['indicators']['quote'][0]
    adj = res['indicators'].get('adjclose', [{}])[0].get('adjclose', q['close'])
    dates, closes = [], []
    for i,t in enumerate(ts):
        c = adj[i] if adj[i] is not None else q['close'][i]
        if c is None: continue
        dates.append(dt.datetime.fromtimestamp(t, tz=dt.timezone.utc).date().isoformat())
        closes.append(float(c))
    return np.array(dates), np.array(closes)

def rolling_channel(closes):
    """Return dict arrays (len N, nan where insufficient): mid, s, low3, low4, slope."""
    n = len(closes)
    mid = np.full(n, np.nan); s = np.full(n, np.nan)
    low3 = np.full(n, np.nan); low4 = np.full(n, np.nan); slope = np.full(n, np.nan)
    if n < W: return mid, s, low3, low4, slope
    Sx = W*(W-1)/2.0
    Sxx = (W-1)*W*(2*W-1)/6.0
    denom = W*Sxx - Sx*Sx
    y = closes
    Sy = y[0:W].sum(); Sxy = float(np.dot(np.arange(W), y[0:W])); Syy = float(np.dot(y[0:W], y[0:W]))
    for t in range(W-1, n):
        if t > W-1:
            y_out = y[t-W]; y_in = y[t]
            Sy_new = Sy - y_out + y_in
            Sxy_new = Sxy - (Sy - y_out) + (W-1)*y_in
            Syy_new = Syy - y_out*y_out + y_in*y_in
            Sy, Sxy, Syy = Sy_new, Sxy_new, Syy_new
        b = (W*Sxy - Sx*Sy)/denom
        a = (Sy - b*Sx)/W
        m = a + b*(W-1)
        # population std of residuals
        sse = Syy - a*Sy - b*Sxy
        var = max(sse/W, 0.0)
        std = float(np.sqrt(var))
        mid[t]=m; s[t]=std; low3[t]=m-3*std; low4[t]=m-4*std; slope[t]=b
    return mid, s, low3, low4, slope

def first_trading_day_idx_on_or_after(dates, target):
    for i,d in enumerate(dates):
        if d >= target: return i
    return None

print("Downloading...", flush=True)
data = {}
for t in ALL:
    try:
        dates, closes = fetch(t)
        data[t] = (dates, closes)
        print(f"  {t}: {len(dates)} days {dates[0]}..{dates[-1]}", flush=True)
    except Exception as e:
        print(f"  {t} FAILED: {e}", flush=True)
    time.sleep(0.3)

print("\nComputing channels (W=2500)...", flush=True)
ch = {}
for t in TICKERS:
    dates, closes = data[t]
    mid, std, low3, low4, slope = rolling_channel(closes)
    ch[t] = dict(mid=mid, std=std, low3=low3, low4=low4, slope=slope)

def status_at(ticker, target_date):
    dates, closes = data[ticker]
    c = ch[ticker]
    i = first_trading_day_idx_on_or_after(dates, target_date)
    if i is None: return f"{ticker} {target_date}: no data"
    if np.isnan(c['low3'][i]):
        return (f"{ticker} {dates[i]} close={closes[i]:.2f}: INSUFFICIENT HISTORY "
                f"({i+1} bars < 2500, need 10y)")
    sl = "UP" if c['slope'][i] > 0 else "FLAT/DOWN"
    pos = (closes[i]-c['mid'][i])/c['std'][i] if c['std'][i]>0 else float('nan')
    sig3 = closes[i] < c['low3'][i]; sig4 = closes[i] < c['low4'][i]
    return (f"{ticker} {dates[i]} close={closes[i]:.2f} mid={c['mid'][i]:.2f} "
            f"pos={pos:+.2f}σ low3={c['low3'][i]:.2f} low4={c['low4'][i]:.2f} "
            f"slope={sl} below0={c['low3'][i]<0} SIGNAL-3={sig3} SIGNAL-4={sig4}")

print("\n=== Claim spot-checks ===")
for t, d in [("META","2022-06-15"),("MSFT","2026-03-27"),("MCD","2026-11-19"),("ADBE","2026-11-19")]:
    if t in data: print(status_at(t, d))

# Detailed META June 2022: first -4 cross in May-Jul 2022
print("\n=== META May-Jul 2022 first -4 cross ===")
if "META" in data:
    dates, closes = data["META"]; c = ch["META"]
    for i in range(len(dates)):
        if "2022-05-01" <= dates[i] <= "2022-07-31" and not np.isnan(c['low4'][i]):
            if closes[i] < c['low4'][i]:
                print("  first:", status_at("META", dates[i])); break

# Benchmark check: $10k Jan 2016 -> now
print("\n=== Benchmark check ($10k from first trading day >= 2016-01-04, adj close = total return) ===")
for b in BENCH:
    if b in data:
        dates, closes = data[b]
        i0 = first_trading_day_idx_on_or_after(dates, "2016-01-04")
        print(f"  {b}: {dates[i0]} {closes[i0]:.2f} -> {dates[-1]} {closes[-1]:.2f} "
              f"= ${10000*closes[-1]/closes[i0]:,.0f} ({closes[-1]/closes[i0]-1:.1%})")

# Breadth: month-end signals 2016-2026
print("\n=== Breadth: month-end -3/-4 signals per ticker, 2016-01..2026-10 ===")
seen_months = sorted({d[:7] for t in TICKERS for d in data[t][0] if "2016-01" <= d <= "2026-10"})
sig3_count = {t:0 for t in TICKERS}; sig4_count = {t:0 for t in TICKERS}
months_with_any3, months_with_any4 = 0, 0
for m in seen_months:
    any3, any4 = False, False
    for t in TICKERS:
        dates, closes = data[t]; c = ch[t]
        # last trading day of month
        idx = max([i for i,d in enumerate(dates) if d[:7]==m])
        if np.isnan(c['low3'][idx]): continue
        if c['slope'][idx] <= 0 or c['low3'][idx] < 0: continue
        if closes[idx] < c['low3'][idx]: sig3_count[t]+=1; any3=True
        if closes[idx] < c['low4'][idx]: sig4_count[t]+=1; any4=True
    months_with_any3 += any3; months_with_any4 += any4
print(f"  months scanned: {len(seen_months)}, months with any -3 signal: {months_with_any3}, any -4: {months_with_any4}")
for t in TICKERS:
    print(f"  {t}: -3 months={sig3_count[t]}, -4 months={sig4_count[t]}")

# Forward returns from each -4 month-end signal (others) and -3 for mega caps
print("\n=== Forward performance of month-end signals (entry=signal close, exit touch of mid-line within 365d else 365d close) ===")
import json as _json
rows = []
for t in TICKERS:
    dates, closes = data[t]; c = ch[t]
    mega = t in ("AAPL","MSFT","NVDA","GOOGL","AMZN","META","BRK-B","AVGO","TSLA","JPM")
    k = 3 if mega else 4
    for m in seen_months:
        idx = max([i for i,d in enumerate(dates) if d[:7]==m])
        if np.isnan(c['low3'][idx]) or c['slope'][idx] <= 0 or c['low3'][idx] < 0: continue
        band = c['low3'][idx] if k==3 else c['low4'][idx]
        if not (closes[idx] < band): continue
        # dedupe: skip if previous month also signal
        entry, entry_d = closes[idx], dates[idx]
        fwd = {}
        for h in (63, 126, 252):
            j = min(idx+h, len(dates)-1)
            fwd[h] = closes[j]/entry-1
        # time to mid-line touch + max adverse excursion within 252d
        ttm, mae = None, 0.0
        for j in range(idx+1, min(idx+253, len(dates))):
            mae = min(mae, closes[j]/entry-1)
            if not np.isnan(c['mid'][j]) and closes[j] >= c['mid'][j]:
                ttm = j-idx; break
        rows.append(dict(ticker=t, date=entry_d, k=k, r3m=fwd[63], r6m=fwd[126], r12m=fwd[252], ttm_days=ttm, mae_12m=mae))
print(f"  n signals (month-end sampling): {len(rows)}")
if rows:
    import statistics
    for key in ("r3m","r6m","r12m"):
        vals = [r[key] for r in rows]
        print(f"  {key}: median {statistics.median(vals):+.1%}, mean {sum(vals)/len(vals):+.1%}, hit>0 {(sum(v>0 for v in vals)/len(vals)):.0%}")
    ttm_ok = [r['ttm_days'] for r in rows if r['ttm_days'] is not None]
    print(f"  reached mid-line within 12m: {len(ttm_ok)}/{len(rows)}" +
          (f", median {statistics.median(ttm_ok):.0f} trading days" if ttm_ok else ""))
    print(f"  median max adverse excursion (12m): {statistics.median([r['mae_12m'] for r in rows]):+.1%}")
    for r in rows[:40]:
        print(f"    {r['ticker']} {r['date']} -{r['k']}σ r12m={r['r12m']:+.0%} ttm={r['ttm_days']} mae={r['mae_12m']:+.0%}")
with open("verify_results.json","w") as f:
    _json.dump(rows, f, indent=1)
print("saved verify_results.json")
