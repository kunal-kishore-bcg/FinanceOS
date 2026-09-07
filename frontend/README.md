# FinanceOS Frontend

React + Vite, plain fetch, no component library, one stylesheet
(`src/styles.css`). Talks to the FastAPI backend in `../backend`.

## Setup

```bash
cd frontend
npm install
cp .env.example .env    # defaults to http://localhost:8000, change if needed
npm run dev             # http://localhost:5173
```

The backend's CORS config (`backend/app/main.py`) already allows
`http://localhost:5173` — Vite's default dev port — so this should
work with zero backend changes.

Backend must be running first (`cd ../backend && uvicorn app.main:app --reload`)
with migrations applied and seed data loaded (see `../backend/README.md`).

## Demo login
`analyst@financeos.demo` / `password123` (or `manager@financeos.demo`
— same password). Seeded by `backend/app/seed/seed_data.py`.

## Known gap
The **Confidence** column in the invoice table always shows "Not
provided by AI" — `claude_client.py`'s tool schema only returns
`recommendation` and `rationale`, no confidence score exists anywhere
in the pipeline yet. This is deliberate honesty, not a bug: adding a
real confidence value is a backend change (extend the tool schema +
prompt), not something the frontend can fix on its own.

## Not built
No automated frontend tests. No loading skeleton beyond a plain
"Loading invoices…" text. No client-side routing library — the
login/dashboard switch is plain React state in `App.jsx` (two screens
didn't justify adding react-router-dom as a dependency).
