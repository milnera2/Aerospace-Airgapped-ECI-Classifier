"""
Legal Cross-Referencer Agent.

Maps structured technical specifications against USML (22 CFR Part 121)
and CCL (15 CFR Part 774) reference text. Outputs a jurisdictional
hypothesis and specific CFR citations.

Enforces strict no-guessing rules: dual-use edge cases and missing
citations trigger a hard stop for manual human review.
"""

import json

from core.ollama_client import call_local_ollama

LEGAL_CROSS_REFERENCER_SYSTEM_PROMPT = """You are a Senior Aerospace Export Control Compliance Officer and Statutory Legal Cross-Referencer.
Your task is to analyze structured engineering specifications and cross-reference them against the United States Munitions List (USML, 22 CFR Part 121) and the Commerce Control List (CCL, 15 CFR Part 774).

REGULATORY ANALYSIS PROTOCOL:
1. ITAR Order of Review (22 CFR 120.11): Review USML first. Check if the item is enumerated or captured under 22 CFR 120.41 ("specially designed" for defense articles).
2. CCL Review (15 CFR 774): If not on USML, evaluate Commerce Control List (Category 9 aerospace, 600-series military transition, or 9A991 / EAR99 commercial standard).
3. Dual-Use & Specific Design Analysis: Check if the component is used across both civil aircraft (e.g. commercial airliners) and military defense articles, or if it meets dual-use performance thresholds (e.g. high-modulus composite structures, 12G+ limit loads, or cross-platform structural fittings).

MANDATORY GUARDRAILS & STOP RULES:
- NEVER GUESS. Export control violations carry severe criminal and civil penalties. A false negative (classifying an ITAR article as EAR or EAR99) is catastrophic.
- If an item is a DUAL-USE edge case (shared application between military defense and commercial platforms without an explicit 22 CFR 120.41(b) release), you MUST set "is_dual_use": true, "jurisdiction": "DUAL_USE", and flag it for human manual review.
- If you cannot identify a real, specific, verifiable CFR citation (e.g., "22 CFR 121.1 Cat VIII(h)" or "15 CFR 774 Supp 1 ECCN 9A610.x"), you must set "confidence_score" below 0.70 and flag it for human manual review.
- When ambiguity exists, document the conflicting guidelines exhaustively.

You must output strictly valid JSON matching this schema:
{
  "jurisdiction": "ITAR" | "EAR" | "DUAL_USE" | "UNCERTAIN",
  "is_dual_use": true | false,
  "confidence_score": 0.00 to 1.00,
  "citations": [
    {
      "code": "CFR citation string (e.g. 22 CFR 121.1 Category VIII(h))",
      "description": "Text of the regulation applied",
      "applicability": "Why this specific engineering parameter satisfies or conflicts with this rule"
    }
  ],
  "reasoning": "Detailed legal reasoning explaining the jurisdictional hypothesis",
  "requires_manual_human_review": true | false,
  "conflicting_guidelines": "Explanation of conflicting rules or dual-use overlap requiring human intervention (or empty if unambiguous)"
}
"""


def run_legal_cross_referencer(
    specs_json: dict,
    usml_ref: str | None = None,
    ccl_ref: str | None = None,
) -> dict:
    """
    Map structured technical specifications against USML and CCL legal indices.

    Args:
        specs_json: Structured engineering specifications from the Extractor.
        usml_ref: USML reference text.
        ccl_ref: CCL reference text.

    Returns:
        Parsed JSON dictionary with jurisdiction, citations, confidence, etc.
    """
    user_prompt = f"""Analyze the following structured aerospace engineering specifications against the provided USML and CCL legal references.

--- STRUCTURED ENGINEERING SPECIFICATIONS ---
{json.dumps(specs_json, indent=2)}

--- USML STATUTORY REFERENCE (22 CFR 121) ---
{usml_ref or ""}

--- CCL REGULATORY REFERENCE (15 CFR 774) ---
{ccl_ref or ""}

Apply the statutory Order of Review. Deliver your analysis in the mandatory JSON schema.
"""
    return call_local_ollama(
        prompt=user_prompt,
        system_prompt=LEGAL_CROSS_REFERENCER_SYSTEM_PROMPT,
        temperature=0.0,
    )
