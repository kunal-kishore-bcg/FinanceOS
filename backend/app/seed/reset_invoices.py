"""
Resets invoice review state back to a clean baseline: the original 15
seed invoices from Appendix A2, with no AI recommendations and no
human decisions. purchase_orders and users are never touched.

Usage:
    cd backend
    python3 -m app.seed.reset_invoices

--------------------------------------------------------------------
DESTRUCTIVE — read this before pointing it at anything but a local
dev database
--------------------------------------------------------------------
This clears the ENTIRE invoices table and the ENTIRE audit_log table —
not just the 15 original seed rows. Any invoice submitted manually
through the app (e.g. a 16th test invoice from the frontend's "Submit
an invoice" form) is deleted too, and is NOT recreated — only the
original 15 from app/seed/data/invoices.json come back.

There is deliberately no confirmation prompt: this is meant for fast,
repeatable resets between demo runs, and an interactive prompt would
defeat that. There's nothing standing between running this and losing
anything beyond the 15 seed rows, so don't point it at a database you'd
mind losing data from.

audit_log is cleared in full, not filtered to entity_type="invoice".
Today those are equivalent — nothing else writes to audit_log yet. If
that ever changes, this needs a .filter(AuditLog.entity_type ==
"invoice") added, or it'll start wiping unrelated audit history too.
--------------------------------------------------------------------

SAFE TO RUN MULTIPLE TIMES: yes. Unlike seed_data.py (which checks
"already seeded?" and skips), this script doesn't branch on current
state at all — it unconditionally deletes, then unconditionally
inserts the same 15 fixed rows. Run once or run fifty times in a row
and you get the exact same end state: 15 invoices, zero audit_log
rows, nothing else changed. There's no "already reset" branch that
could get out of sync with what's actually in the database.

Atomicity: the delete of both tables and the re-insert of the 15
invoices happen in one SQLAlchemy transaction (see seed_invoices()'s
internal commit() in seed_data.py — nothing here commits before it, so
that one commit call covers everything). If anything fails partway
through, the whole thing rolls back and the database is left exactly
as it was before the script ran — never a state with both tables
emptied and nothing re-seeded yet.

SQLite ID note: invoice and audit_log primary keys restart from 1
after a full delete (this project doesn't use SQLite's AUTOINCREMENT
keyword, which is the only thing that would prevent ID reuse).
Expected, not a bug — but if anything outside the database (a
bookmarked URL, a screenshot) refers to invoice ID 18, that ID may
point at a different invoice after a reset.
"""
from app.database import SessionLocal
from app.models import Invoice, AuditLog
from app.seed.seed_data import seed_invoices


def reset_invoices() -> None:
    db = SessionLocal()
    try:
        # Both deletes are visible within this session immediately,
        # even before commit — so seed_invoices()'s own
        # "count() > 0 → skip" guard correctly sees 0 and proceeds to
        # insert, rather than skipping. Its internal db.commit() is
        # therefore the single commit for this entire operation.
        deleted_audit = db.query(AuditLog).delete()
        deleted_invoices = db.query(Invoice).delete()

        restored = seed_invoices(db)

        print(
            f"Reset complete: deleted {deleted_invoices} invoice(s) and "
            f"{deleted_audit} audit_log entr{'y' if deleted_audit == 1 else 'ies'}; "
            f"restored {restored} original seed invoices with no AI "
            f"recommendations or human decisions."
        )
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    reset_invoices()
