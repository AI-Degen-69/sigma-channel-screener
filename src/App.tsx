import * as React from "react"
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent
} from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Table,
  TableHeader,
  TableRow,
  TableHead,
  TableBody,
  TableCell
} from "@/components/ui/table"
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Input } from "@/components/ui/input"
import { Separator } from "@/components/ui/separator"
import { Search, Copy, Check } from "lucide-react"

interface ScreenerRow {
  ticker: string
  date: string
  price: number
  mcap: number | null
  pe: number | null
  pb: number | null
  bars: number
  mid: number
  sd: number
  low3: number
  low4: number
  slope_up: boolean
  pos: number
  k: number
  off52w: number
  note: string
}

interface ScreenerChart {
  ticker: string
  dates: string[]
  close: (number | null)[]
  mid: (number | null)[]
  low3: (number | null)[]
  low4: (number | null)[]
  candles?: {
    dates: string[]
    o: (number | null)[]
    h: (number | null)[]
    l: (number | null)[]
    c: (number | null)[]
    mid: (number | null)[]
    low3: (number | null)[]
    low4: (number | null)[]
  }
}

interface ScreenerData {
  asof: string
  rows: ScreenerRow[]
  charts: Record<string, ScreenerChart>
}

const STIER = new Set(["AAPL","MSFT","NVDA","GOOGL","AMZN","META","BRK-B","AVGO","TSLA","JPM"])

type SeriesKey = "close" | "mid" | "low3" | "low4"

interface ChartSeries {
  close?: (number | null)[]
  mid: (number | null)[]
  low3: (number | null)[]
  low4: (number | null)[]
}

const seriesFor = (series: ChartSeries, key: SeriesKey): (number | null)[] => {
  if (key === "close") return series.close ?? []
  if (key === "mid") return series.mid
  if (key === "low3") return series.low3
  return series.low4
}

const sortValue = (row: ScreenerRow, key: string): number | string | null => {
  if (key === "buy") return row.k === 3 ? row.low3 : row.low4
  const raw: unknown = (row as unknown as Record<string, unknown>)[key]
  if (typeof raw === "boolean") return raw ? 1 : 0
  if (typeof raw === "number" || typeof raw === "string") return raw
  return null
}

const compareValues = (a: number | string, b: number | string): number => {
  if (typeof a === "number" && typeof b === "number") return a - b
  return String(a).localeCompare(String(b))
}

const signalBadge = (note: string | undefined) => {
  if (note?.startsWith("ACTION")) {
    return <Badge className="bg-emerald-500/10 text-emerald-500 border-emerald-500/20">ACTION</Badge>
  }
  if (note?.startsWith("WATCH")) {
    return <Badge className="bg-amber-500/10 text-amber-500 border-amber-500/20">WATCH</Badge>
  }
  if (note?.startsWith("SKIP")) return <Badge variant="destructive">SKIP</Badge>
  return <Badge variant="outline">HOLD</Badge>
}

const positionClass = (pos: number | null, k: number | null): string => {
  if (pos === null || k === null) return "text-foreground"
  if (pos <= -k) return "text-emerald-500 font-bold"
  if (pos <= -(k - 0.5)) return "text-amber-500 font-semibold"
  if (pos >= 2) return "text-rose-500"
  return "text-foreground"
}

