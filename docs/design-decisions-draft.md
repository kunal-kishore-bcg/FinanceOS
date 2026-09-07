# Design Decisions — Draft Notes (Phase 1: Schema & Migrations)

Working notes captured during the foundation build. To be condensed
into the final 300–500 word `docs/design-decisions.md` before
submission — this is not a substitute for it.

## 1. No FK constraint on invoices.po_number
Appendix A2 deliberately includes an invoice referencing a PO number
that doesn't exist (INV-009 → PO-2024-999) and two invoices with no PO
reference at all (INV-004, INV-014). These aren't bad data — they're
the exception scenarios the triage engine is meant to catch. A hard
foreign key would reject those rows on insert, silently removing the
two hardest test cases from the seed set. Referential validity is
enforced as a business rule in the matching/triage logic (Phase 2),
not as a database constraint.

## 2. vendor_id → vendor_name (purchase_orders, invoices)
The brief's schema table (section 3.3) ties a dedicated `vendors`
table to Process 3 (Vendor Risk & Onboarding Screener) only. Process 1
seed data provides vendor names, not vendor IDs, and Process 1 has no
requirement to dedupe or risk-score vendors. Adding a vendors table
here would be the scope creep section 6.5 explicitly warns against.
Vendor is stored as a plain string on both tables.

## 3. Added reviewed_by / reviewed_at to invoices
Section 6.2 is explicit that override rate can't be measured or
improved on without knowing who overrode a decision. human_override
alone captures the decision, not the reviewer or when it happened.
Both fields are nullable and unused by anything yet — added now so a
schema migration isn't needed later purely to support a rubric
requirement that's already known.

## 4. Added password_hash to users
Not in the brief's minimum field list, but "basic user login" (section
3.1) isn't achievable without a stored credential. Treated as a
required addition, not an extra.

## 5. "NONE" / blank PO Ref normalized to NULL
Appendix A2 uses the literal text "NONE" for INV-004 and a blank cell
for INV-014. Both mean "no PO reference" — both are stored as NULL
rather than preserving "NONE" as a string, so downstream logic
checking for a missing PO only has one case to handle, not two.

## 6. Expected-outcomes reference kept out of the invoices table
Appendix A2's "Exception Flag" / "Expected AI Output" columns are a
test oracle, not invoice data. They're kept in
`app/seed/data/expected_outcomes_reference.json` for validating the
triage engine in Phase 2, not loaded into `invoices` — a real invoice
record shouldn't ship with the answer key baked in.

## Open — to revisit before Phase 2
- Whether ai_recommendation / human_override should be constrained to
  an enum (approve/escalate/reject) rather than a free string —
  deferred until the triage logic's exact output contract is locked
  in with the Claude tool-use schema.
- cost_centre and status are free-text for now. Worth a lookup table
  if this ever needs to share cost centres with Process 2 (budget
  variance) — out of scope for a Process 1 build, but worth a
  sentence in Q&A if asked about extensibility.
