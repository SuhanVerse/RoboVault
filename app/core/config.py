from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "RoboVault"
    api_v1_prefix: str = "/api/v1"

    database_url: str = (
        "postgresql+psycopg2://robovault:robovault@localhost:5433/robovault"
    )
    secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
