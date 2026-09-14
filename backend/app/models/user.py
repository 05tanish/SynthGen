from sqlalchemy import Column, Integer, String, DateTime, Boolean, CheckConstraint, Index
from sqlalchemy.sql import func
from app.db.database import Base

class User(Base):
    __tablename__ = "users"
    
    __table_args__ = (
        CheckConstraint('otp_attempts >= 0 AND otp_attempts <= 10', name='check_otp_attempts_range'),
        Index('ix_users_email_verified', 'email', 'is_verified'),
    )

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    name = Column(String(255), nullable=True)
    is_verified = Column(Boolean, default=False, nullable=False)
    
    # Legacy token-based verification (kept for compat)
    verification_token = Column(String(255), nullable=True, index=True)
    
    # OTP-based verification
    otp_code = Column(String(255), nullable=True)           # hashed 6-digit OTP
    otp_expires_at = Column(DateTime(timezone=True), nullable=True)
    otp_attempts = Column(Integer, default=0, nullable=False)
    otp_last_sent_at = Column(DateTime(timezone=True), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
