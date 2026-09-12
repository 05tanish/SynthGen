from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models.user import User
from app.schemas.user import UserCreate, UserResponse, Token, ChangePassword
from app.core.security import get_password_hash, verify_password, create_access_token
from app.api.deps import get_current_user
from app.core.config import settings
from app.core.logging import logger
import uuid
import resend

router = APIRouter()

def send_verification_email(email: str, token: str):
    link = f"http://localhost:5173/verify?token={token}"
    if settings.RESEND_API_KEY and settings.RESEND_API_KEY != "re_placeholder":
        try:
            resend.api_key = settings.RESEND_API_KEY
            r = resend.Emails.send({
                "from": "onboarding@resend.dev",
                "to": email,
                "subject": "Verify your Agentic AI Account",
                "html": f"<p>Welcome to Agentic AI! Please click <a href='{link}'>here</a> to verify your account.</p>"
            })
            logger.info(f"Sent verification email to {email}")
        except Exception as e:
            logger.error(f"Failed to send email to {email}: {e}")
    else:
        logger.warning(f"RESEND_API_KEY not configured. Verification link for {email}: {link}")

@router.post("/register", response_model=UserResponse)
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == user_in.email).first()
    if user:
        raise HTTPException(
            status_code=400,
            detail="The user with this email already exists in the system.",
        )
        
    token = str(uuid.uuid4())
    user = User(
        email=user_in.email,
        hashed_password=get_password_hash(user_in.password),
        is_verified=False,
        verification_token=token
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # Send email asynchronously or just fire and forget
    send_verification_email(user.email, token)
    
    return user

@router.get("/verify/{token}")
def verify_email(token: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.verification_token == token).first()
    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired verification token")
        
    user.is_verified = True
    user.verification_token = None
    db.commit()
    
    return {"message": "Account successfully verified"}

@router.post("/login", response_model=Token)
def login(db: Session = Depends(get_db), form_data: OAuth2PasswordRequestForm = Depends()):
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )
    
    access_token = create_access_token(subject=user.id)
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/change-password")
def change_password(data: ChangePassword, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if not verify_password(data.current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect current password")
        
    current_user.hashed_password = get_password_hash(data.new_password)
    db.commit()
    return {"message": "Password changed successfully"}

@router.get("/me", response_model=UserResponse)
def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user
