# Aerospace-Airgapped-ECI-Classifier

A secure, locally hosted multi-agent AI system designed to assist Export Control Officers in classifying aerospace components under ITAR (defense) or EAR (commercial) regulations.

By executing strictly on-premises using **Ollama** and **Streamlit**, this workflow eliminates the federal compliance violations associated with cloud APIs. The system utilizes a specialized, three-agent architecture (Technical Extractor, Legal Cross-Referencer, and Compliance Marking Generator) to evaluate mechanical specifications against ITAR and EAR frameworks, ensuring high accuracy while actively preventing automation bias and false negatives through hard-coded human intervention triggers.

---

## Security Constraints (Mandatory)

| Constraint | Requirement |
|------------|-------------|
| **Air-Gapped Runtime** | All LLM execution occurs on `localhost` via Ollama. No cloud APIs (OpenAI, Anthropic, etc.) are permitted. |
| **Data Sovereignty** | Ingested PDFs and technical descriptions never leave the host machine. Streamlit runs locally in the browser. |
| **No Guessing** | The Legal Cross-Referencer is forbidden from default-guessing. Dual-use ambiguity or missing CFR citations triggers an immediate hard stop for manual human review. |
| **Extractor Isolation** | The Technical Extractor is system-prompt forbidden from making legal determinations (ITAR/EAR/USML/CFR). Only the Cross-Referencer handles legal logic. |

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    USER INPUT (Streamlit UI)                │
│  PDF upload (PyMuPDF / Tesseract OCR) or technical text     │
└─────────────────────┬───────────────────────────────────────┘
                      ▼
┌─────────────────────────────────────────────────────────────┐
│              ORCHESTRATOR (orchestrator.py)                 │
│  Sequential pipeline with hard-stop guardrail enforcement   │
└─────────────────────┬───────────────────────────────────────┘
                      ▼
┌─────────────────────────────────────────────────────────────┐
│  AGENT 1 — Technical Extractor                              │
│  • Ingests raw technical description / PDF text             │
│  • Outputs structured mechanical & operational JSON         │
│  • STRICTLY FORBIDDEN from making legal claims              │
└─────────────────────┬───────────────────────────────────────┘
                      ▼
┌─────────────────────────────────────────────────────────────┐
│  AGENT 2 — Legal Cross-Referencer                           │
│  • Maps specs against USML (22 CFR Part 121) & CCL          │
│    (15 CFR Part 774) reference text                         │
│  • Outputs jurisdiction hypothesis + CFR citations          │
│  • GUARDRAIL CHECK:                                         │
│    - Dual-use flag? → HARD STOP                             │
│    - Confidence < 0.75? → HARD STOP                         │
│    - Missing/invalid citations? → HARD STOP                 │
│  • Never guesses; halts for manual human review             │
└─────────────────────┬───────────────────────────────────────┘
                      ▼  (only if unambiguous)
