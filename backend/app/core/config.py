from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    app_name: str = "SalesIA Enterprise"
    app_env: str = "development"

    database_url: str

    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60

    # Orígenes CORS permitidos, separados por coma. En producción debe
    # incluir la URL del frontend desplegado (p. ej. la de Render).
    cors_origins: str = (
        "http://localhost:5173,"
        "http://127.0.0.1:5173,"
        "http://localhost:5174,"
        "http://127.0.0.1:5174"
    )

    @property
    def cors_origins_list(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.cors_origins.split(",")
            if origin.strip()
        ]

    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


settings = Settings()