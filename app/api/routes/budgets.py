from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.models.budget import Budget  # == Goal 모델(파일명만 다를 수 있음)
from app.models.category import Category
from app.schemas.budgets import BudgetCreate, BudgetUpdate, BudgetOut

router = APIRouter(prefix="/budgets", tags=["Budgets"])

def ensure_category_owned(db: Session, user_id: int, category_id: int):
    row = db.get(Category, category_id)
    if not row or row.user_id != user_id:
        raise HTTPException(404, "Category not found")

@router.post("", response_model=BudgetOut, status_code=status.HTTP_201_CREATED)
def create_budget(
    body: BudgetCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    ensure_category_owned(db, user.id, body.category_id)

    budget = Budget(
        user_id=user.id,
        category_id=body.category_id,
        month=body.month,
        monthly_limit=body.monthly_limit,
    )
    db.add(budget)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(409, "Budget already exists for this month and category")
    db.refresh(budget)
    return budget

@router.get("", response_model=list[BudgetOut])
def list_budgets(
    month: str | None = Query(None, pattern=r"^\d{4}-\d{2}$"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    q = select(Budget).where(Budget.user_id == user.id)
    if month:
        q = q.where(Budget.month == month)
    return db.scalars(q.order_by(Budget.month.asc())).all()

@router.patch("/{budget_id}", response_model=BudgetOut)
def update_budget(
    budget_id: int,
    body: BudgetUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    budget = db.get(Budget, budget_id)
    if not budget or budget.user_id != user.id:
        raise HTTPException(404, "Budget not found")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(budget, k, v)
    db.commit()
    db.refresh(budget)
    return budget

@router.delete("/{budget_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_budget(
    budget_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    budget = db.get(Budget, budget_id)
    if not budget or budget.user_id != user.id:
        raise HTTPException(404, "Budget not found")
    db.delete(budget)
    db.commit()
    return None
