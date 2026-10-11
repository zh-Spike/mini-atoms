from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "mini-atoms"
    database_url: str = "sqlite:///./mini_atoms.db"

    llm_base_url: str = "https://cf.api.fan/v1"
    llm_api_key: str = ""
    llm_model: str = "deepseek-flash"
    # Fast mode: sends `thinking: {type: disabled}` (DeepSeek-style) and low reasoning effort
    # (GLM / Grok); much faster first token for codegen. Unsupported params are dropped per model.
    llm_disable_thinking: bool = True
    # Comma-separated models (same gateway) users can pick 2-3 of for a race; `llm_model` is
    # always offered too.
    llm_race_models: str = "glm-5.3-flashx,glm-5.3,grok-4.7"
    # Models called via the Responses API: on this gateway grok-* rejects Chat Completions and
    # glm-5.3 leaks its reasoning into `content` there. Others are detected on the first 400.
    llm_responses_models: str = "glm-5.3,grok-4.7"
    # Demo mode: replay prebuilt apps instead of calling a model. Also on when no API key is set.
    llm_mock: bool = False

    secret_key: str = "dev-secret-change-me"
    # Comma-separated "CODE:max_uses" pairs, e.g. "ROOT2026:50,DEMO:10".
    invite_codes: str = "DEMO:100"
    # AI runs allowed per account.
    user_generation_limit: int = 30
    # Comma-separated usernames that can open the operations dashboard and full prompt traces.
    admin_usernames: str = ""
    # Build commit, shown on the public status page; injected at image build time.
    git_sha: str = "dev"
    # Day boundaries for usage and operations charts.
    stats_timezone: str = "Asia/Shanghai"


@lru_cache
def get_settings() -> Settings:
    return Settings()
