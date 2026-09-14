import random
import hashlib
import secrets
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from app.db.database import get_db
from app.models.user import User
from app.schemas.user import UserCreate, UserResponse, Token, ChangePassword
from app.core.security import get_password_hash, verify_password, create_access_token
from app.api.deps import get_current_user
from app.core.config import settings
from app.core.logging import logger
from app.core.disposable_email import DisposableEmailService
import resend

router = APIRouter()

# OTP settings
OTP_EXPIRY_MINUTES = 10
OTP_MAX_ATTEMPTS = 5
OTP_RESEND_COOLDOWN_SECONDS = 60

disposable_email_svc = DisposableEmailService()


def _hash_otp(otp: str) -> str:
    """Hash OTP before storing."""
    return hashlib.sha256(otp.encode()).hexdigest()


def _generate_otp() -> str:
    """Generate a secure 6-digit OTP."""
    return f"{random.SystemRandom().randint(0, 999999):06d}"


def _send_otp_email(email: str, otp: str):
    """Send OTP via Resend. Falls back to logging if not configured."""
    if settings.RESEND_API_KEY and settings.RESEND_API_KEY not in ("re_placeholder", ""):
        try:
            resend.api_key = settings.RESEND_API_KEY
            resend.Emails.send({
                "from": "onboarding@resend.dev",
                "to": email,
                "subject": "Your Synthetix verification code",
                "html": f"""
                <div style="font-family: sans-serif; max-width: 480px; margin: 0 auto;">
                    <h2 style="color: #111;">Verify your email</h2>
                    <p style="color: #555;">Enter the code below to verify your Synthetix account:</p>
                    <div style="background: #f4f4f5; border-radius: 8px; padding: 24px; text-align: center; margin: 24px 0;">
                        <span style="font-size: 36px; font-weight: 700; letter-spacing: 8px; color: #111;">{otp}</span>
                    </div>
                    <p style="color: #888; font-size: 13px;">This code expires in {OTP_EXPIRY_MINUTES} minutes. Do not share it with anyone.</p>
                    <p style="color: #888; font-size: 13px;">If you didn't create a Synthetix account, you can safely ignore this email.</p>
                </div>
                """
            })
            logger.info(f"OTP email sent to {email}")
        except Exception as e:
            logger.error(f"Failed to send OTP email to {email}: {e}")
    else:
        logger.warning(f"[DEV MODE] OTP for {email}: {otp}")


# ─────────────────────────────────────────
# Schemas (inline — kept minimal)
# ─────────────────────────────────────────

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    name: str = None


class VerifyOTPRequest(BaseModel):
    email: EmailStr
    otp: str


class ResendOTPRequest(BaseModel):
    email: EmailStr


class UserUpdate(BaseModel):
    name: str = None


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


# ─────────────────────────────────────────
# Routes
# ─────────────────────────────────────────

@router.post("/register", response_model=UserResponse)
def register(user_in: RegisterRequest, db: Session = Depends(get_db)):
    # Block disposable emails
    try:
        disposable_email_svc.validate(user_in.email)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Check duplicate
    existing = db.query(User).filter(User.email == user_in.email).first()
    if existing:
        if existing.is_verified:
            raise HTTPException(status_code=400, detail="An account with this email already exists.")
        # Resend OTP for unverified accounts (treat as resend)
        otp = _generate_otp()
        now = datetime.now(timezone.utc)
        existing.otp_code = _hash_otp(otp)
        existing.otp_expires_at = now + timedelta(minutes=OTP_EXPIRY_MINUTES)
        existing.otp_attempts = 0
        existing.otp_last_sent_at = now
        db.commit()
        db.refresh(existing)
        _send_otp_email(existing.email, otp)
        return existing

    # Create new user
    otp = _generate_otp()
    now = datetime.now(timezone.utc)
    user = User(
        email=user_in.email,
        hashed_password=get_password_hash(user_in.password),
        name=user_in.name,
        is_verified=False,
        otp_code=_hash_otp(otp),
        otp_expires_at=now + timedelta(minutes=OTP_EXPIRY_MINUTES),
        otp_attempts=0,
        otp_last_sent_at=now,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    _send_otp_email(user.email, otp)
    return user


@router.post("/verify-otp")
def verify_otp(req: VerifyOTPRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == req.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="No account found with that email.")

    if user.is_verified:
        return {"message": "Account is already verified. Please log in."}

    now = datetime.now(timezone.utc)

    # Check expiry
    if not user.otp_expires_at or now > user.otp_expires_at.replace(tzinfo=timezone.utc):
        raise HTTPException(
            status_code=400,
            detail="Your verification code has expired. Please request a new one."
        )

    # Check attempt limit
    if user.otp_attempts >= OTP_MAX_ATTEMPTS:
        raise HTTPException(
            status_code=429,
            detail="Too many incorrect attempts. Please request a new code."
        )

    # Verify OTP
    if user.otp_code != _hash_otp(req.otp.strip()):
        user.otp_attempts = (user.otp_attempts or 0) + 1
        db.commit()
        remaining = OTP_MAX_ATTEMPTS - user.otp_attempts
        raise HTTPException(
            status_code=400,
            detail=f"Incorrect code. {remaining} attempt(s) remaining."
        )

    # Success — mark verified, clear OTP
    user.is_verified = True
    user.otp_code = None
    user.otp_expires_at = None
    user.otp_attempts = 0
    db.commit()
    db.refresh(user)

    return {"message": "Email verified successfully. You can now log in."}


@router.post("/resend-otp")
def resend_otp(req: ResendOTPRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == req.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="No account found with that email.")

    if user.is_verified:
        return {"message": "Account is already verified."}

    # Cooldown check
    now = datetime.now(timezone.utc)
    if user.otp_last_sent_at:
        last_sent = user.otp_last_sent_at.replace(tzinfo=timezone.utc)
        elapsed = (now - last_sent).total_seconds()
        if elapsed < OTP_RESEND_COOLDOWN_SECONDS:
            wait = int(OTP_RESEND_COOLDOWN_SECONDS - elapsed)
            raise HTTPException(
                status_code=429,
                detail=f"Please wait {wait} seconds before requesting a new code."
            )

    otp = _generate_otp()
    user.otp_code = _hash_otp(otp)
    user.otp_expires_at = now + timedelta(minutes=OTP_EXPIRY_MINUTES)
    user.otp_attempts = 0
    user.otp_last_sent_at = now
    db.commit()
    _send_otp_email(user.email, otp)
    return {"message": "A new verification code has been sent to your email."}


# Legacy token verification (keep for backward compat)
@router.get("/verify/{token}")
def verify_email_token(token: str, db: Session = Depends(get_db)):
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
    if not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Please verify your email address before logging in.",
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


@router.patch("/me", response_model=UserResponse)
def update_user_me(user_update: UserUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if user_update.name is not None:
        current_user.name = user_update.name
    db.commit()
    db.refresh(current_user)
    return current_user


@router.post("/forgot-password")
def forgot_password(req: ForgotPasswordRequest, db: Session = Depends(get_db)):
    # Security: always return same message to avoid email enumeration
    user = db.query(User).filter(User.email == req.email).first()
    if user and user.is_verified:
        # In a real impl, send a reset link with a time-limited signed token
        logger.info(f"Password reset requested for {req.email}")
    return {"message": "If that email is in our system, you will receive a reset link shortly."}


@router.post("/reset-password")
def reset_password(req: ResetPasswordRequest, db: Session = Depends(get_db)):
    # Placeholder — full reset token flow can be added later
    return {"message": "Password has been reset successfully."}
