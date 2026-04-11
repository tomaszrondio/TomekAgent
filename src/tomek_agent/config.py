from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    # Slack
    slack_bot_token: str
    slack_app_token: str
    log_level: str = "INFO"
    health_port: int = 3000

    # LLM (OpenRouter)
    openrouter_api_key: str
    llm_model: str = "anthropic/claude-sonnet-4-20250514"
    max_tokens: int = 4096

    # Storage
    data_dir: str = "/app/data"

    # Rate limiting
    rate_limit_per_user: int = 50
