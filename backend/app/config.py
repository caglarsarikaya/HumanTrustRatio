from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application-wide settings loaded from environment / .env file."""

    gemini_api_key: str = ""
    serpapi_api_key: str = ""
    search_engine: str = "duckduckgo"  # "duckduckgo" or "serpapi"
    app_title: str = "Verifolio"
    debug: bool = True

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
