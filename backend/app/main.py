import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.db import Base, engine
from app.errors import GridlockError, gridlock_error_handler
from app.routers import data, geocode, model, predictions
from app.services import geocode_lookup
from app.services.startup import recover_model_on_startup

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stdout,
)
logger = logging.getLogger("gridlock")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(bind=engine)
    logger.info("Database initialized at %s", settings.database_url)
    recover_model_on_startup()
    cis_dir = settings.data_dir / "cis_fallback"
    if cis_dir.exists():
        n = len(list(cis_dir.glob("*.json")))
        logger.info("CIS fallback data: %d zone files loaded", n)
    else:
        logger.warning("No CIS fallback data at %s — using synthetic scores", cis_dir)
    n_geo = geocode_lookup.load(settings.geocode_data_path)
    if n_geo:
        logger.info("Geocode reverse lookup: %d cell names loaded", n_geo)
    else:
        logger.warning("No geocode data loaded — cell names will be unavailable")
    yield


app = FastAPI(title="Gridlock Backend", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Content-Type"],
)

app.add_exception_handler(GridlockError, gridlock_error_handler)

app.include_router(predictions.router, prefix="/api")
app.include_router(model.router, prefix="/api")
app.include_router(data.router, prefix="/api")
app.include_router(geocode.router, prefix="/api")
