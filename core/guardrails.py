"""
Hard-stop guardrail enforcement for the ECI classification pipeline.

The Legal Cross-Referencer is forbidden from default-guessing.
Dual-use ambiguity or missing CFR citations trigger an immediate halt
for manual human review to prevent false negatives.
"""

from config.settings import CONFIDENCE_THRESHOLD


class DualUseGuardrailTriggered(Exception):
    """Raised when an item is identified as dual-use or citations are ambiguous."""

    def __init__(self, message: str, details: dict):
        super().__init__(message)
        self.details = details


def evaluate_guardrails(legal_result: dict) -> None:
    """
    Enforce strict hard-stop rules on the Legal Cross-Referencer output.

    Halts the autonomous chain if any of the following are true:
      - The item is flagged as dual-use (is_dual_use == True).
      - Jurisdiction is indeterminate (DUAL_USE, UNCERTAIN, AMBIGUOUS, UNKNOWN).
      - Confidence score is below CONFIDENCE_THRESHOLD.
      - No verifiable CFR citations (22 CFR / 15 CFR) are present.
      - Manual human review is explicitly required.

    Never allows default guessing to prevent false negatives.

    Args:
        legal_result: The output dictionary from the Legal Cross-Referencer agent.

    Raises:
        DualUseGuardrailTriggered: If any guardrail violation is detected.
    """
    is_dual_use = bool(legal_result.get("is_dual_use", False))
    jurisdiction = str(legal_result.get("jurisdiction", "")).upper()
    confidence = float(legal_result.get("confidence_score", 0.0))
    citations = legal_result.get("citations", []) or []
    requires_review = bool(legal_result.get("requires_manual_human_review", False))

    violations = []

    if is_dual_use:
        violations.append(
            "ITEM FLAGGED AS DUAL-USE: Shared military defense and civil aerospace utility detected."
        )

    if jurisdiction in {"DUAL_USE", "UNCERTAIN", "AMBIGUOUS", "UNKNOWN", ""}:
        violations.append(f"JURISDICTION INDETERMINATE: Autonomous determination returned '{jurisdiction}'.")

    if confidence < CONFIDENCE_THRESHOLD:
        violations.append(
            f"LOW CONFIDENCE SCORE: Confidence is {confidence:.2f} "
            f"(Threshold: {CONFIDENCE_THRESHOLD:.2f} required for autonomous pass-through)."
        )

    if not citations:
        violations.append(
            "MISSING CITATIONS: Legal cross-referencer failed to establish specific CFR statutory citations."
        )
    else:
        valid_citations = [
            c
            for c in citations
            if c.get("code") and ("CFR" in c.get("code", "") or "22 CFR" in c.get("code", "") or "15 CFR" in c.get("code", ""))
        ]
        if not valid_citations:
            violations.append("INVALID CITATIONS: No verified CFR citations (22 CFR / 15 CFR) detected.")

    if requires_review or violations:
        conflicting_text = legal_result.get("conflicting_guidelines") or (
            "Potential overlap between USML (22 CFR 121) and CCL (15 CFR 774)."
        )
        reasoning_text = legal_result.get("reasoning") or (
            "Ambiguity in technical parameters or dual application platforms."
        )

        stop_payload = {
            "violations": violations,
            "jurisdiction": jurisdiction,
            "confidence_score": confidence,
            "citations": citations,
            "conflicting_guidelines": conflicting_text,
            "legal_reasoning": reasoning_text,
            "status": "HALTED_FOR_HUMAN_REVIEW",
        }
        raise DualUseGuardrailTriggered(
            f"Autonomous workflow halted due to safety guardrails: {'; '.join(violations)}",
            details=stop_payload,
        )
