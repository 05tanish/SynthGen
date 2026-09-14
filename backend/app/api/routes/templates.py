from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models.template import Template

router = APIRouter()

@router.get("/")
def get_templates(db: Session = Depends(get_db)):
    templates = db.query(Template).all()
    if not templates:
        # Mock some default templates if empty
        return [
            {"id": 1, "name": "Customer Data", "description": "Basic customer profiles", "complexity": "Low", "use_case": "CRM Testing"},
            {"id": 2, "name": "E-commerce Orders", "description": "Transaction logs", "complexity": "Medium", "use_case": "Analytics"}
        ]
    return templates

@router.get("/{template_id}")
def get_template(template_id: int, db: Session = Depends(get_db)):
    template = db.query(Template).filter(Template.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return template
