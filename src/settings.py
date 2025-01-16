import os
from pydantic_settings import BaseSettings, SettingsConfigDict
import pathlib


class Settings(BaseSettings):
    TG_KEY: str
    DATABASE_SQLITE_NAME: str
    GIGACHAT_KEY: str
    
    model_config = SettingsConfigDict(
        env_file=f"{pathlib.Path(__file__).resolve().parent}/.env"
    )

    def get_db_url(self):
        # return f'sqlite+aiosqlite://{os.path.abspath(os.path.join(os.path.dirname(__file__), "..", f"{self.DATABASE_SQLITE_NAME}.db"))}'
        return f'sqlite+aiosqlite:///{self.DATABASE_SQLITE_NAME}.db'

        
settings = Settings()
