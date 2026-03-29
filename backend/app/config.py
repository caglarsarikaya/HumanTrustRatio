from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application-wide settings loaded from environment / .env file."""

    gemini_api_key: str = ""
    app_title: str = "Proof of Humanity"
    debug: bool = True

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
