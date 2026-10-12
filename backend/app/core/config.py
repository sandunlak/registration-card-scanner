"""Application settings loaded from environment / .env file."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Database
    database_url: str = "sqlite+aiosqlite:///./data/db/app.db"

    # Image storage
    images_dir: str = "./data/images"
    max_upload_size_mb: int = 20
    allowed_mime_types: str = "image/jpeg,image/png,image/webp,image/tiff"

    # Privacy
    image_retention_days: int = 90

    # OCR
    ocr_confidence_threshold: float = 0.75

    # CORS
    allowed_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    # Logging
    log_level: str = "INFO"

    # ── Derived helpers ────────────────────────────────────────────────────
    @property
    def allowed_origins_list(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]

    @property
    def allowed_mime_types_list(self) -> list[str]:
        return [m.strip() for m in self.allowed_mime_types.split(",") if m.strip()]


settings = Settings()
