from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Dataset
from app.schemas import ModelStatusResponse
from app.services.model_state import model_state

router = APIRouter()


@router.get("/model/status", response_model=ModelStatusResponse)
def get_model_status(db: Session = Depends(get_db)):
    result = (
        db.query(
            func.count(Dataset.id),
            func.coalesce(func.sum(Dataset.row_count), 0),
        )
        .filter(Dataset.status == "active")
        .first()
    )

    dataset_count = result[0] if result else 0
    total_rows = result[1] if result else 0

    return ModelStatusResponse(
        status=model_state.status,
        last_trained_at=model_state.last_trained_at,
        dataset_count=dataset_count,
        total_rows=total_rows,
    )