export default function App() {
  const [data, setData] = React.useState<ScreenerData | null>(null)
  const [selectedTicker, setSelectedTicker] = React.useState<string>("MCD")
  const [activeTab, setActiveTab] = React.useState<string>("all")
  const [searchQuery, setSearchQuery] = React.useState<string>("")
  const [slopeFilter, setSlopeFilter] = React.useState<string>("all")
  const [sortKey, setSortKey] = React.useState<string>("pos")
  const [sortDir, setSortDir] = React.useState<number>(1)
  const [chartMode, setChartMode] = React.useState<"line" | "candle">("line")
  const [copied, setCopied] = React.useState<boolean>(false)
  const [toastMessage, setToastMessage] = React.useState<string | null>(null)
  const [loadError, setLoadError] = React.useState<string | null>(null)

  const canvasRef = React.useRef<HTMLCanvasElement | null>(null)
  const [hoverIndex, setHoverIndex] = React.useState<number>(-1)
  const [tooltipData, setTooltipData] = React.useState<{ x: number; y: number; text: string } | null>(null)

  React.useEffect(() => {
    let cancelled = false
    fetch("/screener_data.json?v=" + Date.now())
      .then(res => {
        if (!res.ok) throw new Error(`HTTP ${res.status} ${res.statusText}`)
        return res.json() as Promise<ScreenerData>
      })
      .then((d: ScreenerData) => {
        if (cancelled) return
        setData(d)
        // Select deepest discount
        if (d.rows && d.rows.length > 0) {
          const sorted = [...d.rows].sort((a, b) => (a.pos ?? 99) - (b.pos ?? 99))
          setSelectedTicker(sorted[0].ticker)
        }
      })
      .catch((err: unknown) => {
        if (cancelled) return
        console.error("Error loading screener data:", err)
        setLoadError(err instanceof Error ? err.message : String(err))
      })
    return () => {
      cancelled = true
    }
  }, [])

  const selectedRow = React.useMemo(() => {
    return data?.rows.find(r => r.ticker === selectedTicker) || null
  }, [data, selectedTicker])

  const filteredRows = React.useMemo(() => {
    if (!data) return []
    return data.rows.filter(r => {
      if (activeTab === "sig" && !/^(ACTION|WATCH)/.test(r.note || "")) return false
      if (activeTab === "tier" && !STIER.has(r.ticker)) return false
      if (slopeFilter === "up" && !r.slope_up) return false
      if (slopeFilter === "down" && r.slope_up) return false
      if (searchQuery) {
        const q = searchQuery.toUpperCase()
        if (!r.ticker.includes(q) && !(r.note || "").toUpperCase().includes(q)) return false
      }
      return true
    }).sort((a, b) => {
      const va = sortValue(a, sortKey)
      const vb = sortValue(b, sortKey)
      if (va === null && vb === null) return 0
      if (va === null) return 1
      if (vb === null) return -1
      const cmp = compareValues(va, vb)
      if (cmp !== 0) return cmp * sortDir
      return a.ticker.localeCompare(b.ticker)
    })
  }, [data, activeTab, slopeFilter, searchQuery, sortKey, sortDir])

  const stats = React.useMemo(() => {
    if (!data) return { total: 0, action: 0, watch: 0, leader: null as ScreenerRow | null }
    let action = 0
    let watch = 0
    let leader: ScreenerRow | null = null

    data.rows.forEach(r => {
      if ((r.note || "").startsWith("ACTION")) action++
      else if ((r.note || "").startsWith("WATCH")) watch++
      if (typeof r.pos === "number" && (!leader || r.pos < leader.pos)) {
        leader = r
      }
    })
    return { total: data.rows.length, action, watch, leader }
  }, [data])

  // Chart rendering
  const renderChart = React.useCallback((t: string, hover: number = -1) => {
    if (!data || !canvasRef.current) return
    const chart = data.charts[t]
    if (!chart) return

    const cv = canvasRef.current
    const ctx = cv.getContext("2d")
    if (!ctx) return

    const rect = cv.getBoundingClientRect()
    const dpr = window.devicePixelRatio || 1
    cv.width = rect.width * dpr
    cv.height = rect.height * dpr
    ctx.scale(dpr, dpr)
    const W = rect.width
    const H = rect.height

    ctx.clearRect(0, 0, W, H)

    const cm = chartMode === "candle" && chart.candles ? chart.candles : null
    const D: ChartSeries & { dates: string[] } = cm
      ? { close: cm.c, dates: cm.dates, mid: cm.mid, low3: cm.low3, low4: cm.low4 }
      : chart
    const n = D.dates.length
    if (n < 2) return

    const series: [SeriesKey, string, number][] = [
      ["mid", "#38bdf8", 1.5],
      ["low3", "#22c55e", 1.5],
      ["low4", "#f59e0b", 1.5]
    ]
    if (!cm) series.unshift(["close", "#f4f4f5", 2])

    let lo = Infinity
    let hi = -Infinity
    for (const [k] of series) {
      for (const v of seriesFor(D, k)) {
        if (v !== null) {
          lo = Math.min(lo, v)
          hi = Math.max(hi, v)
        }
      }
    }
    if (cm) {
      for (let i = 0; i < n; i++) {
        const hh = cm.h[i]
        const ll = cm.l[i]
        if (hh !== null && ll !== null) {
          lo = Math.min(lo, ll)
          hi = Math.max(hi, hh)
        }
      }
    }

    const L = 48, R = 52, T = 12, B = 24
    const pad = (hi - lo) * 0.08 || 1
    const X = (i: number) => L + (i / (n - 1)) * (W - L - R)
    const Y = (v: number) => T + (1 - (v - (lo - pad)) / (hi + pad - (lo - pad))) * (H - T - B)

    // Price grid
    ctx.strokeStyle = "rgba(255,255,255,0.06)"
    ctx.lineWidth = 1
    ctx.fillStyle = "rgba(255,255,255,0.4)"
    ctx.font = "10px monospace"
    for (let g = 0; g <= 4; g++) {
      const v = lo - pad + (hi - lo + 2 * pad) * (g / 4)
      const y = Y(v)
      ctx.beginPath()
      ctx.moveTo(L, y)
      ctx.lineTo(W - R, y)
      ctx.stroke()
      ctx.fillText(v.toFixed(0), W - R + 6, y + 3.5)
    }

    // Candlesticks
    if (cm) {
      const bw = Math.max(2, ((W - L - R) / n) * 0.65)
      for (let i = 0; i < n; i++) {
        const o = cm.o[i], h = cm.h[i], l = cm.l[i], cl = cm.c[i]
        if (o == null || h == null || l == null || cl == null) continue
        const col = cl >= o ? "#22c55e" : "#ef4444"
        const x = X(i)
        ctx.strokeStyle = col
        ctx.beginPath()
        ctx.moveTo(x, Y(h))
        ctx.lineTo(x, Y(l))
        ctx.stroke()
        const yO = Y(o), yC = Y(cl)
        ctx.fillStyle = col
        ctx.fillRect(x - bw / 2, Math.min(yO, yC), bw, Math.max(1.5, Math.abs(yC - yO)))
      }
    }

    // Regression bands & close line
    const colors: Record<SeriesKey, string> = { close: "#f4f4f5", mid: "#38bdf8", low3: "#22c55e", low4: "#f59e0b" }
    for (const [k, , w] of series) {
      ctx.strokeStyle = colors[k]
      ctx.lineWidth = w
      ctx.beginPath()
      let pen = false
      seriesFor(D, k).forEach((v, i) => {
        if (v === null) { pen = false; return }
        const x = X(i), y = Y(v)
        if (!pen) { ctx.moveTo(x, y); pen = true } else ctx.lineTo(x, y)
      })
      ctx.stroke()
    }

    // Hover crosshair
    if (hover >= 0 && hover < n) {
      const hx = X(hover)
      const hp = cm ? cm.c[hover] : chart.close[hover]
      ctx.save()
      ctx.strokeStyle = "rgba(255,255,255,0.3)"
      ctx.setLineDash([4, 4])
      ctx.beginPath()
      ctx.moveTo(hx, T)
      ctx.lineTo(hx, H - B)
      ctx.stroke()
      if (hp != null) {
        ctx.beginPath()
        ctx.moveTo(L, Y(hp))
        ctx.lineTo(W - R, Y(hp))
        ctx.stroke()
        ctx.setLineDash([])
        ctx.fillStyle = "#ffffff"
        ctx.beginPath()
        ctx.arc(hx, Y(hp), 3.5, 0, Math.PI * 2)
        ctx.fill()
      }
      ctx.restore()
    }
  }, [data, chartMode])

  React.useEffect(() => {
    if (selectedTicker) {
      renderChart(selectedTicker, hoverIndex)
    }
  }, [selectedTicker, chartMode, hoverIndex, renderChart])

  const handleCanvasMouseMove = (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (!data || !canvasRef.current) return
    const chart = data.charts[selectedTicker]
    if (!chart) return

    const cv = canvasRef.current
    const rect = cv.getBoundingClientRect()
    const mx = e.clientX - rect.left
    // Candle series is a shorter window than the 6Y series, so derive the hovered
    // index from the same series the chart is currently drawing.
    const cm = chartMode === "candle" && chart.candles ? chart.candles : null
    const dates = cm ? cm.dates : chart.dates
    const n = dates.length
    const L = 48, R = 52
    const W = rect.width
    if (n < 2) return

    let best = 0
    let bd = 1e9
    for (let i = 0; i < n; i++) {
      const x = L + (i / (n - 1)) * (W - L - R)
      const d = Math.abs(x - mx)
      if (d < bd) { bd = d; best = i }
    }

    setHoverIndex(best)
    const date = dates[best]
    const price = (cm ? cm.c : chart.close)[best]
    const mid = (cm ? cm.mid : chart.mid)[best]
    const l3 = (cm ? cm.low3 : chart.low3)[best]

    setTooltipData({
      x: Math.min(e.clientX - rect.left + 15, rect.width - 160),
      y: Math.max(e.clientY - rect.top - 50, 10),
      text: `${date} | $${price?.toFixed(2) ?? "—"} (Mid: $${mid?.toFixed(2) ?? "—"} | −3σ: $${l3?.toFixed(2) ?? "—"})`
    })
  }

  const handleCopyPrompt = async () => {
    if (!selectedRow) return
    const posTxt = selectedRow.pos != null ? `${selectedRow.pos >= 0 ? "+" : ""}${selectedRow.pos.toFixed(2)}` : "—"
    const prompt = `Fundamental check for ${selectedRow.ticker} at $${selectedRow.price?.toFixed(2) ?? "—"} (${posTxt} σ below trend).\n` +
      `With web search on, answer ONLY:\n(1) TEMPORARY recoverable dip or PERMANENT damage? Cite the cause + 2-3 recent sources.\n` +
      `(2) Bankruptcy/severe distress risk in 12-24 months? Cover debt, interest coverage, FCF, maturities, dividend.\n` +
      `End with GREEN LIGHT or RED LIGHT + one paragraph of reasoning.`

    try {
      await navigator.clipboard.writeText(prompt)
      setCopied(true)
      setToastMessage("AI check prompt copied to clipboard!")
    } catch (err: unknown) {
      console.error("Clipboard write failed:", err)
      setToastMessage("Copy failed — select the prompt text manually.")
    }
    setTimeout(() => {
      setCopied(false)
      setToastMessage(null)
    }, 2500)
  }

  const tvSymbol = (t: string) => {
    if (t === "BRK-B") return "NYSE:BRK.B"
    const nyse = new Set(["JPM","XOM","JNJ","UNH","MCD","CRM","MRK","ABBV","KO","WMT","HD","DIS","NKE","CAT","GE","BA","GS","MS","V","MA","IBM","ORCL","LLY"])
    return (nyse.has(t) ? "NYSE:" : "NASDAQ:") + t
  }

  const sortBy = (key: string) => {
    if (key === sortKey) {
      setSortDir(-sortDir)
      return
    }
    setSortKey(key)
    setSortDir(1)
  }

  const renderSortHead = (label: string, key: string, align = "text-left") => (
    <TableHead
      key={key}
      scope="col"
      aria-sort={sortKey === key ? (sortDir === 1 ? "ascending" : "descending") : "none"}
      tabIndex={0}
      onClick={() => sortBy(key)}
      onKeyDown={e => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault()
          sortBy(key)
        }
      }}
      className={`cursor-pointer select-none ${align}`}
    >
      {label}
      <span aria-hidden="true" className="ml-1 text-muted-foreground">
        {sortKey === key ? (sortDir === 1 ? "↑" : "↓") : ""}
      </span>
    </TableHead>
  )

  return (
    <div className="flex min-h-screen flex-col bg-background text-foreground">
      {/* ═══ SITE HEADER ═══ */}
      <header className="sticky top-0 z-40 flex h-14 items-center justify-between border-b border-border bg-background/80 px-6 backdrop-blur-md">
        <div className="flex items-center gap-3">
          <div className="flex size-7 items-center justify-center rounded-lg bg-primary text-primary-foreground font-mono font-bold text-sm">
            σ
          </div>
          <span className="font-semibold text-sm tracking-tight">σ-Channel Screener</span>
          <Separator orientation="vertical" className="h-4" />
          <span className="text-xs text-muted-foreground font-mono">2500-day OLS Regression</span>
        </div>
        <div className="flex items-center gap-3 text-xs text-muted-foreground">
          <Badge variant="outline" className="font-mono text-[11px]">
            preset: nova
          </Badge>
          <span>{data ? `as of ${data.asof}` : loadError ? "data unavailable" : "loading..."}</span>
        </div>
      </header>

      {/* ═══ MAIN DASHBOARD VIEW ═══ */}
      <main className="flex-1 space-y-6 p-6">
        {loadError && (
          <Card className="border-destructive/40" role="alert">
            <CardHeader className="pb-2">
              <CardTitle className="text-base text-destructive">Could not load screener_data.json</CardTitle>
              <CardDescription className="font-mono text-xs">{loadError}</CardDescription>
            </CardHeader>
            <CardContent>
              <Button size="sm" variant="outline" onClick={() => window.location.reload()}>
                Retry
              </Button>
            </CardContent>
          </Card>
        )}

        {/* KPI CARDS */}
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardDescription>Screened Universe</CardDescription>
              <Badge variant="outline" className="text-xs">US Large-Cap</Badge>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold font-mono">{stats.total} Tickers</div>
              <p className="text-xs text-muted-foreground mt-1">Market Cap &gt; $50B · 10+ Years History</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardDescription>Action Required</CardDescription>
              <Badge variant="secondary" className="text-emerald-500 bg-emerald-500/10 border-emerald-500/20">
                {stats.action} Signals
              </Badge>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold font-mono text-emerald-500">{stats.action}</div>
              <p className="text-xs text-muted-foreground mt-1">S-Tier ≤ −3σ / Standard ≤ −4σ</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardDescription>Radar Watch</CardDescription>
              <Badge variant="secondary" className="text-amber-500 bg-amber-500/10 border-amber-500/20">
                {stats.watch} Approaching
              </Badge>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold font-mono text-amber-500">{stats.watch}</div>
              <p className="text-xs text-muted-foreground mt-1">Within 0.5σ of statistical buy line</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardDescription>Deepest Discount</CardDescription>
              <Badge variant="outline" className="font-mono">{stats.leader?.pos != null ? `${stats.leader.pos.toFixed(2)}σ` : "—"}</Badge>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold font-mono">{stats.leader?.ticker ?? "—"}</div>
              <p className="text-xs text-muted-foreground mt-1">
                {stats.leader ? (() => {
                  const buyVal = stats.leader.k === 3 ? stats.leader.low3 : stats.leader.low4
                  const buyTxt = buyVal != null ? `$${buyVal.toFixed(2)}` : "—"
                  return `$${stats.leader.price?.toFixed(2) ?? "—"} (Buy: ${buyTxt})`
                })() : "—"}
              </p>
            </CardContent>
          </Card>
        </div>

        {/* INTERACTIVE CHART */}
        <Card className="overflow-hidden">
          <CardHeader className="flex flex-row items-center justify-between pb-4">
            <div>
              <CardTitle className="text-lg">
                {selectedRow ? `${selectedRow.ticker} — 2500-Day σ-Channel Analysis` : "Channel Chart"}
              </CardTitle>
              <CardDescription className="text-xs">
                Linear regression midline (take-profit) &amp; standard deviation buy envelopes
              </CardDescription>
            </div>
            <div className="flex gap-2">
              <Button
                variant={chartMode === "line" ? "default" : "outline"}
                size="sm"
                onClick={() => setChartMode("line")}
              >
                Trend (6Y)
              </Button>
              <Button
                variant={chartMode === "candle" ? "default" : "outline"}
                size="sm"
                onClick={() => setChartMode("candle")}
              >
                Candles (2Y)
              </Button>
            </div>
          </CardHeader>
          <CardContent className="relative px-4 pb-4">
            <div className="h-[280px] w-full rounded-md border border-border/40 bg-zinc-950/60 p-2">
              <canvas
                ref={canvasRef}
                role="img"
                aria-label={`σ-channel price chart for ${selectedTicker}`}
                className="h-full w-full cursor-crosshair"
                onMouseMove={handleCanvasMouseMove}
                onMouseLeave={() => { setHoverIndex(-1); setTooltipData(null); }}
              />
            </div>
            {tooltipData && (
              <div
                className="pointer-events-none absolute z-20 rounded bg-popover px-2.5 py-1 text-xs font-mono text-popover-foreground shadow-md border border-border"
                style={{ left: tooltipData.x, top: tooltipData.y }}
              >
                {tooltipData.text}
              </div>
            )}
          </CardContent>
        </Card>

        {/* DATA TABLE & DETAIL SPLIT */}
        <div className="grid gap-6 lg:grid-cols-3">
          {/* Table (2 cols) */}
          <div className="lg:col-span-2 space-y-4">
            <Card>
              <CardHeader className="pb-3">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <Tabs value={activeTab} onValueChange={setActiveTab}>
                    <TabsList>
                      <TabsTrigger value="all">All Tickers</TabsTrigger>
                      <TabsTrigger value="sig">Action + Watch</TabsTrigger>
                      <TabsTrigger value="tier">S-Tier Only</TabsTrigger>
                    </TabsList>
                  </Tabs>

                  <div className="flex items-center gap-2">
                    <div className="flex items-center gap-1" role="group" aria-label="Trend slope filter">
                      <Button
                        variant={slopeFilter === "all" ? "default" : "outline"}
                        size="sm"
                        aria-pressed={slopeFilter === "all"}
                        onClick={() => setSlopeFilter("all")}
                      >
                        Any Slope
                      </Button>
                      <Button
                        variant={slopeFilter === "up" ? "default" : "outline"}
                        size="sm"
                        aria-pressed={slopeFilter === "up"}
                        onClick={() => setSlopeFilter("up")}
                      >
                        Slope ↑
                      </Button>
                      <Button
                        variant={slopeFilter === "down" ? "default" : "outline"}
                        size="sm"
                        aria-pressed={slopeFilter === "down"}
                        onClick={() => setSlopeFilter("down")}
                      >
                        Slope ↓
                      </Button>
                    </div>

                    <div className="relative">
                      <Search className="absolute left-2.5 top-2.5 size-3.5 text-muted-foreground" />
                      <Input
                        aria-label="Search tickers"
                        placeholder="Search ticker..."
                        value={searchQuery}
                        onChange={e => setSearchQuery(e.target.value)}
                        className="h-8 w-40 pl-8 text-xs"
                      />
                    </div>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="p-0">
                <div className="max-h-[500px] overflow-auto">
                  <Table>
                    <TableHeader className="sticky top-0 bg-card z-10">
                      <TableRow>
                        {renderSortHead("Ticker", "ticker")}
                        {renderSortHead("Price", "price", "text-right")}
                        {renderSortHead("σ Position", "pos", "text-right")}
                        {renderSortHead("Buy Target", "buy", "text-right")}
                        {renderSortHead("Slope", "slope_up", "text-right")}
                        {renderSortHead("52w Drawdown", "off52w", "text-right")}
                        <TableHead scope="col" className="text-right">Signal</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {filteredRows.map(r => {
                        const isSelected = r.ticker === selectedTicker
                        const isStier = STIER.has(r.ticker)
                        const buyVal = r.k === 3 ? r.low3 : r.low4
                        const buyPrice = buyVal != null ? `−${r.k}σ @ $${buyVal.toFixed(2)}` : "—"
                        const sigBadge = signalBadge(r.note)
                        const sdClass = positionClass(r.pos ?? null, r.k ?? null)

                        return (
                          <TableRow
                            key={r.ticker}
                            tabIndex={0}
                            data-state={isSelected ? "selected" : undefined}
                            className={`cursor-pointer font-mono text-xs ${isSelected ? "bg-accent/50" : ""}`}
                            onClick={() => setSelectedTicker(r.ticker)}
                            onKeyDown={e => {
                              if (e.key === "Enter" || e.key === " ") {
                                e.preventDefault()
                                setSelectedTicker(r.ticker)
                              }
                            }}
                          >
                            <TableCell className="font-sans font-semibold flex items-center gap-2">
                              {isStier && <span className="size-1.5 rounded-full bg-sky-400" title="S-Tier Top 10" />}
                              {r.ticker}
                            </TableCell>
                            <TableCell className="text-right">{r.price != null ? `$${r.price.toFixed(2)}` : "—"}</TableCell>
                            <TableCell className={`text-right ${sdClass}`}>
                              {r.pos != null ? `${r.pos > 0 ? "+" : ""}${r.pos.toFixed(2)}σ` : "—"}
                            </TableCell>
                            <TableCell className="text-right text-muted-foreground">{buyPrice}</TableCell>
                            <TableCell className={`text-right ${r.slope_up ? "text-emerald-500" : "text-rose-500"}`}>
                              {r.pos !== undefined ? (r.slope_up ? "↑ Up" : "↓ Flat") : "—"}
                            </TableCell>
                            <TableCell className="text-right">
                              {r.off52w !== undefined && r.off52w !== null ? `${(r.off52w * 100).toFixed(1)}%` : "—"}
                            </TableCell>
                            <TableCell className="text-right">{sigBadge}</TableCell>
                          </TableRow>
                        )
                      })}
                    </TableBody>
                  </Table>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Inspector Detail (1 col) */}
          <div className="space-y-4">
            {selectedRow ? (
              <Card>
                <CardHeader className="pb-3">
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="flex items-center gap-2">
                        <CardTitle className="text-xl font-mono">{selectedRow.ticker}</CardTitle>
                        <Badge variant="outline" className="text-[10px]">
                          {STIER.has(selectedRow.ticker) ? "S-Tier Asset" : "Standard Universe"}
                        </Badge>
                      </div>
                      <CardDescription className="text-xs mt-1">
                        {selectedRow.note || "Hold / Cash state"}
                      </CardDescription>
                    </div>
                    <div className="text-right">
                      <div className="text-xl font-bold font-mono">${selectedRow.price?.toFixed(2) ?? "—"}</div>
                      <span className="text-[11px] text-muted-foreground">{selectedRow.date}</span>
                    </div>
                  </div>
                </CardHeader>
                <CardContent className="space-y-4 text-xs">
                  {/* METRIC GRID */}
                  <div className="grid grid-cols-2 gap-2 border-y border-border py-3 font-mono">
                    <div>
                      <span className="text-[10px] text-muted-foreground block uppercase">σ Position</span>
                      <span className="text-sm font-semibold">{selectedRow.pos != null ? `${selectedRow.pos.toFixed(2)}σ` : "—"}</span>
                    </div>
                    <div>
                      <span className="text-[10px] text-muted-foreground block uppercase">Buy Target</span>
                      <span className="text-sm font-semibold">
                        {(() => {
                          const buyVal = selectedRow.k === 3 ? selectedRow.low3 : selectedRow.low4
                          return buyVal != null ? `−${selectedRow.k}σ @ $${buyVal.toFixed(2)}` : "—"
                        })()}
                      </span>
                    </div>
                    <div>
                      <span className="text-[10px] text-muted-foreground block uppercase">Take-Profit Mid</span>
                      <span className="text-sm font-semibold text-emerald-500">
                        {selectedRow.mid != null && selectedRow.price ? (
                          `$${selectedRow.mid.toFixed(2)} (+${Math.round((selectedRow.mid / selectedRow.price - 1) * 100)}%)`
                        ) : "—"}
                      </span>
                    </div>
                    <div>
                      <span className="text-[10px] text-muted-foreground block uppercase">Valuation</span>
                      <span className="text-sm font-semibold">
                        P/E {selectedRow.pe ? selectedRow.pe.toFixed(1) : "n/a"}
                      </span>
                    </div>
                  </div>

                  {/* TRADINGVIEW EMBED */}
                  <div className="space-y-1.5">
                    <span className="font-semibold text-xs flex items-center justify-between text-muted-foreground">
                      <span>TradingView Daily Chart</span>
                      <span className="text-[10px]">● Live</span>
                    </span>
                    <iframe
                      title="TradingView"
                      className="w-full h-52 rounded border border-border bg-black"
                      src={`https://s.tradingview.com/widgetembed/?symbol=${encodeURIComponent(tvSymbol(selectedRow.ticker))}&interval=D&theme=dark&style=1&withdateranges=1&hide_side_toolbar=1&allow_symbol_change=0`}
                    />
                  </div>

                  {/* AI THESIS CHECK PROMPT */}
                  <div className="rounded-lg border border-border/80 bg-zinc-950 p-3 space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="font-semibold text-[11px] uppercase tracking-wider text-muted-foreground">
                        AI Fundamental Check
                      </span>
                      <Button variant="ghost" size="sm" onClick={handleCopyPrompt} className="h-6 px-2 text-[11px] gap-1">
                        {copied ? <Check className="size-3 text-emerald-500" /> : <Copy className="size-3" />}
                        {copied ? "Copied" : "Copy"}
                      </Button>
                    </div>
                    <pre className="text-[11px] text-zinc-400 font-mono whitespace-pre-wrap leading-relaxed">
                      {`Fundamental check for ${selectedRow.ticker} at $${selectedRow.price?.toFixed(2) ?? "—"} (${selectedRow.pos != null ? `${selectedRow.pos >= 0 ? "+" : ""}${selectedRow.pos.toFixed(2)}σ` : "—"} below trend).`}
                    </pre>
                  </div>
                </CardContent>
              </Card>
            ) : (
              <Card>
                <CardContent className="p-6 text-center text-muted-foreground text-xs">
                  Select a stock from the table to view its full σ-channel analysis.
                </CardContent>
              </Card>
            )}
          </div>
        </div>
      </main>

      {/* TOAST NOTIFICATION */}
      {toastMessage && (
        <div
          role="status"
          aria-live="polite"
          className="fixed bottom-4 right-4 z-50 rounded-lg border border-border bg-popover px-4 py-2 text-xs text-popover-foreground shadow-lg flex items-center gap-2"
        >
          <Check className="size-4 text-emerald-500" />
          <span>{toastMessage}</span>
        </div>
      )}
    </div>
  )
}