┌─────────────────────────────────────────────────────────────┐
│  AGENT 3 — Compliance Marking Generator                     │
│  • Generates exact CUI banner formatting                    │
│  • 32 CFR Part 2002 / DoD 5200.48 / ITAR & EAR warnings     │
└─────────────────────┬───────────────────────────────────────┘
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                    CUI BANNER (Streamlit UI)                │
└─────────────────────────────────────────────────────────────┘
```

### Agent Roles

| Agent | Responsibility | Legal Authority? | Output |
|-------|---------------|------------------|--------|
| **Technical Extractor** | Extracts mechanical/operational specs from raw text or PDF | ❌ Forbidden from legal claims | Structured JSON (part name, materials, loads, envelope, etc.) |
| **Legal Cross-Referencer** | Cross-references specs against USML / CCL | ✅ Yes — export control analysis | Jurisdiction hypothesis, CFR citations, confidence score |
| **Compliance Marking Generator** | Generates CUI banner & statutory warning markings | ✅ Yes — compliance markings only | CUI control block, header/footer, statutory warning statement |

### Guardrail & Stop Rules

The orchestrator enforces a **hard stop** if any of the following occur after Agent 2:

1. **Dual-use flag** (`is_dual_use: true`) — item shared between military defense and civil platforms.
2. **Indeterminate jurisdiction** — result is `DUAL_USE`, `UNCERTAIN`, `AMBIGUOUS`, or `UNKNOWN`.
3. **Low confidence** — `confidence_score < 0.75`.
4. **Missing or invalid citations** — no verifiable `22 CFR` / `15 CFR` citation returned.

When triggered, the autonomous loop halts immediately, the conflicting guidelines are surfaced for manual human review, and **no CUI banner is generated** to prevent false negatives.

---

## File Inventory

```
aerospace-airgapped-eci-classifier/
├── app.py                          # Streamlit entry point
├── test_cases.py                   # Mock test variables: Commercial / Defense / Dual-Use
├── requirements.txt                # Python dependencies for the air-gapped stack
├── README.md                       # This documentation
├── LICENSE
│
├── config/                         # Configuration (Ollama host, model, thresholds)
│   ├── __init__.py
│   └── settings.py                 # OLLAMA_HOST, OLLAMA_MODEL, CONFIDENCE_THRESHOLD,
│                                   # DEFAULT_USML_REFERENCE, DEFAULT_CCL_REFERENCE
│
├── core/                           # Pipeline orchestration & guardrails
│   ├── __init__.py
│   ├── ollama_client.py            # Local Ollama API wrapper (air-gapped localhost only)
│   ├── guardrails.py               # DualUseGuardrailTriggered + evaluate_guardrails()
│   └── pipeline.py                 # orchestrate_classification() — sequential 3-agent flow
│
├── agents/                         # Three distinct agents
│   ├── __init__.py
│   ├── extractor.py                # Technical Extractor (no legal claims)
│   ├── cross_referencer.py         # Legal Cross-Referencer (USML/CCL mapping)
│   └── marking_generator.py        # Compliance Marking Generator (CUI banners)
│
├── utils/                          # Utilities
│   ├── __init__.py
│   └── pdf_extractor.py            # PyMuPDF (fitz) + Tesseract OCR text extraction
│
├── data/                           # Statutory reference text (embedded defaults)
│   ├── usml_reference.txt          # USML — 22 CFR Part 121
│   └── ccl_reference.txt           # CCL — 15 CFR Part 774
│
└── tests/                          # Smoke tests
    ├── __init__.py
    └── test_pipeline.py            # Pipeline validation using test_cases.py
