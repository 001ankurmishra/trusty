"""
FR-05/FR-06: text vs scanned PDF detection, text extraction, local OCR (Tesseract).
Requires the `tesseract-ocr` system binary installed locally (see README).
"""
import fitz  # PyMuPDF
import pytesseract
from PIL import Image
import io
import docx as docx_lib
import openpyxl


def parse_pdf(filepath: str):
    """Returns list of {page, text, ocr_used, confidence_flag}"""
    doc = fitz.open(filepath)
    pages = []
    for i, page in enumerate(doc):
        text = page.get_text().strip()
        ocr_used = False
        low_confidence = False
        if len(text) < 20:  # likely scanned page -> OCR fallback
            pix = page.get_pixmap(dpi=200)
            img = Image.open(io.BytesIO(pix.tobytes("png")))
            try:
                data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
                words = [w for w in data["text"] if w.strip()]
                confs = [int(c) for c, w in zip(data["conf"], data["text"]) if w.strip() and c != "-1"]
                text = " ".join(words)
                avg_conf = sum(confs) / len(confs) if confs else 0
                low_confidence = avg_conf < 60
                ocr_used = True
            except Exception as e:
                text = f"[OCR failed: {e}]"
                low_confidence = True
        pages.append({"page": i + 1, "text": text, "ocr_used": ocr_used, "low_confidence": low_confidence})
    doc.close()
    return pages


def parse_image(filepath: str):
    img = Image.open(filepath)
    data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
    words = [w for w in data["text"] if w.strip()]
    confs = [int(c) for c, w in zip(data["conf"], data["text"]) if w.strip() and c != "-1"]
    text = " ".join(words)
    avg_conf = sum(confs) / len(confs) if confs else 0
    return [{"page": 1, "text": text, "ocr_used": True, "low_confidence": avg_conf < 60}]


def parse_docx(filepath: str):
    d = docx_lib.Document(filepath)
    text = "\n".join(p.text for p in d.paragraphs)
    return [{"page": 1, "text": text, "ocr_used": False, "low_confidence": False}]


def parse_xlsx(filepath: str):
    wb = openpyxl.load_workbook(filepath, data_only=True)
    chunks = []
    for i, ws in enumerate(wb.worksheets):
        rows = []
        for row in ws.iter_rows(values_only=True):
            rows.append(" | ".join(str(c) for c in row if c is not None))
        chunks.append({"page": i + 1, "text": f"Sheet: {ws.title}\n" + "\n".join(rows), "ocr_used": False, "low_confidence": False})
    return chunks


def parse_txt(filepath: str):
    with open(filepath, "r", errors="ignore") as f:
        return [{"page": 1, "text": f.read(), "ocr_used": False, "low_confidence": False}]


def parse_document(filepath: str, file_type: str):
    ft = file_type.lower()
    if ft == "pdf":
        return parse_pdf(filepath)
    if ft in ("png", "jpg", "jpeg"):
        return parse_image(filepath)
    if ft == "docx":
        return parse_docx(filepath)
    if ft == "xlsx":
        return parse_xlsx(filepath)
    return parse_txt(filepath)
