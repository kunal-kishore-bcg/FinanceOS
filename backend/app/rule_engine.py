"""
Deterministic invoice exception rule engine.

Pure functions on plain dicts — no DB session, no HTTP, no LLM call.
This is intentional: it's the one piece of triage logic that must be
100% reproducible and independently testable (see the self-test at the
bottom, run with `python -m app.rule_engine`).

Returns flags ONLY — plain-English strings describing what a human
Finance reviewer (or the LLM standing in as first-pass reviewer) needs
to know. It never returns approve/escalate/reject. Brief 6.2: "Show
confidence or rationale alongside every AI recommendation" and the
recommendation itself is explicitly the LLM's job, not this module's.

--------------------------------------------------------------------
SIGNATURE NOTE — read before changing this file
--------------------------------------------------------------------
The brief says: "Accept an invoice dict and a matched PO dict (or None
if PO not found)." evaluate_invoice() does exactly that as its two
required positional args. Two of the seven required checks cannot be
implemented correctly from those two args alone, so two optional
keyword args were added:

  - `all_invoices`: needed for duplicate detection (checking one
    invoice against a matched PO tells you nothing about whether
    another invoice already claimed the same PO+vendor+amount).

  - `known_vendors`: needed to distinguish INV-004 ("Unknown Vendor
    XYZ", no PO, vendor doesn't exist anywhere in the register) from
    INV-014 (DataBridge Analytics, no PO, but a perfectly legitimate,
    recognised vendor). Appendix A2 expects different severities
    (Reject vs Escalate) for these two "missing PO" cases, and vendor
    recognition is the only signal that tells them apart. Without
    known_vendors, both cases collapse to the same single flag and
    the LLM has nothing to discriminate on.

Both default to None and the checks that need them are skipped if
they're not supplied, so the literal 2-arg call still works — it just
does less. The real call site (routers/invoices.py) always supplies
both.
--------------------------------------------------------------------
"""
from __future__ import annotations


def build_known_vendors(purchase_orders: list[dict]) -> set[str]:
    """Vendor universe, derived from the PO register. Process 1 has no
    vendors table (see docs/design-decisions-draft.md, decision 2) —
    this is the only source of 'is this vendor recognised at all'."""
    return {po["vendor_name"].strip() for po in purchase_orders}


def find_matching_po(po_number: str | None, purchase_orders: list[dict]) -> dict | None:
    """Exact-match lookup by po_number. Returns None for both 'no
    po_number given' and 'po_number given but not in the register' —
    evaluate_invoice() tells those two apart using the raw invoice
    dict's po_number field, not this return value alone."""
    if not po_number:
        return None
    po_number = po_number.strip()
    for po in purchase_orders:
        if po["po_number"] == po_number:
            return po
    return None


def evaluate_invoice(
    invoice: dict,
    matched_po: dict | None,
    *,
    all_invoices: list[dict] | None = None,
    known_vendors: set[str] | None = None,
) -> list[str]:
    """
    Run all seven checks in the specified order and return the flags
    that fired. Order matters for two reasons: (1) it's the order the
    brief specified, and (2) check 7 (partial invoice) explicitly only
    fires if nothing else has already flagged this invoice.
    """
    flags: list[str] = []

    po_number = (invoice.get("po_number") or "").strip() or None
    invoice_vendor = invoice["vendor_name"].strip()
    amount = float(invoice["amount"])

    # 1. PO not found — a po_number was given but it doesn't match any
    #    PO in the register. (A missing po_number entirely is check 6,
    #    not this one.)
    if po_number and matched_po is None:
        flags.append(f"No matching PO found for reference {po_number}")

    # 2. Vendor name mismatch
    if matched_po is not None:
        po_vendor = matched_po["vendor_name"].strip()
        if invoice_vendor.lower() != po_vendor.lower():
            flags.append(
                f"Vendor name mismatch: invoice vendor '{invoice_vendor}' "
                f"does not match PO vendor '{po_vendor}'"
            )
    elif known_vendors is not None and invoice_vendor not in known_vendors:
        # No PO to compare against (missing or not found) — fall back
        # to checking whether this vendor is recognised at all.
        flags.append(f"Vendor '{invoice_vendor}' is not a recognised vendor in the PO register")

    # 3. PO status closed
    if matched_po is not None and matched_po["status"] == "Closed":
        flags.append("PO status is Closed")

    # 4. Duplicate invoice detection — only flag the later of a pair,
    #    so the original invoice doesn't also get flagged against itself.
    #    Relies on invoice_number sort order matching submission order,
    #    which holds for zero-padded fixed-width IDs (INV-001 style);
    #    would need created_at instead if IDs ever become variable-width.
    if all_invoices is not None and po_number is not None:
        earlier_duplicates = [
            i for i in all_invoices
            if i["invoice_number"] != invoice["invoice_number"]
            and (i.get("po_number") or "").strip() == po_number
            and i["vendor_name"].strip().lower() == invoice_vendor.lower()
            and float(i["amount"]) == amount
            and i["invoice_number"] < invoice["invoice_number"]
        ]
        if earlier_duplicates:
            flags.append(
                f"Duplicate of {earlier_duplicates[0]['invoice_number']} — same vendor, PO, and amount"
            )

    # 5. Amount exceeds PO
    if matched_po is not None and amount > float(matched_po["approved_amount"]):
        over = amount - float(matched_po["approved_amount"])
        flags.append(f"Invoice amount exceeds approved PO by ${over:,.0f}")

    # 6. Missing PO reference field
    if po_number is None:
        flags.append("Missing PO reference field")

    # 7. Partial invoice — under PO amount, only if nothing else fired
    if matched_po is not None and amount < float(matched_po["approved_amount"]) and not flags:
        flags.append(
            f"Invoice amount (${amount:,.0f}) is under the approved PO amount "
            f"(${float(matched_po['approved_amount']):,.0f}) — partial invoice"
        )

    return flags


if __name__ == "__main__":
    # Self-test against Appendix A2. Pure stdlib — runs with no
    # dependencies installed, which is also why this module is written
    # to not import SQLAlchemy/FastAPI/anthropic at all.
    import json
    from pathlib import Path

    DATA_DIR = Path(__file__).parent / "seed" / "data"

    with open(DATA_DIR / "purchase_orders.json") as f:
        purchase_orders = json.load(f)
    with open(DATA_DIR / "invoices.json") as f:
        invoices = json.load(f)
    with open(DATA_DIR / "expected_outcomes_reference.json") as f:
        expected = {c["invoice_number"]: c for c in json.load(f)["cases"]}

    known_vendors = build_known_vendors(purchase_orders)

    print(f"{'Invoice':<10} {'Flags produced':<95} {'Expected (appendix)':<20} {'Check'}")
    print("-" * 145)

    failures = []
    for inv in invoices:
        matched_po = find_matching_po(inv["po_number"], purchase_orders)
        flags = evaluate_invoice(inv, matched_po, all_invoices=invoices, known_vendors=known_vendors)

        exp = expected[inv["invoice_number"]]
        expects_exception = exp["exception_flag"] != "None"
        has_exception = len(flags) > 0

        ok = expects_exception == has_exception
        if not ok:
            failures.append(inv["invoice_number"])

        flags_str = "; ".join(flags) if flags else "(none)"
        print(f"{inv['invoice_number']:<10} {flags_str:<95} {exp['expected_output']:<20} {'PASS' if ok else 'FAIL'}")

    print("-" * 145)
    if failures:
        print(f"FAILED: {failures}")
        raise SystemExit(1)
    print(f"All {len(invoices)} cases: exception/no-exception matches Appendix A2 expected output.")
