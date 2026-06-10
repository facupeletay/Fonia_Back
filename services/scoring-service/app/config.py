from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str = "postgresql://scoring_user:scoring_pass@postgres:5432/pfi"
    redis_url:    str = "redis://redis:6379/0"
    minio_url:    str = "http://minio:9000"

settings = Settings()
