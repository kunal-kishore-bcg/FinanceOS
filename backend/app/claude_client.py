"""
Claude API integration for invoice triage recommendations.

Uses forced tool-use so the model must return structured JSON, not
free text (brief 6.3: "Request structured output from the LLM (JSON
with defined keys) — do not parse free-text responses with regex").

The prompt lives in /prompts/invoice_triage.md, not hardcoded here
(brief 6.3: "Prompts must be externalised from code"). That file is
currently a PLACEHOLDER — see the note at its top.

--------------------------------------------------------------------
SCHEMA STATUS — read before assuming this matches your finalized prompt
--------------------------------------------------------------------
TRIAGE_TOOL below has 5 fields (recommendation, rationale, confidence,
flags, reviewer_action) per your instruction. Three of them
(confidence, flags, reviewer_action) are PROVISIONAL — the local copy
of /prompts/invoice_triage.md has no JSON schema section to check
against, so their types/enum values are a best guess, not a verified
match to whatever you've written in your Prompt Engineering chat:

  - confidence: enum "high"/"medium"/"low". Could just as easily be a
    0-1 float or a 0-100 score in your actual prompt — went with a
    categorical enum because everything else in this project has been
    "Finance-literate language, no technical terms," and a raw
    probability reads as a technical artifact to a Finance analyst.
  - flags: array of strings — assumed to echo back the rule-engine
    findings the recommendation was based on (same shape already
    passed in via the user message).
  - reviewer_action: free-text string — one sentence telling the human
    reviewer what to check before acting on the recommendation.

Paste the actual JSON schema from your prompt and these three get
corrected to match exactly, not guessed at.

CONSEQUENCE NOT YET HANDLED: confidence/flags/reviewer_action are
returned by get_triage_recommendation() below, but Invoice (the model)
only has ai_recommendation and ai_rationale columns. Nothing in
routers/invoices.py stores the new three fields anywhere queryable —
right now they'd only survive inside the audit_log JSON blob, not on
the invoice row itself. That's specifically why the frontend's
Confidence column would still show nothing after this change alone —
closing that gap needs a follow-up migration + model + router change,
not just this file. Flagging it now so it doesn't look like this fix
was supposed to be complete on its own.
--------------------------------------------------------------------
"""
from __future__ import annotations

import logging
from pathlib import Path

import anthropic

from app.config import settings

logger = logging.getLogger("financeos.claude")

PROMPT_PATH = Path(__file__).parent.parent.parent / "prompts" / "invoice_triage.md"

# claude-sonnet-5: balance of reasoning depth and cost for a structured
# classification task. Swap freely — nothing else here depends on the
# specific model string.
MODEL = "claude-sonnet-5"

TRIAGE_TOOL = {
    "name": "submit_triage_recommendation",
    "description": "Submit a triage recommendation for a single AP invoice exception.",
    "input_schema": {
        "type": "object",
        "properties": {
            "recommendation": {
                "type": "string",
                "enum": ["approve", "escalate", "reject"],
            },
            "rationale": {
                "type": "string",
                "description": "One sentence, plain-English, explaining the recommendation to a Finance analyst.",
            },
            # PROVISIONAL — see module docstring. Confirm against the
            # real prompt: type (enum vs numeric) and exact values.
            "confidence": {
                "type": "string",
                "enum": ["high", "medium", "low"],
                "description": "How confident the model is in this recommendation, in Finance-literate terms.",
            },
            # PROVISIONAL — see module docstring. Confirm whether this
            # should echo the rule-engine findings verbatim or be a
            # model-selected subset of the ones that drove the decision.
            "flags": {
                "type": "array",
                "items": {"type": "string"},
                "description": "The rule-engine findings this recommendation is based on.",
            },
            # PROVISIONAL — see module docstring. Confirm field name
            # and whether it's free text or a constrained set of actions.
            "reviewer_action": {
                "type": "string",
                "description": "One sentence telling the human reviewer what to check before acting on this recommendation.",
            },
        },
        "required": ["recommendation", "rationale", "confidence", "flags", "reviewer_action"],
    },
}


