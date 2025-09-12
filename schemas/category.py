# Category 스키마
from pydantic import BaseModel
from typing import Optional

# 카테고리 생성
class CategoryCreate(BaseModel):
    name: str
    type: str

# 카테고리 수정
class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None

# 카테고리 정보
class CategoryResponse(BaseModel):
    id: int
    user_id: int
    name: str
    type: str
    
    class Config:
        from_attributes = True
