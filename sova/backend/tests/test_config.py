import pytest
import os
from app.core.config import Settings

def test_config_rejects_weak_secret_in_prod(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("SECRET_KEY", "sova-local-dev-secret-change-me")
    with pytest.raises(ValueError, match="MUST provide a strong, unique SECRET_KEY"):
        Settings()

def test_config_rejects_short_secret_in_prod(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("SECRET_KEY", "short")
    with pytest.raises(ValueError, match="MUST provide a strong, unique SECRET_KEY"):
        Settings()

def test_config_allows_weak_secret_in_dev(monkeypatch):
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("SECRET_KEY", "sova-local-dev-secret-change-me")
    settings = Settings()
    assert settings.APP_ENV == "development"
