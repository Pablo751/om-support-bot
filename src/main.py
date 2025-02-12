import logging
from fastapi import FastAPI
from src.routers.webhook import webhook_router
import uvicorn

def create_app() -> FastAPI:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    app = FastAPI(title="YOM Support Bot", version="1.0.0")
    app.include_router(webhook_router)
    return app

app = create_app()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
