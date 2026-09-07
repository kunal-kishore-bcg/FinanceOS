from sqlalchemy import Column, Integer, String, Numeric, DateTime, func

from app.database import Base


class PurchaseOrder(Base):
    """
    Brief minimum schema (section 3.3): id, po_number, vendor_id,
    approved_amount, cost_centre, status.

    vendor_id -> vendor_name: the brief ties a dedicated `vendors`
    table to Process 3 (Vendor Risk & Onboarding Screener) only.
    Appendix A1 gives vendor names, not vendor IDs, and Process 1 has
    no requirement to dedupe or risk-score vendors. Adding a vendors
    table here would be the scope creep section 6.5 explicitly warns
    against. See docs/design-decisions-draft.md.
    """
    __tablename__ = "purchase_orders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    po_number = Column(String, unique=True, nullable=False, index=True)
    vendor_name = Column(String, nullable=False)
    approved_amount = Column(Numeric(12, 2), nullable=False)
    cost_centre = Column(String, nullable=False)
    status = Column(String, nullable=False, default="Open")  # Open | Closed
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
