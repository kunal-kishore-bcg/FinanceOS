# FinanceOS Backend — Foundation Phase (Process 1: Invoice Exception Triage)

Foundation layer only: DB schema, migrations, seed data. No API
routes, auth endpoints, or frontend yet — that's the next phase.

## Stack
FastAPI · SQLAlchemy 2.0 · Alembic · SQLite (dev) · Claude API (tool-use mode) · JWT

## Setup

```bash
cd backend
python -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp ../.env.example .env                             # then fill in ANTHROPIC_API_KEY
alembic upgrade head                                # creates financeos.db, all 4 tables
python -m app.seed.seed_data                        # loads Appendix A1/A2 + 2 demo users
```

## Verify

```bash
sqlite3 financeos.db "select count(*) from purchase_orders;"   # expect 10
sqlite3 financeos.db "select count(*) from invoices;"           # expect 15
sqlite3 financeos.db "select invoice_number, po_number from invoices where po_number is null;"
# expect INV-004 and INV-014
sqlite3 financeos.db "select invoice_number from invoices where po_number = 'PO-2024-999';"
# expect INV-009 — confirms the "PO doesn't exist" exception case loaded correctly
```

## Schema notes
Every deviation from the brief's literal minimum schema (vendor_id →
vendor_name, no FK on invoices.po_number, added fields on
invoices/users) is documented in `../docs/design-decisions-draft.md`
with the reasoning. Nothing was changed silently.

## Not built yet (foundation first, by design)
- FastAPI routes / API layer
- JWT auth endpoints
- Claude tool-use integration for triage recommendations
- React frontend
- Dashboard aggregation queries (exception volume, override rate, resolution time)
