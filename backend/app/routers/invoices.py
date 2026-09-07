"""
Invoice API routes: submission (rule engine + Claude triage), listing,
and the human decision endpoint (confirm or override).

Status model (revised per explicit instruction — this supersedes the
Phase-2-original version, which set status to the AI's recommendation
immediately):

  - After POST /, status is ALWAYS "pending_review", regardless of
    what the AI recommended. ai_recommendation and ai_rationale are
    stored and returned, but status does not move on AI output alone.
  - status only changes via PATCH /{id}/decision, i.e. only when a
    human has explicitly acted — either confirming the AI's
    recommendation or overriding it with something else.

This is the stricter reading of brief 6.2 ("never auto-approve based
solely on AI output... All AI outputs must be reviewable and
overridable by a human") flagged as an open question in the Phase 2
notes; this update resolves it in favor of the stricter reading.

Consequence worth noting: since status no longer mirrors
ai_recommendation automatically, "override rate" (brief 6.2: "if you
cannot measure override rate, you cannot improve the model") now needs
the human's decision to be classified against what the AI said, not
just recorded. See _classify_decision() below — this is a necessary
follow-on from this change, not a separate feature request.
"""
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import Invoice, PurchaseOrder, AuditLog, User
from app.rule_engine import evaluate_invoice, find_matching_po, build_known_vendors
from app.claude_client import get_triage_recommendation

router = APIRouter(prefix="/invoices", tags=["invoices"])


class InvoiceCreate(BaseModel):
    invoice_number: str
    vendor_name: str
    po_number: Optional[str] = None
    amount: float


class DecisionRequest(BaseModel):
    decision: str = Field(pattern="^(approve|escalate|reject)$")
    reason: str


def _po_to_dict(po: PurchaseOrder) -> dict:
    """Explicit conversion, not `.__dict__` — avoids leaking SQLAlchemy
    instance state into the rule engine's plain-dict interface, and
    converts Numeric/Decimal to float at the ORM boundary."""
    return {
        "po_number": po.po_number,
        "vendor_name": po.vendor_name,
        "approved_amount": float(po.approved_amount),
        "cost_centre": po.cost_centre,
        "status": po.status,
    }


def _invoice_to_dict(inv: Invoice) -> dict:
    return {
        "invoice_number": inv.invoice_number,
        "vendor_name": inv.vendor_name,
        "po_number": inv.po_number,
        "amount": float(inv.amount),
    }


def _write_audit(db: Session, user_id: Optional[int], entity_id: int, action: str, old_value, new_value):
    db.add(AuditLog(
        user_id=user_id,
        entity_type="invoice",
        entity_id=entity_id,
        action=action,
        old_value=old_value,
        new_value=new_value,
    ))


def _classify_decision(ai_recommendation: Optional[str], human_decision: str) -> str:
    """
    Distinguishes three cases for the audit log, needed to measure
    override rate now that status doesn't auto-adopt ai_recommendation:

      - "human_confirmed" — human's decision matches what the AI said.
      - "human_override"  — AI made a recommendation and the human
        chose something different.
      - "human_decision"  — there was no AI recommendation to agree
        or disagree with (e.g. the AI call failed), so this is a
        fresh human call, not an override of anything.
    """
    if ai_recommendation is None:
        return "human_decision"
    if human_decision == ai_recommendation:
        return "human_confirmed"
    return "human_override"


