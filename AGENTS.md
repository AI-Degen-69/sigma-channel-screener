# AGENTS.md

React 19 + Tailwind v4 + Vite dashboard for the σ-channel screener, plus standalone HTML dashboards and the Python screen that generates their shared data.

## Commands

```bash
pnpm install     # Node 20+, pnpm (lockfile: pnpm-lock.yaml)
pnpm dev         # Vite dev server (default http://localhost:5173)
pnpm build       # tsc -b && vite build -> dist/
pnpm lint        # oxlint
```

Python side (not npm): `python monthly_screener.py` regenerates `screener_data.json` / `screener_latest.md`.

## Hard rules

**Keep `index.vanilla.html` zero-build.** It is a self-contained page: inline `<style>`/`<script>`, no imports, no TypeScript, no npm packages, no bundler step. It must keep working when served as a plain file over HTTP (`python -m http.server 8000` → `http://localhost:8000/index.vanilla.html`), so don't convert it to modules, move it into `src/`, or make it depend on Vite. `dashboard.html` is the older reference page with the same constraint.

**`screener_data.json` lives at the repo root and is served by the Vite plugin.** The `screenerData()` plugin in `vite.config.ts` serves that root file at `/screener_data.json` in dev (`Cache-Control: no-store`) and emits the same bytes into `dist/` on build. Keep it that way:

- Never copy or move it into `public/` — that re-introduces the stale duplicate the plugin exists to prevent.
- Don't rename it or change its location; `monthly_screener.py` writes it next to the dashboards and both `index.vanilla.html` and the React app fetch `screener_data.json`.
- Don't commit a second generated copy (`dist/` is ignored and rebuilt).
