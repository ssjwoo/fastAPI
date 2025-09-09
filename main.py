아래는 **리포트 API 3종 + CSV 다운로드**까지 포함한 **완성 단일 파일**입니다.

* 기존 MVP(회원가입/로그인, 계좌/카테고리/거래/예산 CRUD, 월별 예산 요약)에 더해
* `/reports/summary`, `/reports/budget-status`, `/reports/summary.csv`를 추가했고
* 거래 조회에 **금액/날짜 범위 필터**도 넣었습니다.

> 실행 전 설치: `pip install fastapi "uvicorn[standard]" sqlalchemy passlib[bcrypt] python-jose[cryptography]`
>
> 실행: `uvicorn main:app --reload`

---

## main.py (리포트 3종 + CSV 포함, 한 파일 완성본)

```python
"""
가계부 백엔드 — 리포트 3종 + CSV 확장 (Single-file 완성본)
========================================================
✓ 회원가입/로그인(JWT)
✓ 계좌/카테고리/거래/예산 CRUD
✓ 거래 조회 필터(월/계좌/카테고리 + 금액/날짜 범위)
✓ 월별 예산 요약(/budgets/summary)
✓ 리포트 3종
   - /reports/summary?month=YYYY-MM  → 총수입/총지출, 카테고리별 합계
   - /reports/budget-status?month=YYYY-MM → 예산 대비 사용률(%)
   - /reports/summary.csv?month=YYYY-MM → CSV 다운로드

학습 포인트(왕초보 설명):
- **입력은 모두 양수**로 받고, 증/감은 카테고리의 `type(income|expense)`가 결정합니다.
- **돈은 반쪽만 바뀌면 큰일**: 거래와 잔액을 **같은 DB 트랜잭션**에서 처리합니다.
- **리포트**는 이미 저장된 거래/예산을 **합계/묶음**으로 계산해 응답으로 보여줍니다.
"""

from datetime import datetime, timedelta, date
from typing import Optional, List
from decimal import Decimal, ROUND_HALF_UP
import io, csv

from fastapi import FastAPI, Depends, HTTPException, status, Query, Path
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from jose import JWTError, jwt
from passlib.context import CryptContext

from sqlalchemy import (
    create_engine, Column, Integer, String, Date, DateTime, Numeric,
    ForeignKey, CheckConstraint, UniqueConstraint, func, select
)
from sqlalchemy.orm import sessionmaker, declarative_base, relationship, Session

# ==========================
# 0) 기본 설정 (비밀키/DB)
# ==========================
SECRET_KEY = "change_me_please"                 # ⚠️ 실제 서비스에서는 환경변수로 긴 랜덤값 사용
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24시간

# SQLite(로컬 테스트) — 파일 하나로 바로 동작
DATABASE_URL = "sqlite:///./app.db"
# MySQL 예시: mysql+pymysql://user:password@localhost:3306/ledger

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

# DB 세션 DI
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ==========================
# 1) 유틸: 암호/토큰
# ==========================

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# ==========================
# 2) SQLAlchemy 모델(테이블)
# ==========================
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False, default="user")

    accounts = relationship("Account", back_populates="user", cascade="all, delete-orphan")
    categories = relationship("Category", back_populates="user", cascade="all, delete-orphan")
    budgets = relationship("Budget", back_populates="user", cascade="all, delete-orphan")


class Account(Base):
    __tablename__ = "accounts"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    account_name = Column(String(50), nullable=False)
    balance = Column(Numeric(14, 2), nullable=False, default=0)

    user = relationship("User", back_populates="accounts")
    transactions = relationship("Transaction", back_populates="account", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("user_id", "account_name", name="uq_user_accountname"),
    )


class Category(Base):
    __tablename__ = "categories"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(50), nullable=False)
    type = Column(String(8), nullable=False)  # 'income' | 'expense'

    user = relationship("User", back_populates="categories")
    transactions = relationship("Transaction", back_populates="category")

    __table_args__ = (
        CheckConstraint("type in ('income','expense')", name="ck_category_type"),
        UniqueConstraint("user_id", "name", name="uq_user_categoryname"),
    )


class Transaction(Base):
    __tablename__ = "transactions"
    id = Column(Integer, primary_key=True)
    account_id = Column(Integer, ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False, index=True)
    category_id = Column(Integer, ForeignKey("categories.id", ondelete="RESTRICT"), nullable=False, index=True)
    amount = Column(Numeric(14, 2), nullable=False)  # 항상 양수 저장
    description = Column(String(255), nullable=False, default="")
    date = Column(Date, nullable=False, index=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    account = relationship("Account", back_populates="transactions")
    category = relationship("Category", back_populates="transactions")


class Budget(Base):
    __tablename__ = "budgets"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    category_id = Column(Integer, ForeignKey("categories.id", ondelete="CASCADE"), nullable=False, index=True)
    month = Column(String(7), nullable=False)  # 'YYYY-MM'
    amount = Column(Numeric(14, 2), nullable=False)

    user = relationship("User", back_populates="budgets")
    category = relationship("Category")

    __table_args__ = (
        UniqueConstraint("user_id", "category_id", "month", name="uq_budget_unique"),
    )


Base.metadata.create_all(bind=engine)

# ==========================
# 3) Pydantic 스키마 (입/출력)
# ==========================
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=30)
    email: EmailStr
    password: str = Field(min_length=6)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    username: str
    email: EmailStr
    role: str


class AccountCreate(BaseModel):
    account_name: str = Field(min_length=1, max_length=50)
    balance: Decimal = 0


class AccountOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    account_name: str
    balance: Decimal


class CategoryCreate(BaseModel):
    name: str
    type: str = Field(pattern="^(income|expense)$")


class CategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    type: str


class TransactionCreate(BaseModel):
    account_id: int
    category_id: int
    amount: Decimal = Field(gt=0)
    description: Optional[str] = ""
    date: date


class TransactionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    account_id: int
    category_id: int
    amount: Decimal
    description: str
    date: date


class BudgetCreate(BaseModel):
    category_id: int
    month: str = Field(pattern=r"^\d{4}-\d{2}$")  # YYYY-MM
    amount: Decimal = Field(ge=0)


class BudgetOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    category_id: int
    month: str
    amount: Decimal


class BudgetSummaryItem(BaseModel):
    category_id: int
    category_name: str
    budget: Decimal
    spent: Decimal
    diff: Decimal  # budget - spent (음수면 초과)


# 리포트 응답 스키마
class ReportCategoryTotal(BaseModel):
    category_id: int
    category_name: str
    type: str  # 'income' | 'expense'
    total: Decimal


class ReportSummary(BaseModel):
    month: str
    total_income: Decimal
    total_expense: Decimal
    net: Decimal  # income - expense
    breakdown: List[ReportCategoryTotal]


class BudgetStatusItem(BaseModel):
    category_id: int
    category_name: str
    budget: Decimal
    spent: Decimal
    diff: Decimal
    usage_rate: float  # 0~100 (%)


# ==========================
# 4) 인증 관련 DI (현재 사용자)
# ==========================

def get_current_user(db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        sub = payload.get("sub")
        if sub is None:
            raise credentials_exception
        user_id = int(sub)
    except (JWTError, ValueError):
        raise credentials_exception

    user = db.get(User, user_id)
    if not user:
        raise credentials_exception
    return user


# ==========================
# 5) FastAPI 앱 생성
# ==========================
app = FastAPI(title="Personal Ledger API — Reports Edition")

# ---------------------------------
# 5-1) Auth: 회원가입/로그인
# ---------------------------------
@app.post("/auth/register", response_model=UserOut, tags=["auth"])
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    exists = db.execute(
        select(User).where((User.username == user_in.username) | (User.email == user_in.email))
    ).scalar_one_or_none()
    if exists:
        raise HTTPException(status_code=400, detail="Username or email already registered")

    user = User(
        username=user_in.username,
        email=user_in.email,
        password_hash=get_password_hash(user_in.password),
        role="user",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@app.post("/auth/login", response_model=Token, tags=["auth"])
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.execute(select(User).where(User.username == form_data.username)).scalar_one_or_none()
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    access_token = create_access_token({"sub": str(user.id)})
    return {"access_token": access_token, "token_type": "bearer"}


# ---------------------------------
# 5-2) Account CRUD
# ---------------------------------
@app.post("/accounts", response_model=AccountOut, status_code=201, tags=["accounts"])
def create_account(acc_in: AccountCreate, db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    dup = db.execute(
        select(Account).where(Account.user_id == current.id, Account.account_name == acc_in.account_name)
    ).scalar_one_or_none()
    if dup:
        raise HTTPException(status_code=400, detail="Account name already exists")

    acc = Account(user_id=current.id, account_name=acc_in.account_name, balance=acc_in.balance)
    db.add(acc)
    db.commit()
    db.refresh(acc)
    return acc


@app.get("/accounts", response_model=List[AccountOut], tags=["accounts"])
def list_accounts(db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    rows = db.execute(select(Account).where(Account.user_id == current.id).order_by(Account.id)).scalars().all()
    return rows


@app.delete("/accounts/{account_id}", status_code=204, tags=["accounts"])
def delete_account(account_id: int = Path(ge=1), db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    acc = db.get(Account, account_id)
    if not acc or acc.user_id != current.id:
        raise HTTPException(status_code=404, detail="Account not found")
    db.delete(acc)
    db.commit()
    return None


# ---------------------------------
# 5-3) Category CRUD
# ---------------------------------
@app.post("/categories", response_model=CategoryOut, status_code=201, tags=["categories"])
def create_category(cat_in: CategoryCreate, db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    dup = db.execute(
        select(Category).where(Category.user_id == current.id, Category.name == cat_in.name)
    ).scalar_one_or_none()
    if dup:
        raise HTTPException(status_code=400, detail="Category name already exists")

    cat = Category(user_id=current.id, name=cat_in.name, type=cat_in.type)
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return cat


@app.get("/categories", response_model=List[CategoryOut], tags=["categories"])
def list_categories(db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    rows = db.execute(select(Category).where(Category.user_id == current.id).order_by(Category.id)).scalars().all()
    return rows


# ---------------------------------
# 5-4) Transaction CRUD (잔액 동기화 + 필터)
# ---------------------------------

def _assert_own_account(db: Session, user_id: int, account_id: int) -> Account:
    acc = db.get(Account, account_id)
    if not acc or acc.user_id != user_id:
        raise HTTPException(status_code=404, detail="Account not found")
    return acc


def _assert_own_category(db: Session, user_id: int, category_id: int) -> Category:
    cat = db.get(Category, category_id)
    if not cat or cat.user_id != user_id:
        raise HTTPException(status_code=404, detail="Category not found")
    return cat


def _apply_balance(account: Account, category: Category, amount: Decimal, reverse: bool = False):
    """계좌 잔액 변경 로직
    - amount는 항상 양수로 들어온다고 가정
    - category.type == 'expense'면 잔액 감소, 'income'이면 증가
    - reverse=True면 반대로 적용(삭제/롤백 시)
    """
    sign = Decimal(-1) if category.type == "expense" else Decimal(1)
    if reverse:
        sign = -sign
    account.balance = (account.balance or Decimal(0)) + (sign * amount)


@app.post("/transactions", response_model=TransactionOut, status_code=201, tags=["transactions"])
def create_transaction(tx_in: TransactionCreate, db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    acc = _assert_own_account(db, current.id, tx_in.account_id)
    cat = _assert_own_category(db, current.id, tx_in.category_id)

    tx = Transaction(
        account_id=acc.id,
        category_id=cat.id,
        amount=tx_in.amount,
        description=tx_in.description or "",
        date=tx_in.date,
    )
    db.add(tx)
    _apply_balance(acc, cat, tx_in.amount, reverse=False)

    db.commit()
    db.refresh(tx)
    return tx


@app.get("/transactions", response_model=List[TransactionOut], tags=["transactions"])
def list_transactions(
    month: Optional[str] = Query(default=None, pattern=r"^\d{4}-\d{2}$"),
    account_id: Optional[int] = None,
    category_id: Optional[int] = None,
    amount_min: Optional[Decimal] = Query(default=None, ge=0),
    amount_max: Optional[Decimal] = Query(default=None, ge=0),
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    """거래 목록 + 다양한 필터
    - month가 있으면 month 기준으로, 없으면 start_date~end_date 범위 사용
    - amount_min/max로 금액 범위 필터
    - 항상 내 계좌(내 user_id) 범위에서만 검색
    """
    q = select(Transaction).join(Account).where(Account.user_id == current.id)

    if account_id is not None:
        q = q.where(Transaction.account_id == account_id)
    if category_id is not None:
        q = q.where(Transaction.category_id == category_id)

    # 날짜 필터: month 우선, 없으면 start/end 사용
    if month:
        start, end = _month_range(month)
        q = q.where(Transaction.date >= start, Transaction.date < end)
    else:
        if start_date:
            q = q.where(Transaction.date >= start_date)
        if end_date:
            q = q.where(Transaction.date < end_date)

    if amount_min is not None:
        q = q.where(Transaction.amount >= amount_min)
    if amount_max is not None:
        q = q.where(Transaction.amount <= amount_max)

    q = q.order_by(Transaction.date.desc(), Transaction.id.desc()).limit(limit).offset(offset)
    rows = db.execute(q).scalars().all()
    return rows


@app.delete("/transactions/{tx_id}", status_code=204, tags=["transactions"])
def delete_transaction(tx_id: int, db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    tx = db.get(Transaction, tx_id)
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")
    if tx.account.user_id != current.id:
        raise HTTPException(status_code=403, detail="Forbidden")

    _apply_balance(tx.account, tx.category, tx.amount, reverse=True)
    db.delete(tx)
    db.commit()
    return None


class TransactionUpdate(BaseModel):
    amount: Optional[Decimal] = Field(default=None, gt=0)
    description: Optional[str] = None
    date: Optional[date] = None
    category_id: Optional[int] = None
    account_id: Optional[int] = None


@app.patch("/transactions/{tx_id}", response_model=TransactionOut, tags=["transactions"])
def update_transaction(tx_id: int, patch: TransactionUpdate, db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    tx = db.get(Transaction, tx_id)
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")
    if tx.account.user_id != current.id:
        raise HTTPException(status_code=403, detail="Forbidden")

    old_acc = tx.account
    old_cat = tx.category
    old_amount = tx.amount

    new_acc = old_acc
    new_cat = old_cat

    if patch.account_id is not None:
        new_acc = _assert_own_account(db, current.id, patch.account_id)
    if patch.category_id is not None:
        new_cat = _assert_own_category(db, current.id, patch.category_id)

    # 1) 옛 값 롤백
    _apply_balance(old_acc, old_cat, old_amount, reverse=True)

    # 2) 새로운 값 적용
    new_amount = patch.amount if patch.amount is not None else old_amount

    tx.account = new_acc
    tx.category = new_cat
    tx.amount = new_amount
    if patch.description is not None:
        tx.description = patch.description
    if patch.date is not None:
        tx.date = patch.date

    _apply_balance(new_acc, new_cat, new_amount, reverse=False)

    db.commit()
    db.refresh(tx)
    return tx


# ---------------------------------
# 5-5) Budget CRUD & 월별 요약(기존)
# ---------------------------------
@app.post("/budgets", response_model=BudgetOut, tags=["budgets"])
def upsert_budget(bu: BudgetCreate, db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    _assert_own_category(db, current.id, bu.category_id)

    row = db.execute(
        select(Budget).where(Budget.user_id == current.id, Budget.category_id == bu.category_id, Budget.month == bu.month)
    ).scalar_one_or_none()
    if row:
        row.amount = bu.amount
        db.commit(); db.refresh(row)
        return row
    else:
        row = Budget(user_id=current.id, category_id=bu.category_id, month=bu.month, amount=bu.amount)
        db.add(row); db.commit(); db.refresh(row)
        return row


@app.get("/budgets/summary", response_model=List[BudgetSummaryItem], tags=["budgets"])
def budget_summary(month: str = Query(pattern=r"^\d{4}-\d{2}$"), db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    start, end = _month_range(month)

    # 1) 해당 월 지출 합계(카테고리별, expense만)
    tx_sum = db.execute(
        select(
            Category.id.label("category_id"),
            Category.name.label("category_name"),
            func.coalesce(func.sum(Transaction.amount), 0).label("spent")
        )
        .join(Transaction, Transaction.category_id == Category.id, isouter=True)
        .join(Account, Account.id == Transaction.account_id, isouter=True)
        .where(Category.user_id == current.id, Category.type == "expense")
        .where((Transaction.date >= start) & (Transaction.date < end))
        .group_by(Category.id)
    ).all()

    spent_map = {row.category_id: Decimal(row.spent or 0) for row in tx_sum}

    # 2) 예산 불러오기(카테고리별)
    bu_rows = db.execute(
        select(Budget).where(Budget.user_id == current.id, Budget.month == month)
    ).scalars().all()
    bu_map = {b.category_id: Decimal(b.amount) for b in bu_rows}

    # 3) 결과: 내 모든 expense 카테고리 기준으로 병합
    cats = db.execute(
        select(Category).where(Category.user_id == current.id, Category.type == "expense").order_by(Category.name)
    ).scalars().all()

    result: List[BudgetSummaryItem] = []
    for c in cats:
        budget = bu_map.get(c.id, Decimal(0))
        spent = spent_map.get(c.id, Decimal(0))
        diff = budget - spent
        result.append(BudgetSummaryItem(
            category_id=c.id,
            category_name=c.name,
            budget=budget,
            spent=spent,
            diff=diff,
        ))

    return result


# ---------------------------------
# 5-6) Reports API 3종 + CSV
# ---------------------------------
@app.get("/reports/summary", response_model=ReportSummary, tags=["reports"])
def report_summary(month: str = Query(pattern=r"^\d{4}-\d{2}$"), db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    """월별 총수입/총지출 + 카테고리별 합계(수입/지출 모두)"""
    start, end = _month_range(month)

    # 총수입/총지출
    total_income = Decimal(
        db.execute(
            select(func.coalesce(func.sum(Transaction.amount), 0))
            .join(Category, Category.id == Transaction.category_id)
            .join(Account, Account.id == Transaction.account_id)
            .where(Account.user_id == current.id, Category.type == "income")
            .where(Transaction.date >= start, Transaction.date < end)
        ).scalar_one() or 0
    )

    total_expense = Decimal(
        db.execute(
            select(func.coalesce(func.sum(Transaction.amount), 0))
            .join(Category, Category.id == Transaction.category_id)
            .join(Account, Account.id == Transaction.account_id)
            .where(Account.user_id == current.id, Category.type == "expense")
            .where(Transaction.date >= start, Transaction.date < end)
        ).scalar_one() or 0
    )

    # 카테고리별 합계 (모든 카테고리 포함: 없으면 0 처리)
    cats = db.execute(
        select(Category).where(Category.user_id == current.id).order_by(Category.type, Category.name)
    ).scalars().all()

    # 실제 거래가 있는 카테고리 합계만 먼저 계산
    tx_rows = db.execute(
        select(
            Category.id.label("category_id"),
            Category.name.label("category_name"),
            Category.type.label("type"),
            func.coalesce(func.sum(Transaction.amount), 0).label("total")
        )
        .join(Transaction, Transaction.category_id == Category.id, isouter=True)
        .join(Account, Account.id == Transaction.account_id, isouter=True)
        .where(Category.user_id == current.id)
        .where((Transaction.date >= start) & (Transaction.date < end))
        .group_by(Category.id)
    ).all()

    sum_map = {r.category_id: Decimal(r.total or 0) for r in tx_rows}

    breakdown: List[ReportCategoryTotal] = []
    for c in cats:
        breakdown.append(ReportCategoryTotal(
            category_id=c.id,
            category_name=c.name,
            type=c.type,
            total=sum_map.get(c.id, Decimal(0))
        ))

    net = total_income - total_expense
    return ReportSummary(month=month, total_income=total_income, total_expense=total_expense, net=net, breakdown=breakdown)


@app.get("/reports/budget-status", response_model=List[BudgetStatusItem], tags=["reports"])
def report_budget_status(month: str = Query(pattern=r"^\d{4}-\d{2}$"), db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    """카테고리별 예산/지출/차이/사용률(%) — expense 카테고리만 대상"""
    start, end = _month_range(month)

    # 지출 합계 (expense만)
    tx_rows = db.execute(
        select(
            Category.id.label("category_id"),
            Category.name.label("category_name"),
            func.coalesce(func.sum(Transaction.amount), 0).label("spent")
        )
        .join(Transaction, Transaction.category_id == Category.id, isouter=True)
        .join(Account, Account.id == Transaction.account_id, isouter=True)
        .where(Category.user_id == current.id, Category.type == "expense")
        .where((Transaction.date >= start) & (Transaction.date < end))
        .group_by(Category.id)
    ).all()
    spent_map = {r.category_id: Decimal(r.spent or 0) for r in tx_rows}

    # 예산 (해당 월)
    bu_rows = db.execute(
        select(Budget).where(Budget.user_id == current.id, Budget.month == month)
    ).scalars().all()
    budget_map = {b.category_id: Decimal(b.amount) for b in bu_rows}

    cats = db.execute(
        select(Category).where(Category.user_id == current.id, Category.type == "expense").order_by(Category.name)
    ).scalars().all()

    items: List[BudgetStatusItem] = []
    for c in cats:
        budget = budget_map.get(c.id, Decimal(0))
        spent = spent_map.get(c.id, Decimal(0))
        diff = budget - spent
        if budget > 0:
            usage = (spent / budget * Decimal(100)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            usage_rate = float(usage)
        else:
            usage_rate = 0.0
        items.append(BudgetStatusItem(
            category_id=c.id,
            category_name=c.name,
            budget=budget,
            spent=spent,
            diff=diff,
            usage_rate=usage_rate,
        ))

    return items


@app.get("/reports/summary.csv", tags=["reports"])  # CSV는 바이너리/텍스트 응답이므로 모델 생략
def report_summary_csv(month: str = Query(pattern=r"^\d{4}-\d{2}$"), db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    """/reports/summary의 내용을 CSV 파일로 다운로드"""
    # 내부적으로 /reports/summary 계산을 재사용
    summary = report_summary(month, db, current)

    buf = io.StringIO()
    writer = csv.writer(buf)

    # 헤더
    writer.writerow(["month", summary.month])
    writer.writerow(["total_income", str(summary.total_income)])
    writer.writerow(["total_expense", str(summary.total_expense)])
    writer.writerow(["net", str(summary.net)])
    writer.writerow([])
    writer.writerow(["category_id", "category_name", "type", "total"])

    for item in summary.breakdown:
        writer.writerow([item.category_id, item.category_name, item.type, str(item.total)])

    buf.seek(0)
    filename = f"summary_{summary.month}.csv"
    return StreamingResponse(buf, media_type="text/csv", headers={
        "Content-Disposition": f"attachment; filename={filename}"
    })


# ==========================
# 6) 헬퍼: 월 범위 계산
# ==========================

def _month_range(month: str):
    """입력: 'YYYY-MM'  → 해당 월의 [시작일, 다음달 1일) 범위 반환"""
    y = int(month[:4])
    m = int(month[5:7])
    start = date(y, m, 1)
    if m == 12:
        end = date(y + 1, 1, 1)
    else:
        end = date(y, m + 1, 1)
    return start, end


# ==========================
# 7) 루트 엔드포인트 (상태 확인)
# ==========================
@app.get("/")
def root():
    return {"ok": True, "service": "Personal Ledger API — Reports Edition", "docs": "/docs"}
```

---

## 빠른 테스트 가이드 (Swagger)

1. `/auth/register` → `/auth/login` → **Authorize** 토큰 설정
2. `/accounts` POST로 `현금` 계좌 생성(초기 잔액 100000)
3. `/categories` POST로 `식비(expense)`, `월급(income)` 생성
4. `/transactions` POST로 9월에 수입/지출 몇 개 입력
5. `/budgets` POST로 9월 예산 설정(식비 300000 등)
6. 리포트 확인

   * `/reports/summary?month=2025-09`
   * `/reports/budget-status?month=2025-09`
   * `/reports/summary.csv?month=2025-09` → **파일 다운로드** 확인

(참고) 거래 목록 필터: `/transactions?month=2025-09&amount_min=5000&amount_max=20000`

---

## 실패·에러 팁

* `401` → 토큰 빠짐/만료: **Authorize**로 토큰 다시 입력
* `400` → `month` 형식(`YYYY-MM`) 또는 `type` 철자 확인
* CSV가 열리지 않음 → 응답이 파일로 저장되었는지, Excel에서 `UTF-8`로 열기

---

필요하면 동일 코드를 **폴더 분리 버전(routers/models/schemas/services)** 으로 변환해 드릴게요.

```
```
