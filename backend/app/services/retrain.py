import time

from app.config import settings
from app.db import SessionLocal
from app.ml import get_predictor
from app.models import Dataset, ViolationRow
from app.services.model_state import model_state


def run_retrain(dataset_id: str | None = None) -> None:
    """Background task: wait for observable delay, then retrain the model."""
    time.sleep(settings.retrain_delay_s)

    db = SessionLocal()
    try:
        all_rows = db.query(ViolationRow).all()

        if not all_rows:
            model_state.set_idle()
            return

        predictor = get_predictor()
        predictor.train(all_rows)

        if dataset_id:
            ds = db.query(Dataset).filter(Dataset.id == dataset_id).first()
            if ds:
                ds.status = "active"
                db.commit()

        model_state.set_ready()
    except Exception:
        model_state.set_idle()
    finally:
        db.close()
