# Category API - 핵심 구현
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from app.core.database import get_db
from app.models.category import Category
from app.schemas.category import CategoryCreate, CategoryUpdate, CategoryResponse

router = APIRouter(prefix="/categories", tags=["categories"])

# 카테고리 생성 API
@router.post("/", response_model=CategoryResponse)
def create_category(category: CategoryCreate, db: Session = Depends(get_db)):
    user_id = 1  # 실제로는 JWT에서 가져와야 함
    
    # 중복 카테고리 체크
    existing = db.query(Category).filter(
        Category.user_id == user_id,
        Category.name == category.name,
        Category.type == category.type
    ).first()
    
    if existing:
        raise HTTPException(status_code=409, detail="이미 존재하는 카테고리입니다")
    
    db_category = Category(
        user_id=user_id,
        name=category.name,
        type=category.type
    )
    db.add(db_category)
    db.commit()
    db.refresh(db_category)
    return db_category

# 카테고리 목록 조회 API (타입별 필터링)
@router.get("/", response_model=List[CategoryResponse])
def get_categories(
    type: Optional[str] = None,
    db: Session = Depends(get_db)
):
    user_id = 1  # 실제로는 JWT에서 가져와야 함
    
    query = db.query(Category).filter(Category.user_id == user_id)
    
    # 타입으로 필터링
    if type:
        query = query.filter(Category.type == type)
    
    return query.all()

# 특정 카테고리 조회 API
@router.get("/{category_id}", response_model=CategoryResponse)
def get_category(category_id: int, db: Session = Depends(get_db)):
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="카테고리를 찾을 수 없습니다")
    return category

# 카테고리 수정 API
@router.patch("/{category_id}", response_model=CategoryResponse)
def update_category(
    category_id: int,
    category_update: CategoryUpdate,
    db: Session = Depends(get_db)
):
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="카테고리를 찾을 수 없습니다")
    
    # 업데이트할 필드만 수정
    if category_update.name is not None:
        category.name = category_update.name
    if category_update.type is not None:
        category.type = category_update.type
    
    db.commit()
    db.refresh(category)
    return category

# 카테고리 삭제 API
@router.delete("/{category_id}")
def delete_category(category_id: int, db: Session = Depends(get_db)):
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="카테고리를 찾을 수 없습니다")
    
    db.delete(category)
    db.commit()
    return {"message": "카테고리가 삭제되었습니다"}
