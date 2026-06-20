import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, UploadFile
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.errors import GridlockError
from app.models import Dataset
from app.schemas import DatasetListResponse, DatasetOut, DeleteResponse
from app.services.ingest import parse_csv
from app.services.model_state import model_state
from app.services.retrain import run_retrain

router = APIRouter()


@router.get("/data", response_model=DatasetListResponse)
def list_datasets(db: Session = Depends(get_db)):
    datasets = db.query(Dataset).order_by(Dataset.uploaded_at.desc()).all()
    return DatasetListResponse(
        datasets=[
            DatasetOut(
                id=ds.id,
                filename=ds.filename,
                uploaded_at=ds.uploaded_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
                row_count=ds.row_count,
                status=ds.status,
            )
            for ds in datasets
        ]
    )


@router.post("/data/upload", status_code=201, response_model=DatasetOut)
async def upload_dataset(
    file: UploadFile,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise GridlockError(
            415, "unsupported_media_type", "Only CSV files are accepted."
        )

    content = await file.read()
    dataset_id = f"d_{uuid.uuid4().hex[:8]}"
    now = datetime.now(timezone.utc)

    data_dir = settings.data_dir
    data_dir.mkdir(parents=True, exist_ok=True)
    file_path = data_dir / f"{dataset_id}.csv"
    file_path.write_bytes(content)

    try:
        rows = parse_csv(content, dataset_id)
    except ValueError as e:
        file_path.unlink(missing_ok=True)
        raise GridlockError(422, "invalid_csv", str(e))

    if not rows:
        file_path.unlink(missing_ok=True)
        raise GridlockError(422, "empty_csv", "CSV contains no valid data rows.")

    dataset = Dataset(
        id=dataset_id,
        filename=file.filename,
        uploaded_at=now,
        row_count=len(rows),
        status="processing",
        path=str(file_path),
    )
    db.add(dataset)
    db.add_all(rows)
    db.commit()

    model_state.set_training()
    background_tasks.add_task(run_retrain, dataset_id)

    return DatasetOut(
        id=dataset.id,
        filename=dataset.filename,
        uploaded_at=now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        row_count=dataset.row_count,
        status=dataset.status,
    )


@router.delete("/data/{dataset_id}", response_model=DeleteResponse)
def delete_dataset(
    dataset_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise GridlockError(404, "not_found", f"Dataset '{dataset_id}' not found.")

    try:
        Path(dataset.path).unlink(missing_ok=True)
    except OSError:
        pass

    db.delete(dataset)
    db.commit()

    remaining = db.query(Dataset).count()
    if remaining == 0:
        model_state.set_idle()
        return DeleteResponse(
            message="Dataset deleted. No datasets remain.",
            retrain_status="idle",
        )

    model_state.set_training()
    background_tasks.add_task(run_retrain)

    return DeleteResponse(
        message="Dataset deleted. Model retrain initiated.",
        retrain_status="training",
    )
