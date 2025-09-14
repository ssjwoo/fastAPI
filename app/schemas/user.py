from pydantic import BaseModel, EmailStr

# 회원가입
class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str

# 응답 (비번제외)
class UserOut(BaseModel):
    user_id: int
    user_name: str
    email: EmailStr

    class Config:
        from_attributes = True
