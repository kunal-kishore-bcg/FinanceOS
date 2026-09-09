from sqlalchemy import Column, Integer, String, Numeric, Text, DateTime, ForeignKey, func

from app.database import Base


class Invoice(Base):
    """
    Brief minimum schema (section 3.3): id, vendor_id, po_number,
    amount, status, ai_recommendation, ai_rationale, human_override,
    created_at.

    Deviations, all documented in docs/design-decisions-draft.md:

    1. vendor_id -> vendor_name — same rationale as PurchaseOrder.

    2. po_number is a plain indexed String, NOT a ForeignKey to
       purchase_orders.po_number. Appendix A2 deliberately includes an
       invoice referencing a PO that doesn't exist (INV-009 ->
       PO-2024-999) and invoices with no PO reference at all (INV-004,
       INV-014). Detecting "PO number does not exist" and "missing PO
       reference" is exactly the exception logic this process tests.
       A hard FK would reject those rows on insert, deleting the two
       hardest test cases from the seed set. Referential validity is a
       business rule enforced in the matching/triage logic (Phase 2),
       not a database constraint.

    3. invoice_number added — a human-readable business key (INV-001,
       etc.), distinct from the internal autoincrement id. The seed
       data and the brief's own UI language (section 6.1) both operate
       on this identifier, not a raw DB id.

    4. reviewed_by / reviewed_at added. human_override alone records
       WHAT a human decided, not WHO or WHEN. Section 6.2 is explicit
       that override rate has to be measurable to be improved on —
       that requires a reviewer reference.

    5. confidence added (migration 0002). Claude's tool schema
       (claude_client.py) has returned a confidence value since the
       schema was expanded to 5 fields, but until this column existed
       it was computed and then discarded — never persisted, never
       returned by GET /invoices/. Nullable string ("high"/"medium"/
       "low"), same provisional-until-the-real-prompt-confirms-it
       status as the rest of that schema — see claude_client.py's
       docstring.
    """
    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True, autoincrement=True)
    invoice_number = Column(String, unique=True, nullable=False, index=True)
    vendor_name = Column(String, nullable=False)
    po_number = Column(String, nullable=True, index=True)  # intentionally not a ForeignKey — see docstring
    amount = Column(Numeric(12, 2), nullable=False)
    status = Column(String, nullable=False, default="pending_review")  # pending_review | approved | escalated | rejected
    ai_recommendation = Column(String, nullable=True)  # approve | escalate | reject
    ai_rationale = Column(Text, nullable=True)
    confidence = Column(String, nullable=True)  # high | medium | low — see docstring point 5
    human_override = Column(String, nullable=True)  # approve | escalate | reject; null if AI decision stands
    reviewed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
