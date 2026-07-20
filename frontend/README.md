# Frontend — HR & Admin Agent Dashboard

React + Vite + TypeScript admin dashboard for the CV Ranking module. Talks
to the backend exclusively over HTTP (`VITE_API_BASE_URL`) — never imports
backend code directly, so the two can be deployed/scaled independently.

## Structure

```
src/
  api/
    client.ts    # fetch wrapper + typed API calls
    types.ts     # TS types mirroring backend/app/api/schemas.py
  components/
    Layout.tsx           # header/shell
    PipelineActions.tsx  # fetch / score / rank / run-all buttons
    VerdictBadge.tsx      # colored STRONG HIRE / RECOMMEND / etc. badge
  pages/
    Dashboard.tsx         # all positions overview
    PositionDetail.tsx    # ranked candidates table for one position
```

## Setup

```powershell
cd frontend
npm install
copy .env.example .env
```

Ports are set in `.env` (`VITE_DEV_PORT=5288`, backend proxy target `8808`).
Only change them if those ports are somehow taken on your machine.

## Running

```powershell
npm run dev
```

Opens at http://localhost:5288 (http://127.0.0.1:5288 also works). The Vite
dev server proxies `/positions`, `/pipeline`, and `/reports` to the backend
on port **8808**. Requires the backend API to be running
(`cd ../backend && python main.py`).

Ports are fixed in `.env` (`VITE_DEV_PORT=5288`, `VITE_API_PROXY_TARGET=...8808`)
with `strictPort: true` so Vite will not silently jump to another port.

## Building for production

```powershell
npm run build
```

Outputs static files to `dist/`, which can be served by any static host or
folded into the backend later.
