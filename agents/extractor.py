"""
Technical Extractor Agent.

Ingests raw technical descriptions / PDF text and outputs structured
mechanical and operational specifications in JSON.

STRICTLY FORBIDDEN from making legal determinations (ITAR/EAR/USML/CFR).
"""

from core.ollama_client import call_local_ollama

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


def run_technical_extractor(raw_text: str) -> dict:
    """
    Ingest raw text/PDF specs and output structured mechanical/operational
    specifications in JSON.

    Args:
        raw_text: Raw technical description or PDF-extracted text.

    Returns:
        Parsed JSON dictionary of extracted specifications.
    """
    user_prompt = f"""Extract the technical, physical, and operational specifications from the following document into the required JSON format:

--- TECHNICAL DOCUMENT ---
{raw_text}
--- END DOCUMENT ---
"""
    return call_local_ollama(
        prompt=user_prompt,
        system_prompt=TECHNICAL_EXTRACTOR_SYSTEM_PROMPT,
        temperature=0.0,
    )
