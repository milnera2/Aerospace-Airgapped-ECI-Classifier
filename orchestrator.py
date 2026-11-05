"""
orchestrator.py
Air-Gapped Multi-Agent Workflow for Export Controlled Information (ECI) Classification.
Operates strictly locally via Ollama (Llama 3.1) with no external or cloud dependencies.
"""

import os
import json
import re
from typing import Dict, Any, Optional, Callable
import requests

# Local Ollama configuration (Strictly Air-Gapped localhost)
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1:latest")
REQUEST_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "120"))

# Default reference text excerpts for USML and CCL if custom index not provided
DEFAULT_USML_REFERENCE = """
UNITED STATES MUNITIONS LIST (USML) - 22 CFR PART 121:
- Category VIII (Aircraft and Related Articles):
  * VIII(a): Aircraft, including helicopters, UAVs, specifically designed or modified for military use.
  * VIII(f): Engines specifically designed or modified for military aircraft.
  * VIII(h): Parts, components, accessories, attachments, and associated equipment specifically designed or modified for defense articles in VIII(a)-(f), including stealth coatings, structural composites certified to military combat shock/vibration/12G+ limit loads, and tactical avionics.
- Category IV (Launch Vehicles, Guided Missiles, Ballistic Missiles, Rockets):
  * IV(a): Rockets, guided missiles, space launch vehicles.
  * IV(f): Structural materials, ablative thermal protection, scramjet/ramjet components specifically designed for missiles or hypersonic weapons.
- Category XIII (Materials and Miscellaneous Articles):
  * XIII(f): Structural materials, radar-absorbent materials (RAM), and coatings specifically designed to reduce radar cross section or infrared signature for defense applications.
- 22 CFR 120.41 ("Specifically Designed"): An item is specifically designed if, as a result of development, it has properties peculiarly responsible for achieving or exceeding performance levels or functions directly related to military defense articles, and is NOT released under 120.41(b) (e.g. form/fit/function common standard commercial parts).
"""

DEFAULT_CCL_REFERENCE = """
COMMERCE CONTROL LIST (CCL) - 15 CFR PART 774 (SUPPLEMENT NO. 1):
- Category 9 (Aerospace and Propulsion):
  * 9A001: Aero gas turbine engines incorporating civil certification technologies (ICAO Annex 16).
  * 9A610: Military aircraft and "specially designed" parts, components, accessories, and attachments therefor not listed in USML Category VIII (the "600 series" transition).
  * 9A991: Civil aircraft and parts/components "specially designed" therefor, not controlled under 9A001 or 9A610 (civil airliners, commercial transport items).
  * EAR99: Items subject to the EAR that are not specified on the Commerce Control List (low-tech, standard civil commercial items with no proprietary defense characteristics).
- Category 1 (Special Materials and Related Equipment):
  * 1C010: Fibrous or filamentary materials suitable for aerospace composite structures (polyacrylonitrile (PAN) based carbon fibers with specific tensile modulus >= 12.7 x 10^6 m).
"""


