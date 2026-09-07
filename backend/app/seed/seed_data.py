"""
Seed script for FinanceOS Phase 1 (Invoice Exception Triage).

Loads Appendix A1 (purchase order register) and Appendix A2 (invoice
batch) from app/seed/data/*.json, plus two dev-only demo users for the
login flow that will be built in a later phase.

Assumes migrations have already been applied. This script does NOT
call Base.metadata.create_all() — schema state should only ever come
from Alembic (brief 6.4: "DB migrations must be repeatable").

Usage:
    cd backend
    python -m app.seed.seed_data
"""
import json
from pathlib import Path

from passlib.context import CryptContext

from app.database import SessionLocal
from app.models import User, PurchaseOrder, Invoice

DATA_DIR = Path(__file__).parent / "data"
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Dev-only credentials — production-grade auth is explicitly out of
# scope for this assessment (brief section 6.5).
DEMO_USERS = [
    {"email": "analyst@financeos.demo", "password": "password123", "role": "analyst"},
    {"email": "manager@financeos.demo", "password": "password123", "role": "manager"},
]


def load_json(filename: str) -> list[dict]:
    with open(DATA_DIR / filename) as f:
        return json.load(f)


def seed_purchase_orders(db) -> int:
    if db.query(PurchaseOrder).count() > 0:
        print("purchase_orders already seeded — skipping")
        return 0
    rows = load_json("purchase_orders.json")
    for row in rows:
        db.add(PurchaseOrder(**row))
    db.commit()
    return len(rows)


def seed_invoices(db) -> int:
    if db.query(Invoice).count() > 0:
        print("invoices already seeded — skipping")
        return 0
    rows = load_json("invoices.json")
    for row in rows:
        db.add(Invoice(**row))
    db.commit()
    return len(rows)


def seed_users(db) -> int:
    if db.query(User).count() > 0:
        print("users already seeded — skipping")
        return 0
    for u in DEMO_USERS:
        db.add(User(
            email=u["email"],
            password_hash=pwd_context.hash(u["password"]),
            role=u["role"],
        ))
    db.commit()
    return len(DEMO_USERS)


def main():
    db = SessionLocal()
    try:
        n_po = seed_purchase_orders(db)
        n_inv = seed_invoices(db)
        n_users = seed_users(db)
        print(f"Seeded: {n_po} purchase orders, {n_inv} invoices, {n_users} users")
        if n_users:
            print(
                "Demo login: analyst@financeos.demo / password123 (analyst), "
                "manager@financeos.demo / password123 (manager)"
            )
    finally:
        db.close()


if __name__ == "__main__":
    main()
