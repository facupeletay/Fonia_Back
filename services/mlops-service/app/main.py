from fastapi import FastAPI
from app.database import Base, engine

Base.metadata.create_all(bind=engine)

app = FastAPI(title="mlops-service", version="0.1.0", root_path="/api/mlops")

@app.get("/health")
def health():
    return {"status": "ok", "service": "mlops-service"}
