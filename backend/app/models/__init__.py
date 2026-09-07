"""
Import every model here so Base.metadata is fully populated — required
for Alembic autogenerate to see the whole schema, and for anything
that inspects Base.metadata directly.
"""
from app.models.user import User
from app.models.purchase_order import PurchaseOrder
from app.models.invoice import Invoice
from app.models.audit_log import AuditLog

__all__ = ["User", "PurchaseOrder", "Invoice", "AuditLog"]
