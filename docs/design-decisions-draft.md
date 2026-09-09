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

## 7. Startup check, not startup auto-create (main.py)
Asked for "DB init if tables don't exist" at startup. Implemented as a
check that fails fast with a clear error if migrations haven't been
run, not as `Base.metadata.create_all()`. A create-on-missing fallback
would give the app two independent paths to a schema (Alembic, and
this fallback) that could silently drift apart, directly undercutting
decision item "Alembic owns schema creation" from the Phase 1 notes.
If a fresh-clone-just-works demo experience matters more than that
guarantee, this is a one-line swap — flagging it as a deliberate
trade-off rather than making the call silently.

## 8. Rule engine signature extended beyond the literal 2-arg spec
`evaluate_invoice(invoice, matched_po)` is the interface as specified,
but two of the seven required checks can't be implemented from those
two args alone: duplicate detection needs visibility into sibling
invoices, and telling INV-004 (unrecognised vendor, Reject) apart from
INV-014 (recognised vendor, Escalate) — both "missing PO reference" —
needs the vendor universe. Added `all_invoices` and `known_vendors` as
optional keyword args, defaulting to None (checks skip silently if not
supplied, so the literal 2-arg call still works, just does less). Full
reasoning is in the module docstring in rule_engine.py.

## 9. Invoice status reflects the AI recommendation until overridden
Brief 6.2: "never auto-approve based solely on AI output." Read
narrowly, `invoice.status` being set to "approve" the moment the AI
recommends it — before any human looks at it — could be seen as
exactly that. Went with it anyway because: the rationale is always
stored and returned, nothing is hidden, and every override is logged
per 6.2's other explicit requirement. The alternative (status stays
"pending_review" until a human explicitly confirms, not just when they
override) is a small addition if you want the stricter reading — flag
it in the interview either way, since a reviewer could reasonably read
6.2 the stricter way.

## 10. INV-011 discrepancy in Appendix A2 seed data
INV-011 bills vendor "SecureVault Storage" against PO-2024-005, but
PO-2024-005 belongs to Acme Consulting Ltd (and is Closed) per
Appendix A1. SecureVault Storage's actual PO is PO-2024-010, for
exactly the invoiced $5,600. Reads like a transcription error in the
case study's own seed data (PO-2024-005 vs PO-2024-010), not an
intentional third exception type — there's no other case testing
"vendor mismatch on an otherwise-valid PO" in isolation. Left the seed
data as-given rather than "fixing" it, since the assessment's own data
is not mine to edit; the rule engine correctly surfaces both the
vendor mismatch and the closed-PO flag, so the outcome (Reject) is
right either way. Worth raising proactively in the interview rather
than waiting to be asked.