@router.post("/", status_code=status.HTTP_201_CREATED)
def create_invoice(
    payload: InvoiceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if db.query(Invoice).filter(Invoice.invoice_number == payload.invoice_number).first():
        raise HTTPException(status_code=409, detail=f"Invoice {payload.invoice_number} already exists")

    all_pos = [_po_to_dict(po) for po in db.query(PurchaseOrder).all()]
    all_invoices = [_invoice_to_dict(inv) for inv in db.query(Invoice).all()]  # existing invoices only
    known_vendors = build_known_vendors(all_pos)
    matched_po = find_matching_po(payload.po_number, all_pos)

    invoice = Invoice(
        invoice_number=payload.invoice_number,
        vendor_name=payload.vendor_name,
        po_number=payload.po_number,
        amount=payload.amount,
        status="pending_review",
    )
    db.add(invoice)
    db.flush()  # assigns invoice.id without committing, so audit_log can reference it in the same transaction

    flags = evaluate_invoice(
        invoice=_invoice_to_dict(invoice),
        matched_po=matched_po,
        all_invoices=all_invoices,
        known_vendors=known_vendors,
    )

    ai_result = get_triage_recommendation(
        invoice_number=invoice.invoice_number,
        vendor_name=invoice.vendor_name,
        amount=float(invoice.amount),
        flags=flags,
    )

    invoice.ai_recommendation = ai_result.get("recommendation")
    invoice.ai_rationale = ai_result.get("rationale") or ai_result.get("error")
    # status is deliberately NOT touched here — it stays "pending_review"
    # regardless of what the AI recommended, or whether the AI call
    # succeeded at all. It only ever changes via PATCH /{id}/decision.

    # Keyed as rule_engine_flags, not flags — ai_result now has its own
    # "flags" key (claude_client.py's tool schema), and {"flags": flags,
    # **ai_result} would have let ai_result's value silently overwrite
    # the rule engine's on key collision. Keeping both distinct on purpose:
    # rule_engine_flags is what the deterministic checks found; ai_result's
    # flags (if the finalized schema keeps that field) is whatever the
    # LLM says it based its call on — worth being able to compare, not merge.
    _write_audit(
        db, user_id=None, entity_id=invoice.id, action="ai_recommendation",
        old_value=None, new_value={"rule_engine_flags": flags, **ai_result},
    )

    db.commit()
    db.refresh(invoice)

    return {
        "id": invoice.id,
        "invoice_number": invoice.invoice_number,
        "flags": flags,
        "ai_recommendation": invoice.ai_recommendation,
        "ai_rationale": invoice.ai_rationale,
        "status": invoice.status,
    }


@router.get("/")
def list_invoices(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    invoices = db.query(Invoice).order_by(Invoice.created_at.desc()).all()
    return [
        {
            "id": inv.id,
            "invoice_number": inv.invoice_number,
            "vendor_name": inv.vendor_name,
            "po_number": inv.po_number,
            "amount": float(inv.amount),
            "status": inv.status,
            "ai_recommendation": inv.ai_recommendation,
            "ai_rationale": inv.ai_rationale,
            "human_override": inv.human_override,
            "reviewed_by": inv.reviewed_by,
            "reviewed_at": inv.reviewed_at,
        }
        for inv in invoices
    ]


@router.patch("/{invoice_id}/decision")
def decide_invoice(
    invoice_id: int,
    payload: DecisionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    The only way an invoice's status changes. Covers both cases the
    brief and your instruction call for: a human confirming the AI's
    recommendation, and a human overriding it — same endpoint, decision
    classified against ai_recommendation to keep the audit trail (and
    therefore the override-rate metric) accurate. See
    _classify_decision().

    human_override column semantics preserved from the model docstring
    ("null if AI decision stands"): stays NULL on confirm, is set to
    the decision on override or on a fresh human_decision.
    """
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if invoice is None:
        raise HTTPException(status_code=404, detail="Invoice not found")

    action = _classify_decision(invoice.ai_recommendation, payload.decision)
    old_value = {"status": invoice.status, "human_override": invoice.human_override}

    invoice.status = payload.decision
    invoice.human_override = None if action == "human_confirmed" else payload.decision
    invoice.reviewed_by = current_user.id
    invoice.reviewed_at = datetime.now(timezone.utc)

    _write_audit(
        db, user_id=current_user.id, entity_id=invoice.id, action=action,
        old_value=old_value, new_value={"decision": payload.decision, "reason": payload.reason},
    )

    db.commit()
    db.refresh(invoice)

    return {
        "id": invoice.id,
        "invoice_number": invoice.invoice_number,
        "status": invoice.status,
        "human_override": invoice.human_override,
        "reviewed_by": invoice.reviewed_by,
        "reviewed_at": invoice.reviewed_at,
        "action": action,
    }
