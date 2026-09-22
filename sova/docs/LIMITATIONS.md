# TrustForge System Limitations

TrustForge is a powerful AI decision-support system, but it is **not** a replacement for human judgment. Understanding its limitations is critical for safe and effective deployment in industrial environments.

## 1. Decision Support Only
- **Human Approval is Mandatory:** The system is explicitly designed to be "fail-closed". If it cannot definitively determine compliance, it will mark the item as `NEEDS_REVIEW`.
- Even when the system marks an item as `PASS` or `FAIL`, a qualified human Reviewer must verify the extraction and logic before finalizing the document.

## 2. OCR and Scanned Document Constraints
- TrustForge uses Tesseract OCR for scanned PDFs and images. Poor scan quality, handwriting, low contrast, or skewed pages can result in missing or hallucinated text.
- Highly complex tables (e.g., nested tables or tables spanning multiple pages) may lose their structural context during extraction, leading to inaccurate parameter mapping.

## 3. Large Language Model (LLM) Capabilities
- **Hallucinations:** While the system includes strict grounding checks (ensuring extracted numbers actually exist in the source text), LLMs can still occasionally misinterpret the association between a parameter name and a value.
- **Context Windows:** The system uses a finite context window (e.g., 4096 tokens). Extremely large documents may be truncated, resulting in missed rules or measurements at the end of the document.

## 4. Hardware Limitations
- TrustForge is tuned to run on a standard 16GB RAM laptop using quantized models (e.g., 3B parameter models). These smaller models are faster and use less memory, but they do not possess the complex reasoning capabilities of frontier models like GPT-4 or Claude 3.5 Sonnet.
- As a result, prompts and documents must be kept relatively straightforward.

## 5. Unit Conversion Scope
- The compliance engine (`compliance.py`) currently supports a limited set of unit conversions (e.g., Pressure: psi, bar, kpa; Length: mm, in, cm; Temperature: C, F). 
- Custom or highly specialized units will default to `unknown` and trigger a manual review.
