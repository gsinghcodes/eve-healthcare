import logging.config
from contextlib import asynccontextmanager
from pathlib import Path

import redis
import yaml

logging_config_path = Path(__file__).resolve().with_name("logging.yaml")
logging_config = yaml.safe_load(logging_config_path.read_text(encoding="utf-8"))
logs_directory = logging_config_path.parent / "logs"
logs_directory.mkdir(parents=True, exist_ok=True)

for handler_config in logging_config["handlers"].values():
    filename = handler_config.get("filename")
    if filename:
        handler_config["filename"] = str(logging_config_path.parent / filename)

logging.config.dictConfig(logging_config)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import models

from routers.auth import router as auth_router
from routers.booking import router as booking_router
from routers.center import router as center_router
from routers.diagnostic_tests import router as diagnostic_test_router
from routers.payments import router as payment_router
from routers.schedule import router as schedule_router
from core.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    redis_client = redis.Redis.from_url(
        settings.CELERY_BROKER_URL,
        decode_responses=True,
    )
    app.state.redis = redis_client
    try:
        yield
    finally:
        redis_client.close()

app = FastAPI(
    title="EVE Healthcare API",
    version="1.0.0",
    lifespan=lifespan,
)

origins = ["http://localhost:3000"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(booking_router)
app.include_router(center_router)
app.include_router(diagnostic_test_router)
app.include_router(payment_router)
app.include_router(schedule_router)


@app.get("/")
def health_check():
    return {
        "status": 200,
        "message": "EVE Healthcare API is running",
    }
