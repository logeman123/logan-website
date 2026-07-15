from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    service_token: str = "dev-token"
    content_url: str = "http://localhost:8001"
    llm_provider: str = "fake"          # "anthropic" | "fake"
    llm_api_key: str = ""
    llm_base_url: str = ""              # e.g. the Vercel AI Gateway endpoint
    llm_model: str = "claude-haiku-4-5-20251001"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
