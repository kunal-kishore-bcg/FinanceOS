# FinanceOS — Invoice Exception Triage

A working web application built for the BCG Enterprise Services GenAI Deployment technical assessment. Implements Process 1: Invoice Exception Triage — accepting invoice submissions, matching against a PO register, running deterministic exception checks, and generating AI-powered triage recommendations via the Anthropic Claude API.

## Architecture

- **Frontend:** React + Vite
- **Backend:** FastAPI (Python)
- **Database:** SQLite with Alembic migrations
- **AI:** Anthropic Claude API with tool-use mode for structured JSON output
- **PDF extraction:** pdfplumber

See `docs/architecture.png` for the full system diagram.

## Prerequisites

- Python 3.9+
- Node.js 18+
- An Anthropic API key

## Setup

### Backend

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Create a `.env` file in the `backend/` directory (see `.env.example`):

```
ANTHROPIC_API_KEY=your-key-here
JWT_SECRET_KEY=your-secret-here
DATABASE_URL=sqlite:///./financeos.db
```

Run migrations and seed data:

```bash
alembic upgrade head
pip install bcrypt==4.0.1
pip install httpx==0.27.0
python3 -m app.seed.seed_data
```

Start the backend:

```bash
uvicorn app.main:app --reload
```

Backend runs on `http://localhost:8000`. API docs at `http://localhost:8000/docs`.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend runs on `http://localhost:5173`.

## Demo Credentials

- `analyst@financeos.demo` / `password123`
- `manager@financeos.demo` / `password123`

## Key Features

- Manual invoice entry with full AI triage pipeline
- PDF invoice upload with automatic field extraction
- Rule engine producing exception flags (PO mismatch, duplicate detection, amount overage, unrecognised vendor)
- Claude API integration with tool-use mode for structured Approve/Escalate/Reject recommendations
- Human confirm and override flow with full audit log
- Dashboard with exception stats, override rate, and average resolution time
- AI rationale visible on hover
- Graceful AI failure fallback state

## Resetting the Database

To reset invoices to the clean seed state for demo purposes:

```bash
cd backend
python3 -m app.seed.reset_invoices
```

## Known Compatibility Notes

- Requires `bcrypt==4.0.1` (not 5.x) due to passlib compatibility with Python 3.9
- Requires `httpx==0.27.0` due to anthropic SDK proxy argument compatibility

## Design Decisions

See `docs/design-decisions.md` for key architectural decisions and trade-offs.
