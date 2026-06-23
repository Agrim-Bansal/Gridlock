from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.db import Base, engine
from app.errors import GridlockError, gridlock_error_handler
from app.routers import data, model, predictions
from app.services.startup import recover_model_on_startup


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(bind=engine)
    recover_model_on_startup()
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
