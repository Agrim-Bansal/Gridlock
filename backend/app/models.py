from sqlalchemy import Column, String, Integer, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.db import Base


class Dataset(Base):
    __tablename__ = "datasets"

    id = Column(String, primary_key=True)
    filename = Column(String, nullable=False)
    uploaded_at = Column(DateTime, nullable=False)
    row_count = Column(Integer, default=0)
    status = Column(String, default="processing")
    path = Column(String, nullable=False)

    rows = relationship(
        "ViolationRow",
        back_populates="dataset",
        cascade="all, delete-orphan",
    )


class ViolationRow(Base):
    __tablename__ = "violation_rows"

    id = Column(Integer, primary_key=True, autoincrement=True)
    dataset_id = Column(
        String,
        ForeignKey("datasets.id", ondelete="CASCADE"),
        nullable=False,
    )
    timestamp = Column(DateTime, nullable=False)
    cell_id = Column(String, nullable=False)
    violation_type = Column(String, nullable=True)
    severity_src = Column(String, nullable=True)

    dataset = relationship("Dataset", back_populates="rows")
