from sqlalchemy import Column, Integer, String, JSON, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.db.database import Base

class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    dataset_id = Column(Integer, ForeignKey("datasets.id"))
    
    status = Column(String, default="pending")  # pending, running, completed, failed
    current_step = Column(String, default="initialized")
    error_message = Column(String, nullable=True)
    
    evaluation_report_json = Column(JSON, nullable=True)
    synthetic_file_path = Column(String, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
