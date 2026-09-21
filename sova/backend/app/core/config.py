import os

# --- Air-gap: set offline flags BEFORE any HuggingFace/transformers import ---
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class Settings:
    APP_ENV = os.getenv("APP_ENV", "development")
    SECRET_KEY = os.getenv("SECRET_KEY", "sova-local-dev-secret-change-me")
    ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES = 480

    DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR}/storage/sova.db")
    CHROMA_DIR = os.getenv("CHROMA_DIR", f"{BASE_DIR}/storage/chroma")
    ARTIFACT_DIR = os.getenv("ARTIFACT_DIR", f"{BASE_DIR}/storage/artifacts")
    UPLOAD_DIR = os.getenv("UPLOAD_DIR", f"{BASE_DIR}/uploads")

    # Ollama endpoints - all local, no cloud calls ever
    OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
    REASONING_MODEL = os.getenv("REASONING_MODEL", "qwen2.5:3b-instruct")
    CODING_MODEL = os.getenv("CODING_MODEL", "qwen2.5-coder:1.5b")
    VISION_MODEL = os.getenv("VISION_MODEL", "moondream")
    EMBED_MODEL_LOCAL = os.getenv("EMBED_MODEL_LOCAL", "all-MiniLM-L6-v2")  # sentence-transformers, CPU-friendly

    MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "50"))
    SANDBOX_TIMEOUT_SECONDS = int(os.getenv("SANDBOX_TIMEOUT_SECONDS", "15"))
    OUTBOUND_NETWORK = os.getenv("OUTBOUND_NETWORK", "false").lower() == "true"

    # Minimum password length for registration
    MIN_PASSWORD_LENGTH = int(os.getenv("MIN_PASSWORD_LENGTH", "8"))

    # RAG distance threshold for grounded verification
    RAG_DISTANCE_THRESHOLD = float(os.getenv("RAG_DISTANCE_THRESHOLD", "1.2"))

    ALLOWED_HOSTS = ["localhost", "127.0.0.1"]

settings = Settings()

os.makedirs(settings.CHROMA_DIR, exist_ok=True)
os.makedirs(settings.ARTIFACT_DIR, exist_ok=True)
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
os.makedirs(os.path.dirname(settings.DATABASE_URL.replace("sqlite:///", "")), exist_ok=True)
