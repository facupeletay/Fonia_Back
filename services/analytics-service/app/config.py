from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str = "postgresql://analytics_user:analytics_pass@postgres:5432/pfi"
    redis_url:    str = "redis://redis:6379/0"

settings = Settings()
