"""
Sequential orchestration pipeline for the three-agent ECI classification workflow.

Flow:
  1. Technical Extractor Agent  -> structured mechanical/operational JSON
     (Strictly forbidden from making legal claims)
  2. Legal Cross-Referencer Agent -> jurisdiction hypothesis + CFR citations
  3. Guardrail evaluation -> HARD STOP on dual-use / low confidence / missing citations
  4. Compliance Marking Generator Agent -> CUI banner (only reached if unambiguous)
"""

from typing import Callable, Optional, Dict, Any

from agents.extractor import run_technical_extractor
from agents.cross_referencer import run_legal_cross_referencer
from agents.marking_generator import run_compliance_marking_generator
from core.guardrails import evaluate_guardrails, DualUseGuardrailTriggered
from config.settings import DEFAULT_USML_REFERENCE, DEFAULT_CCL_REFERENCE


def orchestrate_classification(
    raw_document_text: str,
    usml_ref: Optional[str] = None,
    ccl_ref: Optional[str] = None,
    step_callback: Optional[Callable[[str, str, dict], None]] = None,
) -> dict:
    """
    Execute the sequential 3-agent orchestration pipeline with strict air-gapped guardrails.

    Args:
        raw_document_text: Raw technical description or PDF-extracted text.
        usml_ref: Optional USML reference text override.
        ccl_ref: Optional CCL reference text override.
        step_callback: Optional callback invoked after each agent step with
                       (event_type, message_text, payload).

    Returns:
        A pipeline audit trail dictionary containing:
          - status: "CLASSIFICATION_COMPLETE" or "HALTED_FOR_HUMAN_REVIEW"
          - extractor_output: Agent 1 JSON
          - legal_output: Agent 2 JSON
          - marking_output: Agent 3 JSON (only if not halted)
          - guardrail_triggered: bool
          - guardrail_details: dict (only if halted)
    """
    pipeline_audit_trail: Dict[str, Any] = {
        "status": "IN_PROGRESS",
        "extractor_output": None,
        "legal_output": None,
        "marking_output": None,
        "guardrail_triggered": False,
        "guardrail_details": None,
    }

    # ---- Step 1: Technical Extractor Agent ----
    if step_callback:
        step_callback(
            "extractor_start",
            "Agent 1: Extracting technical parameters (strictly non-legal)...",
            {},
        )

    extractor_specs = run_technical_extractor(raw_document_text)
    pipeline_audit_trail["extractor_output"] = extractor_specs

    if step_callback:
        step_callback(
            "extractor_done",
            "Agent 1: Technical specifications extracted.",
            extractor_specs,
        )

    # ---- Step 2: Legal Cross-Referencer Agent ----
    if step_callback:
        step_callback(
            "legal_start",
            "Agent 2: Cross-referencing against USML (22 CFR 121) and CCL (15 CFR 774)...",
            {},
        )

    usml_text = usml_ref or DEFAULT_USML_REFERENCE
    ccl_text = ccl_ref or DEFAULT_CCL_REFERENCE

    legal_hypothesis = run_legal_cross_referencer(
        extractor_specs, usml_ref=usml_text, ccl_ref=ccl_text
    )
    pipeline_audit_trail["legal_output"] = legal_hypothesis

    if step_callback:
        step_callback(
            "legal_done",
            "Agent 2: Statutory cross-referencing complete.",
            legal_hypothesis,
        )

    # ---- Step 3: Guardrail evaluation (Hard Stop Rule) ----
    try:
        evaluate_guardrails(legal_hypothesis)
    except DualUseGuardrailTriggered as guardrail_error:
        pipeline_audit_trail["status"] = "HALTED_FOR_HUMAN_REVIEW"
        pipeline_audit_trail["guardrail_triggered"] = True
        pipeline_audit_trail["guardrail_details"] = guardrail_error.details

        if step_callback:
            step_callback(
                "guardrail_halt",
                "⚠️ HARD STOP TRIGGERED: Dual-use ambiguity or citation deficit detected.",
                guardrail_error.details,
            )

        # Halt autonomous loop immediately. Do NOT run Compliance Marking Generator.
        return pipeline_audit_trail

    # ---- Step 4: Compliance Marking Generator Agent ----
    # Reached ONLY if the determination is unambiguous and confident.
    if step_callback:
        step_callback(
            "marking_start",
            "Agent 3: Generating CUI document markings and distribution warning...",
            {},
        )

    component_name = extractor_specs.get("component_name", "Aerospace Article")
    marking_output = run_compliance_marking_generator(
        legal_hypothesis, component_name=component_name
    )
    pipeline_audit_trail["marking_output"] = marking_output
    pipeline_audit_trail["status"] = "CLASSIFICATION_COMPLETE"

    if step_callback:
        step_callback(
            "marking_done",
            "Agent 3: CUI compliance banners and warnings successfully generated.",
            marking_output,
        )

    return pipeline_audit_trail
