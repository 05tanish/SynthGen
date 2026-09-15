from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.db.database import get_db
from app.models.user import User
from app.schemas.user import UserResponse, Token
from app.core.security import create_access_token
from app.core.config import settings
from app.core.logging import logger
from app.api.deps import get_current_user

from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

router = APIRouter()


# ─────────────────────────────────────────
# Schemas
# ─────────────────────────────────────────

class GoogleLoginRequest(BaseModel):
    token: str

class UserUpdate(BaseModel):
    name: str = None


# ─────────────────────────────────────────
# Routes
# ─────────────────────────────────────────

@router.post("/google-login", response_model=Token)
def google_login(req: GoogleLoginRequest, db: Session = Depends(get_db)):
    """
    Authenticate with Google OAuth 2.0 ID token.
    - If a user exists with the same email (regardless of how they signed up previously), they are logged in.
    - If no user exists, a new account is created automatically.
    """
    try:
        idinfo = id_token.verify_oauth2_token(
            req.token,
            google_requests.Request(),
            settings.GOOGLE_CLIENT_ID
        )
    except ValueError as e:
        logger.warning(f"Invalid Google token: {e}")
        raise HTTPException(status_code=401, detail="Invalid or expired Google token.")

    email = idinfo.get("email")
    name = idinfo.get("name")
    email_verified = idinfo.get("email_verified", False)

    if not email:
        raise HTTPException(status_code=400, detail="Google token did not contain an email address.")
    if not email_verified:
        raise HTTPException(status_code=400, detail="Google account email is not verified.")

    # Find existing user by email — works regardless of how they previously registered
    user = db.query(User).filter(User.email == email).first()

    if not user:
        # Auto-create account for first-time Google users
        logger.info(f"Creating new account via Google OAuth for {email}")
        user = User(
            email=email,
            name=name,
            hashed_password=None,  # Google OAuth users have no password
            is_verified=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        # Existing user — ensure they are verified and update name if missing
        if not user.is_verified:
            user.is_verified = True
        if not user.name and name:
            user.name = name
        db.commit()
        db.refresh(user)
        logger.info(f"Existing user logged in via Google OAuth: {email}")

    access_token = create_access_token(subject=str(user.id))
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=UserResponse)
def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.patch("/me", response_model=UserResponse)
def update_user_me(
    user_update: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if user_update.name is not None:
        current_user.name = user_update.name
    db.commit()
    db.refresh(current_user)
    return current_user
