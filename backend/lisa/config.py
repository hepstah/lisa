from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    dev_mode: bool = True
    db_path: str = "lisa.db"
    kasa_username: str = ""
    kasa_password: str = ""
    host: str = "0.0.0.0"
    port: int = 8001

    # Phase 2: Voice pipeline
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    stt_model: str = "whisper-1"
    stt_timeout: float = 3.0
    llm_model: str = "claude-haiku-4-5"
    llm_timeout: float = 3.0
    tts_model_path: str = ""
    tts_output_dir: str = "tts_output"

    model_config = {"env_prefix": "LISA_", "env_file": ".env"}


settings = Settings()
