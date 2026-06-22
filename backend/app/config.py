from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    data_dir: Path = Path("./data")
    database_url: str = "sqlite:///./data/gridlock.db"
    retrain_delay_s: float = 2.0
    cors_origins: list[str] = ["http://localhost:5173"]
    predictor: str = "spectral"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
