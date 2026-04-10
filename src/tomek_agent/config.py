from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    slack_bot_token: str
    slack_app_token: str
    log_level: str = "INFO"
    health_port: int = 3000
