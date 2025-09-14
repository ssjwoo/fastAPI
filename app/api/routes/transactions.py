from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.models.transaction import Transaction
from app.models.account import Account
from app.models.category import Category
from app.schemas.transactions import (
    TransactionCreate, TransactionUpdate, TransactionOut
)

router = APIRouter(prefix="/transactions", tags=["Transactions"])

def ensure_account_owned(db: Session, user_id: int, account_id: int):
    row = db.get(Account, account_id)
    if not row or row.user_id != user_id:
        raise HTTPException(404, "Account not found")

def ensure_category_owned(db: Session, user_id: int, category_id: int):
    row = db.get(Category, category_id)
    if not row or row.user_id != user_id:
        raise HTTPException(404, "Category not found")

@router.post("", response_model=TransactionOut, status_code=status.HTTP_201_CREATED)
def create_txn(
    body: TransactionCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    ensure_account_owned(db, user.id, body.account_id)
    ensure_category_owned(db, user.id, body.category_id)

    txn = Transaction(**body.model_dump())
    db.add(txn)
    db.commit()
    db.refresh(txn)
    return txn

@router.get("", response_model=list[TransactionOut])
def list_txn(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    from_: date | None = Query(None, alias="from"),
    to: date | None = None,
    min: float | None = None,
    max: float | None = None,
    account_id: int | None = None,
    category_id: int | None = None,
    keyword: str | None = None,
    page: int = 1,
    size: int = 50,
    sort: str = "occurred_on",  # "-amount" 허용
):
    q = select(Transaction)

    # 내 소유 account/category 범위로 제한 (FK 없으므로 IN 사용)
    acct_ids = db.scalars(select(Account.id).where(Account.user_id == user.id)).all()
    cat_ids = db.scalars(select(Category.id).where(Category.user_id == user.id)).all()
    if not acct_ids or not cat_ids:
        return []

    q = q.where(Transaction.account_id.in_(acct_ids), Transaction.category_id.in_(cat_ids))
    if from_:
        q = q.where(Transaction.occurred_on >= from_)
    if to:
        q = q.where(Transaction.occurred_on <= to)
    if min is not None:
        q = q.where(Transaction.amount >= min)
    if max is not None:
        q = q.where(Transaction.amount <= max)
    if account_id is not None:
        ensure_account_owned(db, user.id, account_id)
        q = q.where(Transaction.account_id == account_id)
    if category_id is not None:
        ensure_category_owned(db, user.id, category_id)
        q = q.where(Transaction.category_id == category_id)
    if keyword:
        q = q.where(Transaction.description.ilike(f"%{keyword}%"))

    # 정렬
    desc = sort.startswith("-")
    col = sort.removeprefix("-")
    sort_col = getattr(Transaction, col, Transaction.occurred_on)
    q = q.order_by(sort_col.desc() if desc else sort_col.asc())

    # 페이지네이션
    q = q.offset((page - 1) * size).limit(size)

    return db.scalars(q).all()

@router.patch("/{txn_id}", response_model=TransactionOut)
def update_txn(
    txn_id: int = Path(...),
    body: TransactionUpdate = ...,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    txn = db.get(Transaction, txn_id)
    if not txn:
        raise HTTPException(404, "Transaction not found")

    # 기존/변경 account/category 모두 소유권 체크
    ensure_account_owned(db, user.id, txn.account_id)
    ensure_category_owned(db, user.id, txn.category_id)
    if body.account_id is not None:
        ensure_account_owned(db, user.id, body.account_id)
    if body.category_id is not None:
        ensure_category_owned(db, user.id, body.category_id)

    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(txn, k, v)

    db.commit()
    db.refresh(txn)
    return txn

@router.delete("/{txn_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_txn(
    txn_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    txn = db.get(Transaction, txn_id)
    if not txn:
        raise HTTPException(404, "Transaction not found")

    ensure_account_owned(db, user.id, txn.account_id)
    ensure_category_owned(db, user.id, txn.category_id)

    db.delete(txn)
    db.commit()
    return None