```

| File / Directory | Purpose |
|------------------|---------|
| `app.py` | Streamlit UI entry point — PDF/text input via sidebar and main area, per-agent progress and results display |
| `test_cases.py` | Three mock test variables: Commercial Baseline, Defense Article, Dual-Use Edge Case |
| `requirements.txt` | Python dependencies for the air-gapped stack |
| `config/settings.py` | Ollama host/model/timeout, confidence threshold, default USML/CCL reference text |
| `core/ollama_client.py` | Local Ollama REST client — strictly `127.0.0.1`, no cloud routing |
| `core/guardrails.py` | Hard-stop guardrail enforcement (dual-use, low confidence, missing citations) |
| `core/pipeline.py` | Sequential orchestration: Extractor → Cross-Referencer → Guardrail → Marking Generator |
| `agents/extractor.py` | Technical Extractor Agent — system prompt forbids legal claims |
| `agents/cross_referencer.py` | Legal Cross-Referencer Agent — USML/CCL mapping, citations, confidence |
| `agents/marking_generator.py` | Compliance Marking Generator Agent — CUI banner + statutory warnings |
| `utils/pdf_extractor.py` | PDF text extraction via PyMuPDF, with Tesseract OCR fallback |
| `data/usml_reference.txt` | Default USML statutory reference (22 CFR Part 121) |
| `data/ccl_reference.txt` | Default CCL regulatory reference (15 CFR Part 774) |
| `tests/test_pipeline.py` | Smoke tests validating all three mock cases |
| `README.md` | This documentation |

> **Note:** The original monolithic `orchestrator.py` has been refactored into the modular `core/`, `agents/`, `config/`, and `utils/` packages above. `app.py` imports from the modular structure.

---

## Step-by-Step Setup Guide

### 1. Install Ollama (Local LLM Runtime)

Ollama runs models entirely on your local machine. No external API calls are made.

**Windows:**
1. Download the Ollama installer from https://ollama.com
2. Run the installer and launch Ollama
3. Verify it is running: `ollama serve` (or confirm the Ollama tray icon is active)

**macOS / Linux:**
```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama serve
```

### 2. Pull Llama 3.1 Model

```bash
ollama pull llama3.1
```

Verify the model is available:
```bash
ollama list
```
You should see `llama3.1:latest` in the list.

### 3. Install Tesseract OCR

Tesseract is required for OCR fallback on scanned/image-based PDFs.

**Windows:**
1. Download the Tesseract installer from https://github.com/UB-Mannheim/tesseract/wiki
2. Install and note the installation path (e.g., `C:\Program Files\Tesseract-OCR`)
3. Add `tesseract.exe` to your system PATH, or set the environment variable:
   ```powershell
   $env:TESSERACT_CMD = "C:\Program Files\Tesseract-OCR\tesseract.exe"
   ```

**macOS:**
```bash
brew install tesseract
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt-get update
sudo apt-get install tesseract-ocr
```

### 4. Configure Python Environment

Create a virtual environment and install dependencies:

```bash
# Create virtual environment
python -m venv .venv

# Activate it
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 5. Run the Streamlit Application

```bash
streamlit run app.py
```

The app will start a local browser interface (typically at `http://localhost:8501`).

**Usage:**
1. Upload a PDF technical specification **or** paste a raw technical description into the chat.
2. Optionally upload `.txt` files containing custom USML (`usml*.txt`) or CCL (`ccl*.txt`) reference text.
3. The pipeline runs sequentially through all three agents.
4. Each agent step expands in the UI to show its JSON output:
   - Agent 1: Technical specifications JSON
   - Agent 2: Jurisdiction hypothesis + CFR citations
   - Agent 3: CUI compliance banner and statutory warnings
5. If a dual-use or citation ambiguity is detected, the chain halts and a distinct warning message is displayed for manual human review.

---

## Running the Test Cases

Three mock test variables are provided in `test_cases.py`:

```python
from test_cases import COMMERCIAL_BASELINE, DEFENSE_ARTICLE, DUAL_USE_EDGE_CASE
from orchestrator import orchestrate_classification

# Commercial Baseline — expected EAR / civil aircraft
result, halted = orchestrate_classification(COMMERCIAL_BASELINE["description"])
print(f"Halted: {halted}")

# Defense Article — expected ITAR / military aircraft
result, halted = orchestrate_classification(DEFENSE_ARTICLE["description"])

# Dual-Use Edge Case — expected HARD STOP for manual review
result, halted = orchestrate_classification(DUAL_USE_EDGE_CASE["description"])
assert halted == True  # Guardrail must trigger
```

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OLLAMA_HOST` | `http://127.0.0.1:11434` | Local Ollama API endpoint |
| `OLLAMA_MODEL` | `llama3.1:latest` | Model to use for all agent inference |
| `OLLAMA_TIMEOUT` | `120` | Request timeout in seconds |
| `TESSERACT_CMD` | *(system PATH)* | Path to `tesseract` binary (Windows) |

---

## Compliance Notes

- This system is a **decision-support tool**, not a replacement for an authorized Export Control Officer (ECO).
- All ITAR/EAR determinations must be validated by a qualified compliance professional before any export action is taken.
- The hard-stop guardrails are designed to err on the side of caution: when in doubt, the system halts rather than risk a false negative.
