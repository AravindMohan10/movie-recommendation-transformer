from pydantic import BaseModel, EmailStr, field_validator

def _truncate_password_72_bytes(v: str) -> str:
    """Bcrypt limit: 72 bytes. Truncate at schema level so no code path ever sees longer."""
    if not isinstance(v, str):
        return v
    b = v.encode("utf-8")[:72]
    return b.decode("utf-8", errors="ignore")

class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str

    @field_validator("password", mode="before")
    @classmethod
    def truncate_password(cls, v: str) -> str:
        return _truncate_password_72_bytes(v)

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserOut(BaseModel):
    user_id: int
    username: str
    email: EmailStr

    class Config:
        from_attributes = True

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

    @field_validator("new_password", mode="before")
    @classmethod
    def truncate_new_password(cls, v: str) -> str:
        return _truncate_password_72_bytes(v)