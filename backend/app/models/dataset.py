from sqlalchemy import Column, Integer, String, JSON, DateTime, func
from app.db.database import Base

class Dataset(Base):
    __tablename__ = "datasets"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    source_type = Column(String) # e.g., 'upload', 'database', 'requirement'
    source_filename = Column(String, nullable=True)
    row_count = Column(Integer)
    column_count = Column(Integer)
    prompt = Column(String, nullable=True)
    
    schema_json = Column(JSON, nullable=True)
    profile_json = Column(JSON, nullable=True)
    relationships_json = Column(JSON, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
