from sqlalchemy import Column, Integer, String, JSON, DateTime, func, ForeignKey, CheckConstraint, Index
from app.db.database import Base

class Dataset(Base):
    __tablename__ = "datasets"
    
    __table_args__ = (
        CheckConstraint('row_count > 0 AND row_count <= 30000', name='check_row_count_valid'),
        CheckConstraint('column_count > 0 AND column_count <= 100', name='check_column_count_valid'),
        CheckConstraint("length(prompt) <= 2000", name='check_prompt_length'),
        Index('ix_datasets_user_created', 'user_id', 'created_at'),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False, index=True)
    source_type = Column(String(50), nullable=False) # e.g., 'upload', 'database', 'prompt'
    source_filename = Column(String(512), nullable=True)
    row_count = Column(Integer, nullable=False)
    column_count = Column(Integer, nullable=False)
    prompt = Column(String(2000), nullable=True)
    
    schema_json = Column(JSON, nullable=True)
    profile_json = Column(JSON, nullable=True)
    relationships_json = Column(JSON, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
