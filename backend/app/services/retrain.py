import logging
import time

from app.config import settings
from app.db import SessionLocal
from app.ml import get_predictor
from app.models import Dataset, ViolationRow
from app.services.model_state import model_state
from app.services.ranking_snapshot import build_snapshot, clear_snapshot, get_any_snapshot

logger = logging.getLogger(__name__)


def run_retrain(dataset_id: str | None = None) -> None:
    """Background task: wait for observable delay, then retrain the model."""
    time.sleep(settings.retrain_delay_s)

    db = SessionLocal()
    try:
        all_rows = db.query(ViolationRow).all()

        if not all_rows:
            model_state.set_idle()
            clear_snapshot()
            return

        predictor = get_predictor()
        predictor.train(all_rows)
        build_snapshot(predictor, all_rows)
        model_state.set_ready()
    except Exception:
        logger.exception("Retrain failed")
        if get_any_snapshot() is not None:
            # Keep serving the last good snapshot instead of flipping to idle.
            model_state.set_ready()
        else:
            model_state.set_idle()
            clear_snapshot()
    finally:
        if dataset_id:
            ds = db.query(Dataset).filter(Dataset.id == dataset_id).first()
            if ds:
                ds.status = "active"
                db.commit()
        db.close()
