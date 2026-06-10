from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str = "postgresql://mlops_user:mlops_pass@postgres:5432/pfi"
    minio_url:    str = "http://minio:9000"

settings = Settings()
