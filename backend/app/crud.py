from sqlalchemy.orm import Session
from .models import User
from .schemas import UserCreate
from .auth import hash_password, verify_password, truncate_password_for_bcrypt

def get_user_by_email(db: Session, email: str):
    return db.query(User).filter(User.email == email).first()

def get_user_by_username(db: Session, username: str):
    return db.query(User).filter(User.username == username).first()

def create_user(db: Session, user: UserCreate):
    # Truncate before hashing so bcrypt 72-byte limit is never hit (belt-and-suspenders with auth.hash_password)
    safe_password = truncate_password_for_bcrypt(user.password)
    hashed_pw = hash_password(safe_password)
    db_user = User(
        username=user.username,
        email=user.email,
        hashed_password=hashed_pw
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def authenticate_user(db: Session, email: str, password: str):
    user = get_user_by_email(db, email)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user