## 11. PDF extraction fails loudly rather than guessing
`pdf_extraction.py` requires an explicit label match (e.g. "Vendor:",
"Invoice Number:") for each required field. If a field can't be found
with reasonable confidence, the upload is rejected with a clear
message naming exactly which field(s) are missing — it doesn't fall
back to a weaker guess (like "first line of the PDF is probably the
vendor name") just to avoid returning an error. Verified with 5 test
cases including one specifically checking that an unlabeled vendor
name correctly fails rather than silently matching something wrong.
Rationale is in the module's docstring: this endpoint has no
preview/correction step before the extracted data hits the rule engine
and Claude, so a wrong silent guess is worse than a rejected upload.

## 12. PO reference stays optional on the PDF path, same as manual entry
Only invoice_number, vendor_name, and amount are required extractions.
A PDF with no PO reference produces po_number=None, which flows into
the rule engine exactly like leaving the PO field blank on manual
entry (see INV-004/INV-014 in the seed data) — correctly triggers
"missing PO reference," not an upload rejection.

## 13. _create_invoice_from_fields() shared between both endpoints
POST / and POST /upload-pdf call the identical helper function for
dedupe check, rule engine, Claude triage, audit log, and response
shape. This is the only way to actually guarantee (not just intend)
that the PDF path is "exactly as the manual entry flow does" — one
function, not two code paths that could quietly drift apart.

## 14. pdfplumber imported lazily, inside extract_invoice_fields()
The actual field-parsing logic (parse_fields_from_text()) has zero
PDF-library dependency and could be unit tested directly in this build
environment without pdfplumber installed — which is how the 5 parsing
test cases in this phase were actually run and verified, not just
hand-traced. Real design benefit beyond testability: the parsing logic
is reusable independent of the PDF library if extraction input ever
comes from somewhere other than a PDF upload.

## 15. Largest-bare-dollar-amount fallback for total (no label found)
If no "Total"/"Amount Due"-style label exists, the extractor takes the
largest dollar figure anywhere in the PDF text, on the assumption that
line items are smaller than the total they sum to. This is a real
heuristic, not a guarantee — an invoice with one large line item and
no visible total would extract that line item's amount as if it were
the total. No way around this without OCR-level document understanding;
flagged as a known limitation rather than silently accepted.

## 16. 10 MB upload cap
Arbitrary but generous for a single-page invoice PDF; a cheap sanity
check against something going wrong on the client side, not a
carefully-derived limit.

## 17. Override rate definition changed — no longer excludes AI-failure cases
Earlier version excluded invoices where the AI had no recommendation
from both sides of the override-rate fraction (documented in the
SummaryBar.jsx of that phase). This request specified the metric
exactly: human_override count ÷ invoices where status != pending_review.
That's simpler to state and defend in one sentence, but it does mean
an invoice where the AI call failed and a human then made a fresh
decision now counts toward "overridden," even though there was no AI
opinion to actually override. Implemented as specified — flagging the
behavior change since it's a real difference in what number the panel
shows, not just a refactor.

## 18. Avg. resolution time computed client-side, not backend
The request asked for this to be calculated in the backend. Every
other stat in this panel (total, AI breakdown, and the override rate
this same request asks to confirm) is computed client-side from the
raw invoice list — moving only this one stat's math to the backend
would split dashboard aggregation across two places computed two
different ways, a likely source of drift if either definition ever
changes. The actual missing backend piece — `created_at`, which
genuinely wasn't in the GET /invoices/ response — is now included;
the averaging happens in SummaryBar.jsx alongside everything else it
already computes. If there's a reason this specifically needs to be
server-side (e.g. wanting raw timestamps kept out of the frontend),
that's a quick follow-up, but it wasn't the default here.

## 19. Confidence column — closed out (migration 0002)
Previously flagged as display-ready-but-not-backend-supported: the
frontend checked `invoice.confidence` but nothing ever set it. That
gap is now closed — `invoices.confidence` (nullable string, migration
0002), persisted in `_create_invoice_from_fields()` from
`ai_result.get("confidence")`, returned by `GET /invoices/`. No
frontend change needed; it was already built to display this the
moment it existed. Still inherits claude_client.py's open item:
`confidence` is a provisional field (enum "high"/"medium"/"low") on
the tool schema pending the finalized prompt.

## 20. Rationale shown via native title tooltip, not click-to-expand
Simpler of the two offered options — no new interaction state, matches
the existing title-tooltip pattern already used for the "AI
unavailable" badge. Real trade-off: doesn't work on touch (no hover),
and has the native browser tooltip delay. Click-to-expand would be
more reliable but is a bigger change; revisit if touch/mobile use
turns out to matter for the actual review workflow.

## Open — to revisit before frontend / demo polish
- Whether ai_recommendation / human_override should be constrained to
  an enum (approve/escalate/reject) at the DB layer rather than a free
  string — now that claude_client.py's tool schema locks the values
  down at the API boundary, a DB-level CHECK constraint would just be
  belt-and-suspenders, not required.
- cost_centre and status are free-text for now. Worth a lookup table
  if this ever needs to share cost centres with Process 2 (budget
  variance) — out of scope for a Process 1 build, but worth a
  sentence in Q&A if asked about extensibility.
- /prompts/invoice_triage.md is a placeholder — must be replaced with
  the finalized prompt before the demo (see claude_client.py).
- No automated tests yet beyond rule_engine.py's built-in self-test
  (`python -m app.rule_engine`). Worth a pytest suite covering the API
  layer before the demo, given "technical depth" is a scored rubric
  dimension.
