import requests
from ..core.config import settings


class LLMError(Exception):
    """Raised when the local Ollama model call fails (connection, timeout, model not found, etc.)."""
    pass


def generate(model: str, prompt: str, system: str = "", max_tokens: int = 500) -> dict:
    """
    Call local Ollama server. Never touches the internet.
    Returns a dict: {"text": str, "truncated": bool, "done_reason": str}
    Raises LLMError on failure.
    """
    try:
        resp = requests.post(
            f"{settings.OLLAMA_URL}/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "system": system,
                "stream": False,
                "keep_alive": "30m",
                "options": {"num_predict": max_tokens, "temperature": 0.2, "num_ctx": 4096},
            },
            timeout=300,
        )
        resp.raise_for_status()
        data = resp.json()
        text = data.get("response", "").strip()
        done_reason = data.get("done_reason", "")
        truncated = done_reason == "length"
        if truncated:
            text += "\n\n[Note: Output was truncated due to token limit.]"
        return {"text": text, "truncated": truncated, "done_reason": done_reason}
    except requests.exceptions.ConnectionError:
        raise LLMError(
            f"Could not reach local Ollama server at {settings.OLLAMA_URL}. "
            f"Run `ollama serve` and pull the required models (see README)."
        )
    except Exception as e:
        raise LLMError(f"Local model call failed: {e}")


def generate_text(model: str, prompt: str, system: str = "", max_tokens: int = 500) -> str:
    """Convenience wrapper that returns just the text string. Raises LLMError on failure."""
    return generate(model, prompt, system, max_tokens)["text"]


def vision_generate(model: str, prompt: str, image_b64: str, max_tokens: int = 512) -> str:
    """Call vision model with a base64-encoded image. Raises LLMError on failure."""
    try:
        resp = requests.post(
            f"{settings.OLLAMA_URL}/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "images": [image_b64],
                "stream": False,
                "keep_alive": "30m",
                "options": {"num_predict": max_tokens, "temperature": 0.2},
            },
            timeout=300,
        )
        resp.raise_for_status()
        return resp.json().get("response", "").strip()
    except requests.exceptions.ConnectionError:
        raise LLMError(f"Could not reach Ollama for vision model at {settings.OLLAMA_URL}.")
    except Exception as e:
        raise LLMError(f"Local vision model call failed: {e}")


def list_local_models():
    try:
        resp = requests.get(f"{settings.OLLAMA_URL}/api/tags", timeout=5)
        resp.raise_for_status()
        return [m["name"] for m in resp.json().get("models", [])]
    except Exception:
        return []


def warmup_model(model: str):
    """Send a minimal generate request to pre-load a model into memory."""
    try:
        requests.post(
            f"{settings.OLLAMA_URL}/api/generate",
            json={
                "model": model,
                "prompt": "hi",
                "stream": False,
                "keep_alive": "30m",
                "options": {"num_predict": 1},
            },
            timeout=120,
        )
    except Exception:
        pass
