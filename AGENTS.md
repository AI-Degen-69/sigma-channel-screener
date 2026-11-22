# AGENTS.md

React 19 + Tailwind v4 + Vite dashboard (`index.html` + `src/`) for the σ-channel screener, plus the Python screen that generates its data. This is the only dashboard UI. Do not add standalone HTML dashboards.

## Commands

```bash
pnpm install     # Node 20.19+ or >=22.12 (Vite 8 requirement) and pnpm; lockfile is pnpm-lock.yaml
pnpm dev         # Vite dev server on http://localhost:5173
pnpm build       # tsc -b && vite build -> dist/
pnpm lint        # oxlint (no config file, default rules)
```

Python side (not npm): `python monthly_screener.py` writes `screener_data.json` (Python 3.10+, NumPy).

## Hard rules

**The dashboard is `index.html` + `src/`, served by Vite.** Preview it with `pnpm dev` on http://localhost:5173. Opening `index.html` as a plain file shows a blank page. There are no standalone HTML dashboards — do not add one.

**`screener_data.json` lives at the repo root and is served by the `screenerData()` plugin in `vite.config.ts`.** In dev the plugin serves that root file at `/screener_data.json` with `Cache-Control: no-store`; on build it emits the same bytes into `dist/`. Keep it that way:

- Never copy or move it into `public/` — that is the stale duplicate the plugin exists to prevent.
- Don't rename or relocate it: `monthly_screener.py` writes it at the repo root, and `src/App.tsx` fetches it from there.
- `dist/` is gitignored and rebuilt, so never commit a second generated copy.
