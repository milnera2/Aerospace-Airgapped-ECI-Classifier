"""
app.py — Streamlit entry point for the air-gapped ECI classification workflow.

Browser-based local UI that visualizes each agent step and never sends data off-host.
Accepts PDF uploads or plain technical descriptions.
"""

import os
import sys
import json
import tempfile
import streamlit as st

# Ensure project root is on the path so package imports resolve
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.pipeline import orchestrate_classification, DualUseGuardrailTriggered
from utils.pdf_extractor import extract_text_from_pdf
from config.settings import DEFAULT_USML_REFERENCE, DEFAULT_CCL_REFERENCE

TEST_PDFS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_pdfs")

TEST_CASES = {
    "Commercial Baseline (EAR / Civil Aircraft)": {
        "filename": "commercial_baseline.pdf",
        "description": (
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
        "expected": "EAR (Commercial). Likely 9A991 or EAR99 for civil transport part. No ITAR claim expected.",
    },
    "Defense Article (ITAR / Military Aircraft)": {
        "filename": "defense_article.pdf",
        "description": (
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
        "expected": "ITAR (Defense). USML Category VIII (military aircraft parts / 22 CFR 121). High confidence citation expected.",
    },
    "Dual-Use Edge Case (Composite Strut)": {
        "filename": "dual_use_edge_case.pdf",
        "description": (
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
        "expected": "HALTED — Dual-use edge case. Guardrail triggers manual human review. No CUI banner generated.",
    },
}


def format_json_block(data: object) -> str:
    """Return a pretty-printed JSON string for display."""
    try:
        return json.dumps(data, indent=2)
    except Exception as e:
        return f"Error serializing output: {str(e)}"


def load_reference_files(uploaded_files) -> tuple:
    """Extract USML and CCL reference text from uploaded .txt files."""
    usml_ref = None
    ccl_ref = None

    if uploaded_files:
        for uploaded_file in uploaded_files:
            if not uploaded_file.name.lower().endswith(".txt"):
                continue
            try:
                content = uploaded_file.read().decode("utf-8")
                name = uploaded_file.name.lower()
                if "usml" in name:
                    usml_ref = content
                elif "ccl" in name:
                    ccl_ref = content
            except Exception:
                pass

    return usml_ref, ccl_ref


def run_pipeline(raw_document_text, usml_ref, ccl_ref):
    """Execute the pipeline with progress indicators and return (result, guardrail_error)."""
    pipeline_result = None
    guardrail_error = None

    # Progress indicators
    progress_bar = st.progress(0)
    status_text = st.empty()

    stages = [
        ("Reading PDF", 0),
        ("Agent 1 — Technical Extractor", 25),
        ("Agent 2 — Legal Cross-Referencer", 50),
        ("Agent 3 — Compliance Marking Generator", 75),
        ("Complete", 100),
    ]

    def update_progress(label, pct):
        progress_bar.progress(pct)
        status_text.text(f"Status: {label}")

    try:
        update_progress("Reading PDF", 0)

        pipeline_result = orchestrate_classification(
            raw_document_text,
            usml_ref=usml_ref,
            ccl_ref=ccl_ref,
            step_callback=lambda event_type, message_text, payload: update_progress(
                message_text, _stage_pct(event_type)
            ),
        )

        status_text.text("Status: Complete")
        progress_bar.progress(100)
    except DualUseGuardrailTriggered as e:
        guardrail_error = e
        status_text.text("Status: Halted — Manual Review Required")
        progress_bar.progress(50)
    except Exception as e:
        st.error(f"Pipeline execution failed: {str(e)}")
        st.caption("Verify Ollama is running locally (`ollama serve`) and `llama3.1` is pulled.")
        return None, None

    return pipeline_result, guardrail_error


def _stage_pct(event_type: str) -> int:
    """Map orchestration callback event types to progress percentages."""
    mapping = {
        "extractor_start": 25,
        "extractor_done": 25,
        "legal_start": 50,
        "legal_done": 50,
        "marking_start": 75,
        "marking_done": 100,
        "guardrail_halt": 50,
    }
    return mapping.get(event_type, 0)


def display_results(pipeline_result, guardrail_error):
    """Render pipeline results to the Streamlit UI."""
    status = pipeline_result.get("status", "IN_PROGRESS")

    st.divider()
    st.subheader("2. Pipeline Results")

    # Hard Stop branch
    if status == "HALTED_FOR_HUMAN_REVIEW" or guardrail_error is not None:
        st.error("WORKFLOW HALTED — Manual Human Review Required")
        if guardrail_error:
            st.write(f"Reason: {guardrail_error}")
        details = pipeline_result.get("guardrail_details", {})
        if details:
            with st.expander("Conflicting Guidelines / Dual-Use Analysis", expanded=True):
                st.json(details)
        st.warning(
            "No CUI banner was generated. This item must be reviewed by an authorized "
            "Export Control Officer before any export determination is made."
        )
    else:
        # Agent 1: Technical Extractor
        st.markdown("### Agent 1 — Technical Extractor")
        if pipeline_result.get("extractor_output"):
            with st.expander("View structured specifications JSON", expanded=True):
                st.json(pipeline_result["extractor_output"])
        else:
            st.info("Extractor output not available.")

        # Agent 2: Legal Cross-Referencer
        st.markdown("### Agent 2 — Legal Cross-Referencer")
        if pipeline_result.get("legal_output"):
            legal = pipeline_result["legal_output"]
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Jurisdiction", legal.get("jurisdiction", "N/A"))
            with col2:
                st.metric("Confidence", f"{float(legal.get('confidence_score', 0)):.2f}")
            with col3:
                st.metric("Dual-Use Flag", str(legal.get("is_dual_use", False)))

            st.markdown("#### Statutory Citations")
            citations = legal.get("citations", []) or []
            if citations:
                for c in citations:
                    st.markdown(
                        f"- **{c.get('code', 'N/A')}**: {c.get('applicability', '')}"
                    )
            else:
                st.info("*No citations returned*")

            st.markdown("#### Reasoning")
            st.write(legal.get("reasoning", "N/A"))

            if legal.get("conflicting_guidelines"):
                with st.expander("Conflicting Guidelines"):
                    st.write(legal["conflicting_guidelines"])
        else:
            st.info("Legal cross-referencer output not available.")

        # Agent 3: Compliance Marking Generator
        st.markdown("### Agent 3 — CUI Compliance Markings")
        if pipeline_result.get("marking_output"):
            with st.expander("View CUI banner and markings JSON", expanded=True):
                st.json(pipeline_result["marking_output"])
        else:
            st.info("No CUI markings generated (pipeline was halted or incomplete).")

    st.success("Classification complete.")


def main():
    st.set_page_config(
        page_title="ECI Classification — Air-Gapped Multi-Agent Workflow",
        layout="wide",
    )

    st.title("ECI Classification — ITAR / EAR")
    st.markdown(
        "Air-gapped, multi-agent workflow for Export Controlled Information (ECI) classification. "
        "All LLM execution runs strictly on localhost via Ollama (Llama 3.1). No cloud APIs."
    )

    # ---- Sidebar: configuration ----
    with st.sidebar:
        st.header("Configuration")
        st.info("Ollama must be running locally (`ollama serve`) with `llama3.1` pulled.")
        st.divider()
        st.subheader("Legal Reference Files (optional)")
        st.caption("Upload .txt files containing custom USML / CCL reference text.")
        ref_files = st.file_uploader(
            "USML / CCL reference text files",
            type=["txt"],
            accept_multiple_files=True,
            help="Name files with 'usml' or 'ccl' in the filename (e.g. usml_reference.txt)",
        )

    # ---- Main input area ----
    st.subheader("1. Input Technical Specification")
    input_method = st.radio(
        "Choose input method:",
        ["Paste technical description", "Upload PDF", "Test demo PDF"],
        horizontal=True,
    )

    raw_document_text = ""

    # Test demo PDF section
    if input_method == "Test demo PDF":
        st.markdown("#### Select a test PDF to load and run through the pipeline:")
        selected_label = st.selectbox(
            "Test case:",
            options=list(TEST_CASES.keys()),
        )
        test_case = TEST_CASES[selected_label]
        test_pdf_path = os.path.join(TEST_PDFS_DIR, test_case["filename"])

        col_demo1, col_demo2 = st.columns([3, 1])
        with col_demo1:
            st.info(f"Expected outcome: {test_case['expected']}")
        with col_demo2:
            load_demo = st.button("Load Test PDF", use_container_width=True)

        if load_demo:
            if os.path.exists(test_pdf_path):
                try:
                    raw_document_text = extract_text_from_pdf(test_pdf_path)
                    if raw_document_text:
                        st.success(f"Loaded {test_case['filename']} — {len(raw_document_text)} characters extracted.")
                        st.session_state["raw_document_text"] = raw_document_text
                    else:
                        st.error("No text could be extracted from the test PDF.")
                except Exception as e:
                    st.error(f"Failed to load test PDF: {str(e)}")
            else:
                st.error(f"Test PDF not found at {test_pdf_path}. Run generate_test_pdfs.py first.")

        # Use session state text if available (persists across reruns)
        if not raw_document_text and "raw_document_text" in st.session_state:
            raw_document_text = st.session_state["raw_document_text"]

    elif input_method == "Upload PDF":
        pdf_file = st.file_uploader(
            "Upload PDF technical specification",
            type=["pdf"],
            help="PyMuPDF extracts text; Tesseract OCR is used as fallback for scanned pages.",
        )
        if pdf_file is not None:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                tmp.write(pdf_file.read())
                tmp_path = tmp.name
            try:
                raw_document_text = extract_text_from_pdf(tmp_path)
            finally:
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass
            if raw_document_text:
                st.success(f"Extracted {len(raw_document_text)} characters from PDF.")
            else:
                st.warning("No text could be extracted from the PDF.")
    else:
        raw_document_text = st.text_area(
            "Paste technical description / engineering datasheet:",
            height=300,
            placeholder="Enter component name, part designation, materials, mechanical parameters, operational envelope, etc.",
        )

    # ---- Run classification ----
    st.divider()

    # Track whether the pipeline is currently running so the button can be
    # greyed out (disabled) while a classification is in flight.
    if "pipeline_running" not in st.session_state:
        st.session_state["pipeline_running"] = False

    run_button = st.button(
        "Run Classification Pipeline",
        type="primary",
        use_container_width=True,
        disabled=st.session_state["pipeline_running"],
    )

    # Button clicked: validate input, then mark the pipeline as running and
    # rerun so the button is visually greyed out during execution.
    if run_button and not st.session_state["pipeline_running"]:
        if not raw_document_text.strip():
            # Show the submission-needed error without rerunning so the
            # banner stays visible to the user.
            st.error("Data Submission Needed — Please paste a technical description, upload a PDF, or load a test demo PDF before running the pipeline.")
        else:
            st.session_state["pipeline_running"] = True
            st.rerun()

    # Pipeline is running: execute it, then reset the flag and rerun to
    # re-enable the button and surface the results.
    if st.session_state["pipeline_running"]:
        # Load reference text
        usml_ref, ccl_ref = load_reference_files(ref_files)
        if usml_ref is None:
            usml_ref = DEFAULT_USML_REFERENCE
        if ccl_ref is None:
            ccl_ref = DEFAULT_CCL_REFERENCE

        # ---- Execute pipeline ----
        pipeline_result, guardrail_error = run_pipeline(
            raw_document_text, usml_ref, ccl_ref
        )

        if pipeline_result is None:
            st.session_state["pipeline_running"] = False
            st.rerun()

        # Store in session state for persistence across reruns
        st.session_state["pipeline_result"] = pipeline_result
        st.session_state["guardrail_error"] = guardrail_error

        # Pipeline finished: re-enable the button.
        st.session_state["pipeline_running"] = False
        st.rerun()

    # ---- Display persisted results ----
    if "pipeline_result" in st.session_state:
        pipeline_result = st.session_state["pipeline_result"]
        guardrail_error = st.session_state.get("guardrail_error")
        display_results(pipeline_result, guardrail_error)


if __name__ == "__main__":
    main()
