from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str = "postgresql://identity_user:identity_pass@postgres:5432/pfi"
    redis_url: str = "redis://redis:6379/0"
    secret_key: str = "dev-secret-key-cambiar-en-produccion"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7

settings = Settings()