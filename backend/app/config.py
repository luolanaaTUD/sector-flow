from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    DATABASE_URL: str = "postgresql+psycopg://sector_flow:sector_flow@localhost:5432/sector_flow"
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    COLLECTOR_ENABLED: bool = True
    SECTOR_TYPES: str = "industry,concept"
    AKSHARE_REQUEST_DELAY: float = 2.0

    @property
    def sector_type_list(self) -> list[str]:
        return [s.strip() for s in self.SECTOR_TYPES.split(",") if s.strip()]


settings = Settings()
