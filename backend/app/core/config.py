from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolve absolute path to backend/.env
ENV_FILE = Path(__file__).resolve().parent.parent.parent / ".env"


class Settings(BaseSettings):
    PROJECT_NAME: str = "Pharmacy Substitution Decision Support System"
    DATABASE_URL: str = (
        "postgresql+psycopg://postgres:YOUR_PASSWORD@localhost:5432/pharmacy_substitution_db"
    )

    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
