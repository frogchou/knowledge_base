from functools import lru_cache
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        extra="ignore",
    )

    database_url: str = Field("sqlite+aiosqlite:///./app.db", alias="DATABASE_URL")
    qdrant_url: str = Field("http://localhost:6333", alias="QDRANT_URL")
    qdrant_api_key: str | None = Field(None, alias="QDRANT_API_KEY")
    embedding_dim: int = Field(1536, alias="EMBEDDING_DIM")

    jwt_secret: str = Field("changeme", alias="JWT_SECRET")
    jwt_expire_minutes: int = Field(60, alias="JWT_EXPIRE_MINUTES")

    allow_anonymous_read: bool = Field(True, alias="ALLOW_ANONYMOUS_READ")
    upload_dir: str = Field("/data/uploads", alias="UPLOAD_DIR")

    openai_api_key: str | None = Field(None, alias="OPENAI_API_KEY")
    openai_model: str = Field("gpt-3.5-turbo", alias="OPENAI_MODEL")

    admin_username: str | None = Field(None, alias="auth__admin_username")
    admin_password: str | None = Field(None, alias="auth__admin_password")


@lru_cache()
def get_settings() -> Settings:
    return Settings()  # type: ignore[arg-type]


settings = get_settings()
