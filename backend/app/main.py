import traceback
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.db import Base, engine
from app.errors import GridlockError, gridlock_error_handler
from app.routers import data, model, predictions


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(bind=engine)

    from app.services.model_state import model_state

    try:
        print("[GRIDLOCK] Starting auto-train...", flush=True)
        from app.ml import get_predictor
        from app.ml.spectral_predictor import SpectralRidgePredictor

        predictor = get_predictor()
        print(f"[GRIDLOCK] Predictor type: {type(predictor).__name__}", flush=True)
        if isinstance(predictor, SpectralRidgePredictor):
            predictor.train_synthetic()
            model_state.set_ready()
            print("[GRIDLOCK] Model ready.", flush=True)
        else:
            print("[GRIDLOCK] Not spectral predictor, skipping auto-train.", flush=True)
    except Exception:
        print(f"[GRIDLOCK] Auto-train FAILED:\n{traceback.format_exc()}", flush=True)
        model_state.set_idle()

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
