# Account 스키마
from pydantic import BaseModel
from typing import Optional

# 계정 생성
class AccountCreate(BaseModel):
    name: str
    type: str

# 계정 수정
class AccountUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None

# 계정 정보
class AccountResponse(BaseModel):
    id: int
    user_id: int
    name: str
    type: str
    
    class Config:
        from_attributes = True
