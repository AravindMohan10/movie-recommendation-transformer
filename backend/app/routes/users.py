from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordRequestForm
from ..schemas import UserOut, UserCreate, ForgotPasswordRequest, ResetPasswordRequest
from ..crud import get_user_by_email, get_user_by_username, create_user
from ..database import SessionLocal
from ..auth import verify_password, create_access_token, get_current_user, hash_password
from ..models import User, PasswordResetToken
from ..limiter import limiter
from datetime import datetime, timezone, timedelta
import secrets
import logging
import urllib.parse

router = APIRouter()
logger = logging.getLogger(__name__)

# So you can verify deployed backend has the 72-byte password fix (curl .../api/version)
@router.get("/version", tags=["users"])
def api_version():
    return {"version": "1.0.0", "password_validation": "v1", "reject_over_72_bytes": True}

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/signup", response_model=UserOut)
@limiter.exempt
async def signup(request: Request, user: UserCreate, db: Session = Depends(get_db)):
    try:
        # Password validation happens in UserCreate schema (raises ValueError if >72 bytes)
        if get_user_by_email(db, user.email):
            raise HTTPException(status_code=400, detail="Email already registered.")
        if get_user_by_username(db, user.username):
            raise HTTPException(status_code=400, detail="Username already taken.")
        created_user = create_user(db, user)
        logger.info("User created: user_id=%s", created_user.user_id)
        return created_user
    except HTTPException:
        raise
    except ValueError as e:
        # Password validation errors (e.g., too long) - return 400 with clear message
        logger.warning("Password validation failed: %s", e)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Signup error")
        raise HTTPException(status_code=500, detail=f"Signup failed: {str(e)}")

@router.post("/login")
@limiter.exempt
def login(
    request: Request,
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    try:
        login_str = form_data.username
        user = get_user_by_email(db, login_str) or get_user_by_username(db, login_str)
        if not user:
            raise HTTPException(status_code=401, detail="Incorrect username/email or password")
        if not verify_password(form_data.password, user.hashed_password):
            raise HTTPException(status_code=401, detail="Incorrect username/email or password")
        token_data = {"sub": str(user.user_id)}
        access_token = create_access_token(token_data)
        response.set_cookie(
            key="cineai_token",
            value=access_token,
            httponly=True,
            secure=False,
            samesite="lax",
            max_age=60 * 60 * 24 * 7,
            path="/"
        )
        logger.info("Login: user_id=%s", user.user_id)
        return {"access_token": access_token, "token_type": "bearer"}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Login error")
        raise HTTPException(status_code=500, detail=f"Login failed: {str(e)}")

@router.post("/logout")
def logout(response: Response):
    response.delete_cookie("cineai_token", path="/")
    return {"msg": "Logged out"}

@router.get("/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user

@router.post("/forgot-password")
@limiter.limit("5/minute")
def forgot_password(request: Request, body: ForgotPasswordRequest, db: Session = Depends(get_db)):
    """Request password reset - sends reset token to email"""
    try:
        user = get_user_by_email(db, body.email)
        
        # For security, always return success even if user doesn't exist
        # This prevents email enumeration attacks
        if not user:
            logger.info(f"Password reset requested for non-existent email: {body.email}")
            return {
                "message": "If an account with that email exists, a password reset link has been sent."
            }
        
        # Generate secure random token
        token = secrets.token_urlsafe(32)
        
        # Set expiration to 1 hour from now
        expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
        
        # Invalidate any existing tokens for this user
        db.query(PasswordResetToken).filter(
            PasswordResetToken.user_id == user.user_id,
            PasswordResetToken.used == 0
        ).update({"used": 1})
        
        # Create new reset token
        reset_token = PasswordResetToken(
            user_id=user.user_id,
            token=token,
            expires_at=expires_at,
            used=0
        )
        db.add(reset_token)
        db.commit()
        db.refresh(reset_token)
        
        # Send password reset email (non-blocking)
        try:
            from ..email_service import send_password_reset_email
            import asyncio
            import threading
            
            def send_email_async():
                """Send email in background thread"""
                try:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    email_sent = loop.run_until_complete(send_password_reset_email(
                        email=user.email,
                        reset_token=token,
                        username=user.username
                    ))
                    loop.close()
                    
                    if email_sent:
                        logger.info(f"Password reset email sent to {user.email}")
                    else:
                        logger.warning(f"Password reset email failed for {user.email}")
                except Exception as e:
                    logger.error(f"Error in email thread: {e}")
            
            # Send email in background thread (non-blocking)
            email_thread = threading.Thread(target=send_email_async, daemon=True)
            email_thread.start()
            
        except Exception as e:
            logger.error(f"Error initiating password reset email: {e}", exc_info=True)
            # Continue anyway - user still gets success message for security
        
        return {
            "message": "If an account with that email exists, a password reset link has been sent."
        }
        
    except Exception as e:
        logger.error(f"Error in forgot password: {e}", exc_info=True)
        db.rollback()
        # Still return success message for security
        return {
            "message": "If an account with that email exists, a password reset link has been sent."
        }

@router.get("/reset-password/verify/{token}")
def verify_reset_token(token: str, db: Session = Depends(get_db)):
    """Verify if a password reset token is valid"""
    try:
        decoded_token = urllib.parse.unquote(token)
        reset_token = db.query(PasswordResetToken).filter(
            PasswordResetToken.token == decoded_token,
            PasswordResetToken.used == 0
        ).first()
        if not reset_token:
            reset_token = db.query(PasswordResetToken).filter(
                PasswordResetToken.token == token,
                PasswordResetToken.used == 0
            ).first()
        if not reset_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired reset token"
            )
        now = datetime.now(timezone.utc)
        expires_at = reset_token.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at < now:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Reset token has expired"
            )
        logger.info("Token verified for user_id=%s", reset_token.user_id)
        return {"valid": True, "message": "Token is valid"}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Verify reset token error")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )

