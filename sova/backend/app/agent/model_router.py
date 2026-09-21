"""
FR-09 Model Registry + FR-10 Intelligent Router + FR-11 Hardware-Aware Routing.

Kept as a config-driven table (not hardcoded branching) so new models can be
added without redesigning the app - just edit MODEL_REGISTRY.
"""
import psutil
from ..core.config import settings
from . import llm_client

MODEL_REGISTRY = [
    {
        "name": settings.REASONING_MODEL,
        "type": "reasoning",
        "capabilities": ["reasoning", "qa", "summarization", "planning"],
        "ram_gb_required": 4,
        "priority": 0.9,
    },
    {
        "name": settings.CODING_MODEL,
        "type": "coding",
        "capabilities": ["python", "code", "debugging", "sql"],
        "ram_gb_required": 2,
        "priority": 0.85,
    },
    {
        "name": settings.VISION_MODEL,
        "type": "vision",
        "capabilities": ["image", "ocr_assist", "diagram", "scanned_document"],
        "ram_gb_required": 3,
        "priority": 0.8,
    },
]


def available_ram_gb():
    return round(psutil.virtual_memory().available / (1024 ** 3), 2)


def classify_task(task_text: str, has_image: bool, has_code_request: bool):
    text = task_text.lower()
    if has_image:
        return "vision"
    if has_code_request or any(k in text for k in ["code", "script", "python", "function", "bug", "debug"]):
        return "coding"
    return "reasoning"


def route(task_text: str, has_image: bool = False, has_code_request: bool = False):
    """Returns {selected_model, reason, confidence, fallback_model, model_type}"""
    task_type = classify_task(task_text, has_image, has_code_request)
    candidates = [m for m in MODEL_REGISTRY if m["type"] == task_type]
    if not candidates:
        candidates = [m for m in MODEL_REGISTRY if m["type"] == "reasoning"]

    ram = available_ram_gb()
    installed = llm_client.list_local_models()

    def fits_hardware(m):
        return ram >= m["ram_gb_required"] * 0.5  # generous margin for quantized ggufs

    scored = []
    for m in candidates:
        score = m["priority"]
        score += 0.1 if fits_hardware(m) else -0.3
        score += 0.05 if any(m["name"].split(":")[0] in inst for inst in installed) else -0.1
        scored.append((score, m))
    scored.sort(key=lambda x: -x[0])
    best = scored[0][1]
    fallback_options = [
        m for m in MODEL_REGISTRY
        if m is not best and m["name"] in installed and fits_hardware(m)
    ]
    fallback = fallback_options[0] if fallback_options else best

    # Build reason text — only claim "fits" if RAM check actually passed
    hw_fits = fits_hardware(best)
    hw_note = (
        f"fits on this laptop ({ram} GB available, model requires ~{best['ram_gb_required']} GB)"
        if hw_fits else
        f"tight fit ({ram} GB available, model requires ~{best['ram_gb_required']} GB — may be slow)"
    )

    reason = (
        f"Task classified as '{task_type}' "
        f"({'image input' if has_image else 'code-related' if task_type=='coding' else 'general reasoning/QA'}); "
        f"{hw_note}."
    )

    return {
        "selected_model": best["name"],
        "model_type": task_type,
        "reason": reason,
        "confidence": round(min(0.95, 0.6 + scored[0][0] / 3), 2),
        "fallback_model": fallback["name"],
        "available_ram_gb": ram,
    }
