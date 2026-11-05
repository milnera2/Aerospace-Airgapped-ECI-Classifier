"""
generate_test_pdfs.py

Generates three demo PDF technical specifications for the ECI classification
workflow: Commercial Baseline, Defense Article, and Dual-Use Edge Case.

Run once to create the test_pdfs/ directory with sample PDFs:
    python generate_test_pdfs.py
"""

import os
import pymupdf  # PyMuPDF

TEST_PDFS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_pdfs")

TEST_CASES = {
    "commercial_baseline.pdf": (
        "Component Name: Commercial airliner wing root attach bracket.\n"
        "Part Designation: BRK-737-WR-001\n"
        "Primary Function: Structural load path fitting attaching wing spars to fuselage on a commercial transport aircraft.\n"
        "Materials Composition: [\"7075-T6 aluminum alloy\", \"anodized finish\"]\n"
        "Mechanical Parameters: Dimensions and tolerances per AS9100 drawing. Limit load capacity 45,000 lbf. Mass 2.1 kg.\n"
        "Operational Envelope: Temperature range -55C to +70C. Pressurized cabin equivalent to 8,000 ft altitude. Standard commercial flight vibration spectrum.\n"
        "Application Interfaces: Bolted to commercial transport fuselage and wing carry-through structure.\n"
        "Unique Physical Features: Standard civil certified bolt pattern, no stealth features, no combat shock requirements.\n"
        "Intended Platform: Commercial passenger airliner (civil transport category).\n"
        "Certification Basis: FAA Part 25 transport category, civil certified.\n"
    ),
    "defense_article.pdf": (
        "Component Name: F-15 structural bulkhead fitting.\n"
        "Part Designation: BHF-F15-BH-042\n"
        "Primary Function: Critical load path structural bulkhead fitting on F-15 Eagle military fighter aircraft, transferring combat maneuver loads between wing box and fuselage.\n"
        "Materials Composition: [\"Titanium 6Al-4V\", \"stealth-grade RAM-compatible primer\", \"cadmium plating\"]\n"
        "Mechanical Parameters: Dimensions per MIL-SPEC drawing. Limit load capacity 150,000 lbf at 12G combat maneuver. Mass 8.7 kg.\n"
        "Operational Envelope: Temperature range -54C to +71C. High-altitude supersonic operation to 65,000 ft. Combat shock and vibration profile per MIL-STD-810.\n"
        "Application Interfaces: Bolted to military fighter airframe structures; interface with weapons pylons.\n"
        "Unique Physical Features: 12G+ limit load certification, combat survivability features, radar cross-section reduction geometry, specifically designed for military combat aircraft.\n"
        "Intended Platform: F-15 Eagle military fighter (USML Category VIII defense article).\n"
        "Certification Basis: MIL-STD / military specification; not FAA Part 25 civil certified.\n"
    ),
    "dual_use_edge_case.pdf": (
        "Component Name: Structural composite strut assembly.\n"
        "Part Designation: STRUT-COMP-X-009\n"
        "Primary Function: Primary load-bearing structural strut used on both commercial regional airliners and military transport aircraft.\n"
        "Materials Composition: [\"carbon fiber reinforced polymer (CFRP)\", \"high-modulus PAN-based carbon fiber\", \"epoxy resin matrix\"]\n"
        "Mechanical Parameters: Dimensions per dual-qualified drawing. Tensile modulus 42 x 10^6 m (high-modulus carbon fiber). Limit load 98,000 lbf. Mass 3.4 kg.\n"
        "Operational Envelope: Temperature range -54C to +85C. Commercial and military flight profiles. MIL-STD-810 vibration and commercial airline gust spectra.\n"
        "Application Interfaces: Mounts to both civil transport fuselage and military cargo aircraft wing structures.\n"
        "Unique Physical Features: High-modulus carbon fiber composite (1C010 material threshold), dual-platform installation hardware, shared civil/military part number.\n"
        "Intended Platform: Dual use — commercial regional airliners AND military transport aircraft.\n"
        "Certification Basis: FAA Part 25 civil certification AND military specification qualification.\n"
    ),
}


def generate_pdfs():
    os.makedirs(TEST_PDFS_DIR, exist_ok=True)

    for filename, text in TEST_CASES.items():
        filepath = os.path.join(TEST_PDFS_DIR, filename)
        doc = pymupdf.open()
        page = doc.new_page()
        page.insert_text((50, 50), text, fontsize=10)
        doc.save(filepath)
        doc.close()
        print(f"Generated: {filepath}")


if __name__ == "__main__":
    generate_pdfs()
