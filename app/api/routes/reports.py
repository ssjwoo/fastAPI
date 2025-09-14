from io import StringIO

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select, case
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.models.transaction import Transaction
from app.models.category import Category
from app.models.budget import Budget  # == Goal

router = APIRouter(prefix="/reports", tags=["Reports"])

def month_range(month: str):
    y, m = month.split("-")
    return f"{y}-{m}-01", f"{y}-{m}-31"

@router.get("/summary")
def summary(
    month: str = Query(..., pattern=r"^\d{4}-\d{2}$"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    start, end = month_range(month)

    total_q = select(
        func.sum(case((Transaction.amount >= 0, Transaction.amount), else_=0)).label("income_total"),
        func.sum(case((Transaction.amount < 0, Transaction.amount), else_=0)).label("expense_total"),
    ).where(
        Transaction.occurred_on >= start,
        Transaction.occurred_on <= end,
        Transaction.category_id.in_(select(Category.id).where(Category.user_id == user.id)),
    )
    income_total, expense_total = db.execute(total_q).one()

    by_cat_q = select(
        Category.id, Category.name, Category.type, func.sum(Transaction.amount).label("sum")
    ).where(
        Transaction.occurred_on >= start,
        Transaction.occurred_on <= end,
        Transaction.category_id == Category.id,
        Category.user_id == user.id,
    ).group_by(Category.id, Category.name, Category.type).order_by(Category.name.asc())

    by_category = [
        {"category_id": cid, "name": name, "type": ctype, "sum": float(s or 0)}
        for cid, name, ctype, s in db.execute(by_cat_q).all()
    ]

    return {
        "month": month,
        "income_total": float(income_total or 0),
        "expense_total": float(expense_total or 0),
        "by_category": by_category,
    }

@router.get("/goal-status")
def goal_status(
    month: str = Query(..., pattern=r"^\d{4}-\d{2}$"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    start, end = month_range(month)

    goals = db.execute(
        select(Budget.id, Budget.category_id, Budget.monthly_limit)
        .where(Budget.user_id == user.id, Budget.month == month)
    ).all()

    items = []
    for gid, cat_id, limit in goals:
        used = db.execute(
            select(func.sum(Transaction.amount))
            .where(
                Transaction.category_id == cat_id,
                Transaction.occurred_on >= start,
                Transaction.occurred_on <= end,
            )
        ).scalar() or 0
        used_abs = float(abs(used))
        limit_f = float(limit)
        rate = (used_abs / limit_f * 100) if limit_f > 0 else 0
        items.append({
            "goal_id": gid,
            "category_id": cat_id,
            "limit": limit_f,
            "used": used_abs,
            "rate_percent": round(rate, 1),
        })
    return {"month": month, "items": items}

@router.get("/summary.csv")
def summary_csv(
    month: str = Query(..., pattern=r"^\d{4}-\d{2}$"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    data = summary(month, db, user)
    buf = StringIO()
    buf.write("month,income_total,expense_total\n")
    buf.write(f'{data["month"]},{data["income_total"]},{data["expense_total"]}\n')
    buf.write("\ncategory_id,name,type,sum\n")
    for row in data["by_category"]:
        buf.write(f'{row["category_id"]},{row["name"]},{row["type"]},{row["sum"]}\n')
    buf.seek(0)
    headers = {"Content-Disposition": f'attachment; filename="summary_{month}.csv"'}
    return StreamingResponse(buf, media_type="text/csv; charset=utf-8", headers=headers)
