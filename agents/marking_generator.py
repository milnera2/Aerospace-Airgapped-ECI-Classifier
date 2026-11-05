"""
Compliance Marking Generator Agent.

Generates exact Controlled Unclassified Information (CUI) banner and
document markings based on a verified legal hypothesis.

Compliant with:
- 32 CFR Part 2002 (National CUI Program)
- DoD Instruction 5200.48 (Controlled Unclassified Information)
- 22 CFR Parts 120-130 (ITAR Statutory Warning Notices)
- 15 CFR Parts 730-774 (EAR Export Administration Notices)
"""

import json

from core.ollama_client import call_local_ollama

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


def run_compliance_marking_generator(
    legal_hypothesis: dict,
    component_name: str = "Aerospace Component",
) -> dict:
    """
    Generate official CUI compliance markings and statutory warning block
    for a verified export determination.

    Args:
        legal_hypothesis: Verified legal determination from the Cross-Referencer.
        component_name: Name of the aerospace component being marked.

    Returns:
        Parsed JSON dictionary with CUI banner and marking details.
    """
    user_prompt = f"""Generate the official CUI compliance markings and statutory warning block for the following verified export determination:

Component: {component_name}
Determination:
{json.dumps(legal_hypothesis, indent=2)}

Output the exact formatting required under 32 CFR 2002 and federal export control marking guidelines.
"""
    return call_local_ollama(
        prompt=user_prompt,
        system_prompt=COMPLIANCE_MARKING_SYSTEM_PROMPT,
        temperature=0.0,
    )
