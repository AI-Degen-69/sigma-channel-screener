# AGENTS.md

React 19 + Tailwind v4 + Vite dashboard for the σ-channel screener, plus two zero-build standalone HTML pages (`index.vanilla.html`, `dashboard.html`) and the Python screen that generates their shared data.

## Commands

```bash
pnpm install     # Node 20.19+ or >=22.12 (Vite 8 requirement) and pnpm; lockfile is pnpm-lock.yaml
pnpm dev         # Vite dev server on http://localhost:5173
pnpm build       # tsc -b && vite build -> dist/
pnpm lint        # oxlint (no config file, default rules)
```

Python side (not npm): `python monthly_screener.py` writes `screener_data.json` and `screener_latest.md` (Python 3.10+, NumPy).

## Hard rules

**Keep `index.vanilla.html` zero-build.** It is self-contained on purpose: inline `<style>`/`<script>`, no module imports, no TypeScript, no npm packages, no bundler. It must keep working when served as a plain file over HTTP (`python -m http.server 8000` → `http://localhost:8000/index.vanilla.html`), so don't move it into `src/` or make it depend on Vite. `dashboard.html` is the older reference page with the same constraint.

**`screener_data.json` lives at the repo root and is served by the `screenerData()` plugin in `vite.config.ts`.** In dev the plugin serves that root file at `/screener_data.json` with `Cache-Control: no-store`; on build it emits the same bytes into `dist/`. Keep it that way:

- Never copy or move it into `public/` — that is the stale duplicate the plugin exists to prevent.
- Don't rename or relocate it: `monthly_screener.py` writes it at the repo root, and both `index.vanilla.html` and `src/App.tsx` fetch it from there.
- `dist/` is gitignored and rebuilt, so never commit a second generated copy.