def _load_system_prompt() -> str:
    if not PROMPT_PATH.exists():
        raise FileNotFoundError(
            f"Prompt template not found at {PROMPT_PATH}. Expected per the brief's "
            "repo structure (Deliverable 2: '/prompts/ — one .md per process')."
        )
    return PROMPT_PATH.read_text()


def _build_user_message(invoice_number: str, vendor_name: str, amount: float, flags: list[str]) -> str:
    flags_text = "\n".join(f"- {f}" for f in flags) if flags else "- No exceptions detected by rule-based checks."
    return (
        f"Invoice: {invoice_number}\n"
        f"Vendor: {vendor_name}\n"
        f"Amount: ${amount:,.2f}\n\n"
        f"Rule-engine findings:\n{flags_text}\n\n"
        "Based only on the findings above, recommend approve, escalate, or reject, "
        "with a one-sentence rationale."
    )


def get_triage_recommendation(
    invoice_number: str,
    vendor_name: str,
    amount: float,
    flags: list[str],
) -> dict:
    """
    Returns {"recommendation": "approve"|"escalate"|"reject"|None,
              "rationale": str | None,
              "confidence": "high"|"medium"|"low"|None,
              "flags": list[str] | None,
              "reviewer_action": str | None,
              "error": str | None}.

    All 6 keys are present on every return path, including every
    failure branch below — a caller checking result.get("confidence")
    should never hit a KeyError just because the AI call failed instead
    of succeeding.

    On any failure (timeout, rate limit, malformed response, anything
    else), every field is None except error, which explains why —
    brief 3.2: "handle LLM failure gracefully ... show a fallback state
    in the UI." The caller must not default a None recommendation to
    "approve" — that would auto-approve on the *absence* of AI output,
    which is worse than the "never auto-approve on AI output alone"
    rule it's meant to satisfy. routers/invoices.py keeps such invoices
    in pending_review.
    """
    empty_result = {"recommendation": None, "rationale": None, "confidence": None,
                     "flags": None, "reviewer_action": None}

    try:
        system_prompt = _load_system_prompt()
    except FileNotFoundError as e:
        logger.error(str(e))
        return {**empty_result, "error": str(e)}

    user_message = _build_user_message(invoice_number, vendor_name, amount, flags)
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=500,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
            tools=[TRIAGE_TOOL],
            tool_choice={"type": "tool", "name": "submit_triage_recommendation"},
            timeout=30.0,
        )
    except anthropic.APITimeoutError:
        logger.warning("Claude API timed out for invoice %s", invoice_number)
        return {**empty_result, "error": "AI request timed out — manual review required."}
    except anthropic.RateLimitError:
        logger.warning("Claude API rate-limited for invoice %s", invoice_number)
        return {**empty_result, "error": "AI service is rate-limited — manual review required."}
    except anthropic.APIStatusError as e:
        logger.error("Claude API error for invoice %s: %s", invoice_number, e)
        return {**empty_result, "error": f"AI service error ({e.status_code}) — manual review required."}
    except Exception as e:  # last-resort net — this call must never crash the request
        logger.error("Unexpected error calling Claude for invoice %s: %s", invoice_number, e)
        return {**empty_result, "error": "AI service unavailable — manual review required."}

    for block in response.content:
        if block.type == "tool_use" and block.name == "submit_triage_recommendation":
            result = block.input
            return {
                "recommendation": result.get("recommendation"),
                "rationale": result.get("rationale"),
                "confidence": result.get("confidence"),
                "flags": result.get("flags"),
                "reviewer_action": result.get("reviewer_action"),
                "error": None,
            }

    logger.error("Claude response for invoice %s had no tool_use block", invoice_number)
    return {**empty_result, "error": "AI did not return a structured recommendation — manual review required."}
