"""
Configuration settings for the air-gapped ECI classification system.

All LLM execution is strictly local via Ollama on localhost.
No cloud API endpoints are permitted.
"""

import os

# ---------------------------------------------------------------------------
# Ollama local API configuration (Air-Gapped)
# ---------------------------------------------------------------------------
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1:latest")
REQUEST_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "120"))

# ---------------------------------------------------------------------------
# Guardrail thresholds
# ---------------------------------------------------------------------------
# Autonomous pass-through requires confidence at or above this threshold.
# Below this value, the pipeline halts for manual human review.
CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", "0.75"))

# ---------------------------------------------------------------------------
# Default statutory reference text (embedded fallback)
# Used when no external USML/CCL reference files are supplied.
# ---------------------------------------------------------------------------
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
