**Key design decisions** made during the build of **FinanceOS Process 1 — Invoice Exception Triage** — with alternatives considered and trade-offs accepted.

**1. Rule engine produces flags only; the LLM owns the recommendation**

The rule engine runs deterministic checks (PO lookup, amount delta, duplicate detection) and outputs flags — it never decides Approve/Escalate/Reject itself. That decision, plus rationale and reviewer_action, comes from Claude, using the flags as structured context.
Alternative considered: pure LLM triage with no pre-processing.
Rejected because: objective facts (does this PO exist, what's the exact delta) are exactly what LLMs hallucinate on. The rule engine makes those checks reliable, freeing the LLM for judgment and business-language output rather than arithmetic.
Trade-off: more upfront engineering than a single LLM call, in exchange for removing the largest hallucination surface in a live demo.

**2. No de-minimis threshold on PO overage**

Any amount exceeding the approved PO triggers Escalate regardless of size — a $650 overage and a $4,000 overage both escalate, differing only in the LLM's rationale, not the tier.
Alternative considered: a materiality floor (e.g. <$5 or <0.1%) to suppress FX/rounding noise.
Rejected for this POC: PO approval exists to control spend at the approved level; a self-approving threshold undermines that control, and the seed data has no rounding-noise cases to justify the added complexity.
Trade-off: a genuine rounding difference escalates identically to a material miss — acceptable here, but production would need a materiality floor.

**3. Schema deviates from spec where the spec conflicts with process scope**

vendor_name replaces vendor_id on invoices/purchase_orders, and invoices.po_number has no foreign key.
Alternative considered: a shared vendors table across all three processes, with referential integrity enforced on PO references.
Rejected because: a vendors table belongs to Process 3's scope, not Process 1's. The seed data deliberately includes invoices with non-existent or missing PO references (INV-004, INV-009, INV-014); an FK constraint would silently reject those rows on seed — deleting the exact exception cases the triage logic exists to catch.
Trade-off: no DB-level referential integrity or name normalization; both are enforced in the application layer, which is also the correct layer for the LLM to reason about near-duplicate vendor names.

**4. No review step between PDF extraction and triage**

Uploaded PDFs are extracted and passed directly into the pipeline — no screen for the user to correct extracted fields before triage.
Alternative considered: an edit/confirm step between extraction and submission.
Rejected because the mitigation is sufficient for this POC: extraction fails loudly on missing or unlabelled fields rather than guessing, and every triaged invoice stays pending until a human confirms — so a bad extraction can never self-approve. The extractor requires explicit field labels ("Invoice Number:", "Vendor:", "Total:") and returns a specific error naming any missing field rather than attempting a best-effort match.
Trade-off: a correctly-formatted PDF with an unusual label (e.g. "Bill To:" instead of "Vendor:") fails extraction entirely rather than partially succeeding — user falls back to manual entry.

**5. Surface every applicable flag, even against a single-answer seed case**

INV-011 triggers both PO_CLOSED and a vendor/PO mismatch, though the brief's answer key documents only one exception.
Alternative considered: suppress the second flag to match the documented expected output.
Rejected because: hiding a genuine flag to match an answer key means concealing information from the reviewer — the opposite of the override-transparency principle the brief requires. Multiple flags feed one LLM recommendation; they don't fragment it.
Trade-off: none — this cost nothing to implement correctly, and surfaced an apparent inconsistency in the seed data itself.
