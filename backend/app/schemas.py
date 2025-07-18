from pydantic import BaseModel, EmailStr, field_validator, model_validator

def _truncate_password_72_bytes(v) -> str:
    """Bcrypt limit: 72 bytes. Truncate at schema level so no code path ever sees longer."""
    if isinstance(v, bytes):
        v = v.decode("utf-8", errors="ignore")
    if not isinstance(v, str):
        return str(v) if v is not None else ""
    b = v.encode("utf-8")[:72]
    return b.decode("utf-8", errors="ignore")

class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str

    @field_validator("password", mode="before")
    @classmethod
    def truncate_password(cls, v) -> str:
        return _truncate_password_72_bytes(v)

    @model_validator(mode="after")
    def ensure_password_truncated(self):
        """Force truncation after model is built (catches any path where before-validator was skipped)."""
        self.password = _truncate_password_72_bytes(self.password)
        return self

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