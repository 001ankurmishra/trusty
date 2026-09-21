import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import model_validator

# --- Air-gap: set offline flags BEFORE any HuggingFace/transformers import ---
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class Settings(BaseSettings):
    APP_ENV: str = "development"
    SECRET_KEY: str = "sova-local-dev-secret-change-me"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480

    DATABASE_URL: str = f"sqlite:///{BASE_DIR}/storage/sova.db"
    CHROMA_DIR: str = f"{BASE_DIR}/storage/chroma"
    ARTIFACT_DIR: str = f"{BASE_DIR}/storage/artifacts"
    UPLOAD_DIR: str = f"{BASE_DIR}/uploads"

    # Ollama endpoints - all local, no cloud calls ever
    OLLAMA_URL: str = "http://localhost:11434"
    REASONING_MODEL: str = "qwen2.5:3b-instruct"
    CODING_MODEL: str = "qwen2.5-coder:1.5b"
    VISION_MODEL: str = "moondream"
    EMBED_MODEL_LOCAL: str = "all-MiniLM-L6-v2"

    MAX_UPLOAD_MB: int = 50
    SANDBOX_TIMEOUT_SECONDS: int = 15
    OUTBOUND_NETWORK: bool = False

    MIN_PASSWORD_LENGTH: int = 8
    RAG_DISTANCE_THRESHOLD: float = 1.2
    
    ALLOWED_HOSTS: list[str] = ["localhost", "127.0.0.1"]
    
    SIGNING_PRIVATE_KEY_PATH: str = f"{BASE_DIR}/storage/private_key.pem"
    SIGNING_PUBLIC_KEY_PATH: str = f"{BASE_DIR}/storage/public_key.pem"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @model_validator(mode='after')
    def validate_secret_key(self):
        is_default_secret = (self.SECRET_KEY == "sova-local-dev-secret-change-me" or len(self.SECRET_KEY) < 32)
        if self.APP_ENV != "development":
            if is_default_secret:
                raise ValueError("In production (APP_ENV != development), you MUST provide a strong, unique SECRET_KEY (at least 32 characters).")
        else:
            if is_default_secret:
                if "0.0.0.0" in self.ALLOWED_HOSTS or "*" in self.ALLOWED_HOSTS:
                    raise ValueError("Cannot use default SECRET_KEY when binding to external interfaces (0.0.0.0). Set APP_ENV=production and generate a strong SECRET_KEY.")
        return self

settings = Settings()

os.makedirs(settings.CHROMA_DIR, exist_ok=True)
os.makedirs(settings.ARTIFACT_DIR, exist_ok=True)
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
os.makedirs(os.path.dirname(settings.DATABASE_URL.replace("sqlite:///", "")), exist_ok=True)
