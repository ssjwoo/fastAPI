# 거래 API 라우터: 생성/조회/수정/삭제 + 기본 필터
from fastapi import APIRouter, Depends, HTTPException, Query, Path, status  # FastAPI 유틸/데코레이터
from sqlalchemy.orm import Session                  # SQLAlchemy 세션 타입
from sqlalchemy import select                       # SELECT 쿼리 빌더
from datetime import date                           # 날짜 타입
from app.db.session import get_db                   # DB 세션 의존성 (A 파트 제공)
from app.models.transaction import Transaction      # 거래 모델
from app.schemas.transaction import (
    TransactionCreate, TransactionUpdate, TransactionOut
)                                                   # Pydantic 스키마
from app.dependencies.auth import get_current_user  # 현재 로그인 사용자
from app.models.user import User                    # User 타입 힌트용
from app.models.account import Account              # 소유권 검증용 (FK 없이도 읽어옴)
from app.models.category import Category            # 소유권 검증용

router = APIRouter(prefix="/transactions", tags=["Transactions"])  # /transactions 라우터

def ensure_account_owned(db: Session, user_id: int, account_id: int):
    """
    주어진 account_id가 현재 사용자(user_id)의 것인지 확인.
    FK 제약이 없으므로 '코드'로 소유권 검증을 수행한다.
    """
    row = db.get(Account, account_id)
    if not row or row.user_id != user_id:
        # 계정이 없거나 남의 계정이면 404로 은닉
        raise HTTPException(404, "Account not found")

def ensure_category_owned(db: Session, user_id: int, category_id: int):
    """
    주어진 category_id가 현재 사용자(user_id)의 것인지 확인.
    """
    row = db.get(Category, category_id)
    if not row or row.user_id != user_id:
        raise HTTPException(404, "Category not found")

@router.post("", response_model=TransactionOut, status_code=status.HTTP_201_CREATED)
def create_txn(
    body: TransactionCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    거래 생성:
    1) account/category 소유권 검증
    2) DB에 추가 후 커밋
    3) 생성된 레코드 반환
    """
    ensure_account_owned(db, user.id, body.account_id)
    ensure_category_owned(db, user.id, body.category_id)

    txn = Transaction(**body.model_dump())  # Pydantic → dict → 모델 생성
    db.add(txn)
    db.commit()
    db.refresh(txn)  # 생성된 PK(id) 반영
    return txn

@router.get("", response_model=list[TransactionOut])
def list_txn(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    from_: date | None = Query(None, alias="from"),  # 'from'은 예약어라 alias 사용
    to: date | None = None,
    min: float | None = None,       # 금액 하한
    max: float | None = None,       # 금액 상한
    account_id: int | None = None,  # 특정 계정 필터
    category_id: int | None = None, # 특정 카테고리 필터
    keyword: str | None = None,     # 메모 키워드
    page: int = 1,                  # 페이지 번호(1부터)
    size: int = 50,                 # 페이지 크기
    sort: str = "occurred_on",      # 정렬 컬럼: "occurred_on" 또는 "-amount" 같은 형태
):
    """
    거래 목록 조회:
    - 내 소유의 accounts/categories만 대상으로 제한(IN 필터)
    - 날짜/금액/계정/카테고리/키워드 필터
    - 정렬/페이지네이션 지원
    """
    q = select(Transaction)

    # 내 소유 자원으로 범위를 좁힌다 (FK가 없으므로 별도의 IN 서브쿼리 필요)
    acct_ids = db.scalars(select(Account.id).where(Account.user_id == user.id)).all()
    cat_ids  = db.scalars(select(Category.id).where(Category.user_id == user.id)).all()
    if not acct_ids or not cat_ids:
        # 소유한 계정/카테고리가 없다면 결과 없음
        return []

    q = q.where(
        Transaction.account_id.in_(acct_ids),
        Transaction.category_id.in_(cat_ids),
    )

    # 기간 필터
    if from_:
        q = q.where(Transaction.occurred_on >= from_)
    if to:
        q = q.where(Transaction.occurred_on <= to)

    # 금액 범위
    if min is not None:
        q = q.where(Transaction.amount >= min)
    if max is not None:
        q = q.where(Transaction.amount <= max)

    # 특정 계정/카테고리만 (있다면 소유권도 재확인)
    if account_id is not None:
        ensure_account_owned(db, user.id, account_id)
        q = q.where(Transaction.account_id == account_id)
    if category_id is not None:
        ensure_category_owned(db, user.id, category_id)
        q = q.where(Transaction.category_id == category_id)

    # 메모 키워드 (ILIKE: 대소문자 무시. 일부 DB에서는 ilike 대신 like를 사용)
    if keyword:
        q = q.where(Transaction.description.ilike(f"%{keyword}%"))

    # 정렬: "occurred_on" 또는 "-amount" 형태 지원
    desc = sort.startswith("-")
    col = sort.removeprefix("-")
    sort_col = getattr(Transaction, col, Transaction.occurred_on)  # 컬럼명 보호
    q = q.order_by(sort_col.desc() if desc else sort_col.asc())

    # 페이지네이션
    q = q.offset((page - 1) * size).limit(size)

    rows = db.scalars(q).all()
    return rows

@router.patch("/{txn_id}", response_model=TransactionOut)
def update_txn(
    txn_id: int = Path(...),                 # 경로 파라미터
    body: TransactionUpdate = ...,           # 부분 업데이트 바디
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    거래 수정:
    - 대상 거래 존재 확인
    - 기존/변경 계정·카테고리가 모두 내 소유인지 검증
    - 전달된 필드만 업데이트
    """
    txn = db.get(Transaction, txn_id)
    if not txn:
        raise HTTPException(404, "Transaction not found")

    # 기존 값이 남의 자원일 수도 있으니 먼저 검증
    ensure_account_owned(db, user.id, txn.account_id)
    ensure_category_owned(db, user.id, txn.category_id)

    # 변경하려는 값이 있다면 그것도 검증
    if body.account_id is not None:
        ensure_account_owned(db, user.id, body.account_id)
    if body.category_id is not None:
        ensure_category_owned(db, user.id, body.category_id)

    # 들어온 필드만 반영
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
    """
    거래 삭제:
    - 대상 존재 확인
    - 소유권 검증
    - 삭제 후 204 반환
    """
    txn = db.get(Transaction, txn_id)
    if not txn:
        raise HTTPException(404, "Transaction not found")

    ensure_account_owned(db, user.id, txn.account_id)
    ensure_category_owned(db, user.id, txn.category_id)

    db.delete(txn)
    db.commit()
    return None  # 204 No Content
