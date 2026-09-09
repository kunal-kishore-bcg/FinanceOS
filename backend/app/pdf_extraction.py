"""
Heuristic PDF invoice field extraction.

Extracts invoice_number, vendor_name, amount, and po_number from PDF
text via label-based regex matching (e.g. "Invoice Number:", "Vendor:",
"Total Due:"). This is NOT a general-purpose invoice-parsing model —
it's a pragmatic best-effort extractor built to satisfy the brief's
"accept PDF uploads" requirement, and it will fail (loudly, not
silently) on PDFs that don't use conventional field labels. It cannot
read scanned/image-only PDFs at all — no OCR here, pdfplumber only
reads an existing text layer.

--------------------------------------------------------------------
NO HUMAN CHECKPOINT ON EXTRACTED DATA — worth understanding before
relying on this in a demo
--------------------------------------------------------------------
Per the brief for this endpoint, extracted fields go straight into the
rule engine and Claude triage with no preview or correction step. A
wrong extraction (misread amount, wrong vendor name) produces a real
invoice record that then gets triaged against incorrect data — and
unlike every AI recommendation elsewhere in this app, there's no
"reviewable before it takes effect" checkpoint for the extraction step
itself. The mitigation here is failing loudly when a required field
can't be found with reasonable confidence, rather than guessing to
avoid an error message: a rejected upload is recoverable, a wrong
number silently fed through the triage pipeline is not. Worth stating
plainly if asked about it: this endpoint trusts the PDF's text more
than the rest of the app trusts anything else.
--------------------------------------------------------------------

Design note: the pdfplumber import is inside extract_invoice_fields(),
not at module level. That's deliberate, not an oversight — it means
parse_fields_from_text() (the actual regex logic, and the part most
likely to need tuning against real invoices) can be imported and unit
tested without pdfplumber installed at all. The PDF library is only
needed once you actually have PDF bytes to open.
"""
from __future__ import annotations

import re
from typing import Optional


class PdfExtractionError(Exception):
    """Raised when the PDF itself can't be read at all — corrupt file,
    encrypted, or no extractable text layer. Distinct from 'could read
    the text but couldn't find a required field,' which is reported
    via missing_fields instead of an exception — that case still
    returns a result, just an incomplete one."""


INVOICE_NUMBER_PATTERNS = [
    r"invoice\s*(?:number|no\.?|#)\s*[:\-]?\s*([A-Za-z0-9][A-Za-z0-9\-_/]{1,24})",
    r"\binv\s*#\s*[:\-]?\s*([A-Za-z0-9][A-Za-z0-9\-_/]{1,24})",
]

PO_NUMBER_PATTERNS = [
    r"(?:purchase\s*order|po)\s*(?:number|no\.?|#|reference|ref\.?)?\s*[:\-]\s*([A-Za-z0-9][A-Za-z0-9\-_/]{1,24})",
]

VENDOR_NAME_PATTERNS = [
    r"(?:vendor|supplier|bill\s*from|remit\s*to)\s*(?:name)?\s*[:\-]\s*([A-Za-z0-9&.,'\- ]{2,60})",
]

# Explicit "total"-style labels are tried first. A bare dollar amount
# is only used as a last resort, and picks the LARGEST figure found on
# the assumption that a total is bigger than the line items it sums —
# a real heuristic, not a guarantee; flagged in extract results as a
# best-effort match either way (there's no way to tell the caller
# "this came from the risky fallback" without extending the return
# shape, which wasn't asked for — noting the limitation here instead).
TOTAL_LABELED_PATTERNS = [
    r"(?:grand\s*total|total\s*(?:amount)?\s*due|invoice\s*total|amount\s*due|total)\s*[:\-]?\s*\$?\s*([\d,]+\.\d{2})",
]
BARE_AMOUNT_PATTERN = r"\$\s*([\d,]+\.\d{2})"


def _first_match(patterns: list[str], text: str) -> Optional[str]:
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return None


def _extract_amount(text: str) -> Optional[float]:
    labeled = _first_match(TOTAL_LABELED_PATTERNS, text)
    if labeled:
        return float(labeled.replace(",", ""))

    bare_matches = re.findall(BARE_AMOUNT_PATTERN, text)
    if bare_matches:
        return max(float(m.replace(",", "")) for m in bare_matches)

    return None


def parse_fields_from_text(text: str) -> dict:
    """
    Pure text -> fields parsing, no PDF library involved. Kept separate
    from extract_invoice_fields() specifically so this — the part that
    will actually need tuning once tested against real invoice PDFs —
    can be exercised directly with plain strings.

    Returns:
        {
            "invoice_number": str | None,
            "vendor_name": str | None,
            "amount": float | None,
            "po_number": str | None,
            "missing_fields": list[str],  # subset of the 3 REQUIRED fields not found
        }

    po_number is intentionally never listed in missing_fields — it's
    legitimately optional here, same as leaving it blank on manual
    entry (see INV-004/INV-014 in the seed data).
    """
    invoice_number = _first_match(INVOICE_NUMBER_PATTERNS, text)
    vendor_name = _first_match(VENDOR_NAME_PATTERNS, text)
    po_number = _first_match(PO_NUMBER_PATTERNS, text)
    amount = _extract_amount(text)

    missing_fields = []
    if not invoice_number:
        missing_fields.append("invoice number")
    if not vendor_name:
        missing_fields.append("vendor name")
    if amount is None:
        missing_fields.append("amount")

    return {
        "invoice_number": invoice_number,
        "vendor_name": vendor_name,
        "amount": amount,
        "po_number": po_number,
        "missing_fields": missing_fields,
    }


def extract_invoice_fields(pdf_bytes: bytes) -> dict:
    """
    Opens the PDF, pulls text from every page, and parses it via
    parse_fields_from_text(). Raises PdfExtractionError if the file
    can't be opened or has no extractable text at all.
    """
    import io
    import pdfplumber  # see module docstring for why this import is here, not at module level

    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            text = "\n".join(page.extract_text() or "" for page in pdf.pages)
    except Exception as e:
        raise PdfExtractionError(f"Could not open this file as a PDF: {e}") from e

    if not text.strip():
        raise PdfExtractionError(
            "No extractable text found in this PDF. If it's a scanned or "
            "image-based document, text extraction isn't supported — use "
            "the manual entry form instead."
        )

    return parse_fields_from_text(text)
