from fastapi import FastAPI

from app.api.routes import auth
from app.api.routes import users, accounts, categories
from app.api.routes import transactions, budgets, reports

app = FastAPI(title="Personal Finance API")

app.include_router(auth.router)
app.include_router(users.router)        
app.include_router(accounts.router)     
app.include_router(categories.router)   
app.include_router(transactions.router)
app.include_router(budgets.router)
app.include_router(reports.router)
