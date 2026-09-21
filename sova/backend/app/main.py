import threading
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .core.db import init_db
from .core.security_monitor import install_network_guard
from .routers import auth_router, projects_router, documents_router, tasks_router, misc_router

install_network_guard()  # must run before anything else touches sockets
init_db()

app = FastAPI(title="TrustForge", version="0.2.0-mvp")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router.router)
app.include_router(projects_router.router)
app.include_router(documents_router.router)
app.include_router(tasks_router.router)
app.include_router(misc_router.router)


@app.get("/")
def root():
    from .core import security_monitor
    counters = security_monitor.get_counters()
    return {
        "status": "TrustForge backend running",
        "blocked_attempts": counters["blocked_attempts"],
        "external_calls_succeeded": counters["external_calls_succeeded"],
        "air_gapped": counters["external_calls_succeeded"] == 0,
    }


def _warmup():
    """Background warm-up: pre-load embedding model + send a 1-token request to each Ollama model."""
    import logging
    log = logging.getLogger("trustforge.warmup")
    try:
        log.info("Warm-up: loading embedding model…")
        from .tools.rag_store import _get_embedder
        _get_embedder()
        log.info("Warm-up: embedding model ready.")
    except Exception as e:
        log.warning(f"Warm-up: embedding model failed: {e}")

    try:
        from .agent.llm_client import warmup_model
        from .core.config import settings
        for model in [settings.REASONING_MODEL, settings.CODING_MODEL, settings.VISION_MODEL]:
            log.info(f"Warm-up: pinging {model}…")
            warmup_model(model)
        log.info("Warm-up: all models pinged.")
    except Exception as e:
        log.warning(f"Warm-up: model ping failed: {e}")


@app.on_event("startup")
async def startup_warmup():
    """Launch warm-up in a background thread so it doesn't block server startup."""
    t = threading.Thread(target=_warmup, daemon=True, name="trustforge-warmup")
    t.start()
