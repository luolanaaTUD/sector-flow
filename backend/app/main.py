import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import fund_flow, sectors
from app.config import settings
from app.database import init_db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Sector Flow API",
    description="A股板块主力资金流向实时 API",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(sectors.router)
app.include_router(fund_flow.router)


@app.on_event("startup")
def on_startup():
    logger.info("Initializing database...")
    init_db()
    logger.info("Database ready.")

    if settings.COLLECTOR_ENABLED:
        from app.collector.worker import start_scheduler
        start_scheduler()
        logger.info("Collector scheduler started.")


@app.get("/health")
def health():
    return {"status": "ok"}
