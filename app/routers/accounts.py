# Account API - 핵심 구현
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from app.core.database import get_db
from app.models.account import Account
from app.schemas.account import AccountCreate, AccountUpdate, AccountResponse

router = APIRouter(prefix="/accounts", tags=["accounts"])

# 계정 생성 API
@router.post("/", response_model=AccountResponse)
def create_account(account: AccountCreate, db: Session = Depends(get_db)):
    # 실제로는 JWT에서 user_id를 가져와야 하지만, 지금은 간단히 1로 설정
    user_id = 1
    
    db_account = Account(
        user_id=user_id,
        name=account.name,
        type=account.type
    )
    db.add(db_account)
    db.commit()
    db.refresh(db_account)
    return db_account

# 특정 계정 조회 API
@router.get("/{account_id}", response_model=AccountResponse)
def get_account(account_id: int, db: Session = Depends(get_db)):
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="계정을 찾을 수 없습니다")
    return account

# 계정 목록 조회 API (검색 기능 포함)
@router.get("/", response_model=List[AccountResponse])
def get_accounts(
    type: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db)
):
    user_id = 1  # 실제로는 JWT에서 가져와야 함
    
    query = db.query(Account).filter(Account.user_id == user_id)
    
    # 타입으로 필터링
    if type:
        query = query.filter(Account.type == type)
    
    # 이름으로 검색
    if search:
        query = query.filter(Account.name.contains(search))
    
    return query.all()

# 계정 수정 API
@router.patch("/{account_id}", response_model=AccountResponse)
def update_account(
    account_id: int,
    account_update: AccountUpdate,
    db: Session = Depends(get_db)
):
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="계정을 찾을 수 없습니다")
    
    # 업데이트할 필드만 수정
    if account_update.name is not None:
        account.name = account_update.name
    if account_update.type is not None:
        account.type = account_update.type
    
    db.commit()
    db.refresh(account)
    return account

# 계정 삭제 API
@router.delete("/{account_id}")
def delete_account(account_id: int, db: Session = Depends(get_db)):
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="계정을 찾을 수 없습니다")
    
    db.delete(account)
    db.commit()
    return {"message": "계정이 삭제되었습니다"}
