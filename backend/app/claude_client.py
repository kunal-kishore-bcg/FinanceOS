"""
Claude API integration for invoice triage recommendations.

Uses forced tool-use so the model must return structured JSON, not
free text (brief 6.3: "Request structured output from the LLM (JSON
with defined keys) — do not parse free-text responses with regex").

The prompt lives in /prompts/invoice_triage.md, not hardcoded here
(brief 6.3: "Prompts must be externalised from code"). That file is
currently a PLACEHOLDER — see the note at its top. Swap in the
finalized version from your Prompt Engineering chat before the demo;
nothing else in this file needs to change when you do.
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
        },
        "required": ["recommendation", "rationale"],
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
              "error": str | None}.

    On any failure (timeout, rate limit, malformed response, anything
    else), recommendation is None and error explains why — brief 3.2:
    "handle LLM failure gracefully ... show a fallback state in the
    UI." The caller must not default a None recommendation to
    "approve" — that would auto-approve on the *absence* of AI output,
    which is worse than the "never auto-approve on AI output alone"
    rule it's meant to satisfy. routers/invoices.py keeps such invoices
    in pending_review.
    """
    try:
        system_prompt = _load_system_prompt()
    except FileNotFoundError as e:
        logger.error(str(e))
        return {"recommendation": None, "rationale": None, "error": str(e)}

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
        return {"recommendation": None, "rationale": None,
                "error": "AI request timed out — manual review required."}
    except anthropic.RateLimitError:
        logger.warning("Claude API rate-limited for invoice %s", invoice_number)
        return {"recommendation": None, "rationale": None,
                "error": "AI service is rate-limited — manual review required."}
    except anthropic.APIStatusError as e:
        logger.error("Claude API error for invoice %s: %s", invoice_number, e)
        return {"recommendation": None, "rationale": None,
                "error": f"AI service error ({e.status_code}) — manual review required."}
    except Exception as e:  # last-resort net — this call must never crash the request
        logger.error("Unexpected error calling Claude for invoice %s: %s", invoice_number, e)
        return {"recommendation": None, "rationale": None,
                "error": "AI service unavailable — manual review required."}

    for block in response.content:
        if block.type == "tool_use" and block.name == "submit_triage_recommendation":
            result = block.input
            return {
                "recommendation": result.get("recommendation"),
                "rationale": result.get("rationale"),
                "error": None,
            }

    logger.error("Claude response for invoice %s had no tool_use block", invoice_number)
    return {"recommendation": None, "rationale": None,
            "error": "AI did not return a structured recommendation — manual review required."}
