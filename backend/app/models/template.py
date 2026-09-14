from sqlalchemy import Column, Integer, String, JSON, DateTime
from sqlalchemy.sql import func
from app.db.database import Base

class Template(Base):
    __tablename__ = "templates"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    description = Column(String)
    schema_json = Column(JSON)
    use_case = Column(String)
    complexity = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