def call_local_ollama(prompt: str, system_prompt: str, model: str = OLLAMA_MODEL, temperature: float = 0.0) -> Dict[str, Any]:
    """
    Executes a prompt against the local Ollama instance with JSON format enforcement.
    Air-gapped: Strictly communicates with 127.0.0.1.
    """
    url = f"{OLLAMA_HOST}/api/generate"
    payload = {
        "model": model,
        "system": system_prompt,
        "prompt": prompt,
        "stream": False,
        "format": "json",
        "options": {
            "temperature": temperature,
            "top_p": 0.9,
        }
    }

    try:
        response = requests.post(url, json=payload, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        res_json = response.json()
        raw_output = res_json.get("response", "").strip()

        # Parse JSON from response
        try:
            return json.loads(raw_output)
        except json.JSONDecodeError:
            # Fallback: find json code block if present
            match = re.search(r"\{.*\}", raw_output, re.DOTALL)
            if match:
                return json.loads(match.group(0))
            raise ValueError(f"Failed to parse valid JSON from Ollama response: {raw_output[:200]}...")

    except requests.exceptions.ConnectionError as e:
        raise ConnectionError(
            f"Cannot connect to local Ollama instance at {OLLAMA_HOST}. "
            "Verify Ollama is running locally ('ollama serve') and accessible on localhost. "
            "Air-gapped operation forbids external network routing."
        ) from e
    except Exception as e:
        raise RuntimeError(f"Ollama execution failed: {str(e)}") from e


# ============================================================================
# AGENT 1: TECHNICAL EXTRACTOR AGENT
# ============================================================================
TECHNICAL_EXTRACTOR_SYSTEM_PROMPT = """You are a Senior Aerospace Materials and Mechanical Specifications Extractor.
Your SOLE responsibility is to analyze raw technical descriptions, engineering datasheets, or extracted PDF specifications and extract clean, factual mechanical and operational specifications into structured JSON.

CRITICAL MANDATORY CONSTRAINT:
You are an engineering analyst ONLY. You are STRICTLY FORBIDDEN from making legal determinations, evaluating export regulations, mentioning ITAR, EAR, ECCN, USML, CFR citations, or drawing any jurisdictional conclusions. Any mention of export law or classification opinions constitutes an immediate protocol failure.

You must extract and output strictly valid JSON matching this schema:
{
  "component_name": "string",
  "part_designation": "string",
  "primary_function": "string",
  "materials_composition": ["string"],
  "mechanical_parameters": {
    "dimensions_and_tolerances": "string",
    "load_capacity_or_tensile_strength": "string",
    "mass_or_density": "string"
  },
  "operational_envelope": {
    "temperature_range": "string",
    "pressure_or_altitude": "string",
    "vibration_or_shock_profile": "string"
  },
  "application_interfaces": "string",
  "unique_physical_features": ["string"],
  "intended_platform": "string"
}
"""

def run_technical_extractor(raw_text: str) -> Dict[str, Any]:
    """Ingests raw text/PDF specs and outputs structured mechanical/operational specifications in JSON."""
    user_prompt = f"""Extract the technical, physical, and operational specifications from the following document into the required JSON format:

--- TECHNICAL DOCUMENT ---
{raw_text}
--- END DOCUMENT ---
"""
    return call_local_ollama(
        prompt=user_prompt,
        system_prompt=TECHNICAL_EXTRACTOR_SYSTEM_PROMPT,
        temperature=0.0
    )


# ============================================================================
# AGENT 2: LEGAL CROSS-REFERENCER AGENT
# ============================================================================
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

def run_legal_cross_referencer(specs_json: Dict[str, Any], usml_ref: Optional[str] = None, ccl_ref: Optional[str] = None) -> Dict[str, Any]:
    """Maps structured technical specifications against USML and CCL legal indices."""
    usml_text = usml_ref or DEFAULT_USML_REFERENCE
    ccl_text = ccl_ref or DEFAULT_CCL_REFERENCE

    user_prompt = f"""Analyze the following structured aerospace engineering specifications against the provided USML and CCL legal references.

--- STRUCTURED ENGINEERING SPECIFICATIONS ---
{json.dumps(specs_json, indent=2)}

--- USML STATUTORY REFERENCE (22 CFR 121) ---
{usml_text}

--- CCL REGULATORY REFERENCE (15 CFR 774) ---
{ccl_text}

Apply the statutory Order of Review. Deliver your analysis in the mandatory JSON schema.
"""
    return call_local_ollama(
        prompt=user_prompt,
        system_prompt=LEGAL_CROSS_REFERENCER_SYSTEM_PROMPT,
        temperature=0.0
    )


# ============================================================================
# AGENT 3: COMPLIANCE MARKING GENERATOR AGENT
# ============================================================================
COMPLIANCE_MARKING_SYSTEM_PROMPT = """You are a Federal Compliance Marking Specialist for Export-Controlled Aerospace Technical Data.
Your task is to generate exact Controlled Unclassified Information (CUI) banner and document markings in strict compliance with:
- 32 CFR Part 2002 (National CUI Program)
- DoD Instruction 5200.48 (Controlled Unclassified Information)
- 22 CFR Parts 120-130 (ITAR Statutory Warning Notices)
- 15 CFR Parts 730-774 (EAR Export Administration Notices)

You will be given a validated, non-ambiguous legal classification hypothesis (ITAR or EAR) with verified citations.

Marking Requirements:
1. Header and Footer Banners:
   - For ITAR: // CUI // SP-EXPT //
   - For EAR: // CUI // SP-EXPT // (or // CUI // FEDCON // depending on dissemination)
2. CUI Control Block (Designated authority, CUI category, dissemination control, distribution statement).
3. Statutory Warning Statement:
   - For ITAR: Exact 22 CFR 120.10 / Arms Export Control Act warning statement.
   - For EAR: Exact 15 CFR 730-774 Export Administration Regulations warning notice.

You must output strictly valid JSON matching this schema:
{
  "banner_header": "string",
  "banner_footer": "string",
  "cui_category": "string",
  "limited_dissemination_controls": "string",
  "cui_control_block": {
    "controlled_by": "string",
    "controlling_office": "string",
    "cui_category": "string",
    "dissemination_control": "string",
    "poc": "string"
  },
  "statutory_warning_statement": "string",
  "complete_cui_document_marking": "string"
}
"""

def run_compliance_marking_generator(legal_hypothesis: Dict[str, Any], component_name: str = "Aerospace Component") -> Dict[str, Any]:
    """Generates official CUI banner and document markings for verified jurisdictional determinations."""
    user_prompt = f"""Generate the official CUI compliance markings and statutory warning block for the following verified export determination:

Component: {component_name}
Determination:
{json.dumps(legal_hypothesis, indent=2)}

Output the exact formatting required under 32 CFR 2002 and federal export control marking guidelines.
"""
    return call_local_ollama(
        prompt=user_prompt,
        system_prompt=COMPLIANCE_MARKING_SYSTEM_PROMPT,
        temperature=0.0
    )


# ============================================================================
# ORCHESTRATION PIPELINE & GUARDRAIL ENFORCEMENT
# ============================================================================
class DualUseGuardrailTriggered(Exception):
    """Raised when an item is identified as dual-use or citations are ambiguous."""
    def __init__(self, message: str, details: Dict[str, Any]):
        super().__init__(message)
        self.details = details


def evaluate_guardrails(legal_result: Dict[str, Any]) -> None:
    """
    Enforces strict hard-stop rules.
    If the Legal Cross-Referencer flags an item as dual-use, or fails to generate
    high-confidence citations, this halts the autonomous chain immediately.
    Never allows default guessing to prevent false negatives.
    """
    is_dual_use = legal_result.get("is_dual_use", False)
    jurisdiction = str(legal_result.get("jurisdiction", "")).upper()
    confidence = float(legal_result.get("confidence_score", 0.0))
    citations = legal_result.get("citations", [])
    requires_review = legal_result.get("requires_manual_human_review", False)

    violations = []

    if is_dual_use:
        violations.append("ITEM FLAGGED AS DUAL-USE: Shared military defense and civil aerospace utility detected.")

    if jurisdiction in ["DUAL_USE", "UNCERTAIN", "AMBIGUOUS", "UNKNOWN"]:
        violations.append(f"JURISDICTION INDETERMINATE: Autonomous determination returned '{jurisdiction}'.")

    if confidence < 0.75:
        violations.append(f"LOW CONFIDENCE SCORE: Confidence is {confidence:.2f} (Threshold: 0.75 required for autonomous pass-through).")

    if not citations or len(citations) == 0:
        violations.append("MISSING CITATIONS: Legal cross-referencer failed to establish specific CFR statutory citations.")
    else:
        # Check that citations are not blank/dummy
        valid_citations = [c for c in citations if c.get("code") and "CFR" in c.get("code", "")]
        if not valid_citations:
            violations.append("INVALID CITATIONS: No verified CFR citations (22 CFR / 15 CFR) detected.")

    if requires_review or violations:
        conflicting_text = legal_result.get("conflicting_guidelines") or "Potential overlap between USML (22 CFR 121) and CCL (15 CFR 774)."
        reasoning_text = legal_result.get("reasoning") or "Ambiguity in technical parameters or dual application platforms."
        
        stop_payload = {
            "violations": violations,
            "jurisdiction": jurisdiction,
            "confidence_score": confidence,
            "citations": citations,
            "conflicting_guidelines": conflicting_text,
            "legal_reasoning": reasoning_text,
            "status": "HALTED_FOR_HUMAN_REVIEW"
        }
        raise DualUseGuardrailTriggered(
            f"Autonomous workflow halted due to safety guardrails: {'; '.join(violations)}",
            details=stop_payload
        )


def orchestrate_classification(
    raw_document_text: str,
    usml_ref: Optional[str] = None,
    ccl_ref: Optional[str] = None,
    step_callback: Optional[Callable[[str, str, Dict[str, Any]], None]] = None
) -> Dict[str, Any]:
    """
    Executes the sequential 3-agent orchestration pipeline with strict air-gapped guardrails.
    
    Flow:
    1. Technical Extractor Agent: Ingests raw text, outputs structured mechanical JSON.
       (Strictly forbidden from making legal claims)
    2. Legal Cross-Referencer Agent: Maps specs to USML/CCL, outputs citations & hypothesis.
    3. GUARDRAIL EVALUATION:
       - If dual-use or citation ambiguity detected -> HARD STOP. Halt loop, flag for human review.
       - NEVER guess to avoid false negatives.
    4. Compliance Marking Generator Agent: If clear determination, generates official CUI markings.
    """
    pipeline_audit_trail = {
        "status": "IN_PROGRESS",
        "extractor_output": None,
        "legal_output": None,
        "marking_output": None,
        "guardrail_triggered": False,
        "guardrail_details": None
    }

    # Step 1: Technical Extractor Agent
    if step_callback:
        step_callback("extractor_start", "Agent 1: Extracting technical parameters (strictly non-legal)...", {})
    
    extractor_specs = run_technical_extractor(raw_document_text)
    pipeline_audit_trail["extractor_output"] = extractor_specs

    if step_callback:
        step_callback("extractor_done", "Agent 1: Technical specifications extracted.", extractor_specs)

    # Step 2: Legal Cross-Referencer Agent
    if step_callback:
        step_callback("legal_start", "Agent 2: Cross-referencing against USML (22 CFR 121) and CCL (15 CFR 774)...", {})

    legal_hypothesis = run_legal_cross_referencer(extractor_specs, usml_ref=usml_ref, ccl_ref=ccl_ref)
    pipeline_audit_trail["legal_output"] = legal_hypothesis

    if step_callback:
        step_callback("legal_done", "Agent 2: Statutory cross-referencing complete.", legal_hypothesis)

    # Step 3: Enforce Guardrails (Hard Stop Rule)
    try:
        evaluate_guardrails(legal_hypothesis)
    except DualUseGuardrailTriggered as guardrail_error:
        pipeline_audit_trail["status"] = "HALTED_FOR_HUMAN_REVIEW"
        pipeline_audit_trail["guardrail_triggered"] = True
        pipeline_audit_trail["guardrail_details"] = guardrail_error.details

        if step_callback:
            step_callback("guardrail_halt", "⚠️ HARD STOP TRIGGERED: Dual-use ambiguity or citation deficit detected.", guardrail_error.details)

        # Halt autonomous loop immediately. Do NOT run Compliance Marking Generator.
        return pipeline_audit_trail

    # Step 4: Compliance Marking Generator Agent (Reached ONLY if unambiguous)
    if step_callback:
        step_callback("marking_start", "Agent 3: Generating CUI document markings and distribution warning...", {})

    component_name = extractor_specs.get("component_name", "Aerospace Article")
    marking_output = run_compliance_marking_generator(legal_hypothesis, component_name=component_name)
    pipeline_audit_trail["marking_output"] = marking_output
    pipeline_audit_trail["status"] = "CLASSIFICATION_COMPLETE"

    if step_callback:
        step_callback("marking_done", "Agent 3: CUI compliance banners and warnings successfully generated.", marking_output)

    return pipeline_audit_trail