@router.post("/reset-password")
def reset_password(request: ResetPasswordRequest, db: Session = Depends(get_db)):
    """Reset password using a valid reset token"""
    try:
        # Validate password strength
        if len(request.new_password) < 6:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password must be at least 6 characters long"
            )
        
        # URL decode the token
        decoded_token = urllib.parse.unquote(request.token)
        
        logger.info(f"Password reset attempt with token (length: {len(decoded_token)})")
        
        # Find valid reset token
        reset_token = db.query(PasswordResetToken).filter(
            PasswordResetToken.token == decoded_token,
            PasswordResetToken.used == 0
        ).first()
        
        if not reset_token:
            logger.warning(f"Reset token not found or already used: {decoded_token[:20]}...")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired reset token"
            )
        
        now = datetime.now(timezone.utc)
        
        # Ensure both datetimes are timezone-aware for comparison
        expires_at = reset_token.expires_at
        if expires_at.tzinfo is None:
            # If expires_at is naive, assume it's UTC
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        
        if expires_at < now:
            logger.warning(f"Reset token expired. Expires: {expires_at}, Now: {now}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Reset token has expired"
            )
        
        # Get user
        user = db.query(User).filter(User.user_id == reset_token.user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Update password
        user.hashed_password = hash_password(request.new_password)
        
        # Mark token as used
        reset_token.used = 1
        
        # Invalidate all other reset tokens for this user
        db.query(PasswordResetToken).filter(
            PasswordResetToken.user_id == user.user_id,
            PasswordResetToken.used == 0,
            PasswordResetToken.id != reset_token.id
        ).update({"used": 1})
        
        db.commit()
        
        logger.info(f"Password successfully reset for user: {user.email}")
        
        return {
            "message": "Password has been successfully reset. You can now log in with your new password."
        }
        
    except HTTPException:
        raise
    except ValueError as e:
        # Password validation errors (e.g., too long) - return 400 with clear message
        logger.warning("Password validation failed: %s", e)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error resetting password: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reset password: {str(e)}"
        )