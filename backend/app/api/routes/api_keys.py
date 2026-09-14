from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.api_key import ApiKey
import secrets
import hashlib
from pydantic import BaseModel

router = APIRouter()

class ApiKeyCreate(BaseModel):
    name: str

@router.get("/")
def get_api_keys(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    keys = db.query(ApiKey).filter(ApiKey.user_id == current_user.id, ApiKey.is_active == True).all()
    return [{"id": k.id, "name": k.name, "key_preview": k.key_preview, "created_at": k.created_at, "last_used_at": k.last_used_at} for k in keys]

@router.post("/")
def create_api_key(data: ApiKeyCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    raw_key = secrets.token_urlsafe(32)
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    key_preview = raw_key[:4] + "..." + raw_key[-4:]
    
    db_key = ApiKey(user_id=current_user.id, name=data.name, key_hash=key_hash, key_preview=key_preview)
    db.add(db_key)
    db.commit()
    db.refresh(db_key)
    
    return {"id": db_key.id, "name": db_key.name, "api_key": raw_key, "created_at": db_key.created_at}

@router.delete("/{key_id}")
def delete_api_key(key_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    db_key = db.query(ApiKey).filter(ApiKey.id == key_id, ApiKey.user_id == current_user.id).first()
    if not db_key:
        raise HTTPException(status_code=404, detail="API Key not found")
    db_key.is_active = False
    db.commit()
    return {"status": "deleted"}
