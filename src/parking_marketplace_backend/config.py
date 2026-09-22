from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    postgres_db: str
    postgres_user: str
    postgres_password: str
    database_url: str

    model_config = SettingsConfigDict(env_file=".env")


def get_settings():
    return Settings()