from sqlalchemy import Column, Integer, String, JSON, DateTime, ForeignKey, CheckConstraint, Enum as SQLEnum
from sqlalchemy.sql import func
from app.db.database import Base
import enum

class JobStatus(str, enum.Enum):
    """Valid job status values"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    dataset_id = Column(Integer, ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False, index=True)
    
    status = Column(
        SQLEnum(JobStatus, name="job_status_enum", create_constraint=True),
        default=JobStatus.PENDING,
        nullable=False
    )
    current_step = Column(String, default="initialized")
    error_message = Column(String, nullable=True)
    
    evaluation_report_json = Column(JSON, nullable=True)
    synthetic_file_path = Column(String, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
