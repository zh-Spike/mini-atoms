from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "mini-atoms"
    database_url: str = "sqlite:///./mini_atoms.db"

    llm_base_url: str = "https://cf.api.fan/v1"
    llm_api_key: str = ""
    llm_model: str = "deepseek-flash"
    # Sends `thinking: {type: disabled}` (DeepSeek-style); much faster first token for codegen.
    llm_disable_thinking: bool = True
    # Comma-separated models (same gateway) users can pick 2-3 of for a race; `llm_model` is
    # always offered too.
    llm_race_models: str = "glm-5.3-flashx,glm-5.3,grok-4.7"

    secret_key: str = "dev-secret-change-me"
    # Comma-separated "CODE:max_uses" pairs, e.g. "ROOT2026:50,DEMO:10".
    invite_codes: str = "DEMO:100"
    # AI runs allowed per account.
    user_generation_limit: int = 30


@lru_cache
def get_settings() -> Settings:
    return Settings()
