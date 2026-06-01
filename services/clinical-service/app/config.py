from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str = "postgresql://clinical_user:clinical_pass@postgres:5432/pfi"
    secret_key: str = "dev-secret-key-cambiar-en-produccion"
    algorithm: str = "HS256"

settings = Settings()
