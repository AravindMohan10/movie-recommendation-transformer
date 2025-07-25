from pydantic import BaseModel, EmailStr, field_validator

def _validate_password_byte_length(v) -> str:
    """Validate password byte length (bcrypt limit: 72 bytes). Reject if too long."""
    if isinstance(v, bytes):
        v = v.decode("utf-8", errors="ignore")
    if not isinstance(v, str):
        v = str(v) if v is not None else ""
    byte_length = len(v.encode("utf-8"))
    if byte_length > 72:
        raise ValueError(
            f"Password is too long. Maximum 72 bytes (your password is {byte_length} bytes). "
            "Use at most 64 characters to be safe."
        )
    return v

class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str

    @field_validator("password", mode="before")
    @classmethod
    def validate_password_length(cls, v) -> str:
        return _validate_password_byte_length(v)

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
    def validate_new_password_length(cls, v: str) -> str:
        return _validate_password_byte_length(v)