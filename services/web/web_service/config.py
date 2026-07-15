from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    service_token: str = "dev-token"
    content_url: str = "http://localhost:8001"
    ai_url: str = "http://localhost:8002"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
