"""Restore model status after a process restart (in-memory state is lost)."""

from __future__ import annotations

import logging
import threading

from app.db import SessionLocal
from app.models import ViolationRow
from app.services.model_state import model_state
from app.services.ranking_snapshot import get_any_snapshot
from app.services.retrain import run_retrain

logger = logging.getLogger(__name__)


def recover_model_on_startup() -> None:
    """If SQLite still has data, reflect that in model status."""
    db = SessionLocal()
    try:
        row_count = db.query(ViolationRow).count()
    finally:
        db.close()

    if row_count == 0:
        model_state.set_idle()
        return

    if get_any_snapshot() is not None:
        logger.info("Recovered ready state from prediction snapshot (%d rows)", row_count)
        model_state.set_ready()
        return

    logger.info("Data present but no snapshot — scheduling retrain (%d rows)", row_count)
    model_state.set_training()
    threading.Thread(target=run_retrain, daemon=True).start()
