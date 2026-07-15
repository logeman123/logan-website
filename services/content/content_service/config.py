from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    service_token: str = "dev-token"
    data_dir: Path = Path(__file__).parent / "data" / "projects"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
