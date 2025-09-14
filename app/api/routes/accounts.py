from fastapi import APIRouter, Depends, HTTPException, Query, Path, status
from sqlalchemy.orm import Session
from sqlalchemy import select, func

from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.models.account import Account
from app.models.transaction import Transaction
from app.schemas.accounts import AccountCreate, AccountUpdate, AccountOut

router = APIRouter(prefix="/accounts", tags=["Accounts"])

def ensure_account_owned(db: Session, user_id: int, account_id: int) -> Account:
    row = db.get(Account, account_id)
    if not row or row.user_id != user_id:
        raise HTTPException(404, "Account not found")
    return row

@router.post("", response_model=AccountOut, status_code=status.HTTP_201_CREATED)
def create_account(
    body: AccountCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    # 같은 사용자 내 이름 중복 방지(선택)
    dup = db.scalar(
        select(func.count()).where(
            Account.user_id == user.id,
            Account.account_name == body.account_name,
        )
    )
    if dup:
        raise HTTPException(409, "Account name already exists")
    row = Account(user_id=user.id, account_name=body.account_name, balance=body.balance)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row

@router.get("", response_model=list[AccountOut])
def list_accounts(
    q: str | None = Query(None, description="이름 검색"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    stmt = select(Account).where(Account.user_id == user.id)
    if q:
        stmt = stmt.where(Account.account_name.ilike(f"%{q}%"))
    return db.scalars(stmt.order_by(Account.account_name.asc())).all()

@router.get("/{account_id}", response_model=AccountOut)
def get_account(
    account_id: int = Path(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return ensure_account_owned(db, user.id, account_id)

@router.patch("/{account_id}", response_model=AccountOut)
def update_account(
    account_id: int,
    body: AccountUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    row = ensure_account_owned(db, user.id, account_id)
    data = body.model_dump(exclude_unset=True)

    if "account_name" in data:
        dup = db.scalar(
            select(func.count()).where(
                Account.user_id == user.id,
                Account.account_name == data["account_name"],
                Account.id != row.id,
            )
        )
        if dup:
            raise HTTPException(409, "Account name already exists")

    for k, v in data.items():
        setattr(row, k, v)

    db.commit()
    db.refresh(row)
    return row

@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_account(
    account_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    row = ensure_account_owned(db, user.id, account_id)
    # FK가 없으므로 수동 참조 점검(거래가 참조 중이면 409)
    in_use = db.scalar(select(func.count()).where(Transaction.account_id == row.id))
    if in_use:
        raise HTTPException(409, "Account is referenced by transactions")
    db.delete(row)
    db.commit()
    return None
