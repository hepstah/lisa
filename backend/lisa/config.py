from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    dev_mode: bool = True
    db_path: str = "lisa.db"
    kasa_username: str = ""
    kasa_password: str = ""
    host: str = "0.0.0.0"
    port: int = 8001

    model_config = {"env_prefix": "LISA_", "env_file": ".env"}


settings = Settings()
