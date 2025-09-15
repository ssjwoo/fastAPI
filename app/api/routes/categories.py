from fastapi import APIRouter, Depends, HTTPException, Query, Path, status
from sqlalchemy.orm import Session
from sqlalchemy import select, func

from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.models.category import Category
from app.models.transaction import Transaction
from app.schemas.categories import CategoryCreate, CategoryUpdate, CategoryOut

# Budget/Goal 모델명 어느 쪽이든 대응
try:
    from app.models.budget import Budget  # 있으면 사용
except Exception:
    try:
        from app.models.goal import Goal as Budget  # goal로 되어 있으면 alias
    except Exception:
        Budget = None  # 없으면 참조 점검 생략

router = APIRouter(prefix="/categories", tags=["Categories"])

def ensure_category_owned(db: Session, user_id: int, category_id: int) -> Category:
    row = db.get(Category, category_id)
    if not row or row.user_id != user_id:
        raise HTTPException(404, "Category not found")
    return row

@router.post("", response_model=CategoryOut, status_code=status.HTTP_201_CREATED)
def create_category(
    body: CategoryCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if body.type not in ("income", "expense"):
        raise HTTPException(422, "type must be 'income' or 'expense'")
    # 사용자 내 (name, type) 유니크
    dup = db.scalar(
        select(func.count()).where(
            Category.user_id == user.id,
            Category.name == body.name,
            Category.type == body.type,
        )
    )
    if dup:
        raise HTTPException(409, "Category already exists")

    row = Category(user_id=user.id, name=body.name, type=body.type)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row

@router.get("", response_model=list[CategoryOut])
def list_categories(
    type: str | None = Query(None, description="'income' 또는 'expense'"),
    q: str | None = Query(None, description="이름 검색"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    stmt = select(Category).where(Category.user_id == user.id)
    if type:
        stmt = stmt.where(Category.type == type)
    if q:
        stmt = stmt.where(Category.name.ilike(f"%{q}%"))
    return db.scalars(stmt.order_by(Category.name.asc())).all()

@router.get("/{category_id}", response_model=CategoryOut)
def get_category(
    category_id: int = Path(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return ensure_category_owned(db, user.id, category_id)

@router.patch("/{category_id}", response_model=CategoryOut)
def update_category(
    category_id: int,
    body: CategoryUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    row = ensure_category_owned(db, user.id, category_id)
    data = body.model_dump(exclude_unset=True)

    new_name = data.get("name", row.name)
    new_type = data.get("type", row.type)
    if new_type not in ("income", "expense"):
        raise HTTPException(422, "type must be 'income' or 'expense'")

    dup = db.scalar(
        select(func.count()).where(
            Category.user_id == user.id,
            Category.name == new_name,
            Category.type == new_type,
            Category.id != row.id,
        )
    )
    if dup:
        raise HTTPException(409, "Category already exists")

    for k, v in data.items():
        setattr(row, k, v)

    db.commit()
    db.refresh(row)
    return row

@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(
    category_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    row = ensure_category_owned(db, user.id, category_id)

    # FK 없음 → 수동 참조 점검(거래/예산이 참조 중이면 409)
    in_txn = db.scalar(select(func.count()).where(Transaction.category_id == row.id))
    in_budget = 0
    if Budget is not None:
        in_budget = db.scalar(select(func.count()).where(Budget.category_id == row.id))
    if in_txn or in_budget:
        raise HTTPException(409, "Category is referenced by other resources")

    db.delete(row)
    db.commit()
    return None
