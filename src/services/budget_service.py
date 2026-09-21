from sqlalchemy.orm import Session
from sqlalchemy.sql import func, extract
from typing import List, Optional
from datetime import date
from src.models import Budget, Transaction, Category

class BudgetService:
    def create_budget(
        self,
        db: Session,
        user_id: int,
        amount: int,
        period: str,
        category_id: Optional[int] = None,
        month: Optional[int] = None,
        year: Optional[int] = None,
    ) -> Budget:
        if amount <= 0:
            raise ValueError("Budget amount must be greater than zero.")
        if period not in {"monthly", "yearly"}:
            raise ValueError("Budget period must be 'monthly' or 'yearly'.")
        if category_id is not None:
            category = db.query(Category).filter(
                Category.id == category_id,
                Category.user_id == user_id,
                Category.type == "expense",
            ).first()
            if not category:
                raise ValueError("Invalid expense category.")

        today = date.today()
        budget = Budget(
            user_id=user_id,
            category_id=category_id,
            amount=amount,
            period=period,
            month=month or today.month,
            year=year or today.year,
        )
        db.add(budget)
        db.commit()
        db.refresh(budget)
        return budget

    def get_budgets(self, db: Session, user_id: int) -> List[Budget]:
        return db.query(Budget).filter(Budget.user_id == user_id).order_by(Budget.created_at.desc()).all()

    def get_budget_usage(self, db: Session, budget: Budget) -> int:
        query = db.query(func.sum(Transaction.amount)).filter(
            Transaction.user_id == budget.user_id,
            Transaction.type == "expense"
        )

        if budget.category_id:
            query = query.filter(Transaction.category_id == budget.category_id)

        if budget.period == "monthly":
            target_month = budget.month or date.today().month
            target_year = budget.year or date.today().year
            query = query.filter(
                extract('year', Transaction.date) == target_year,
                extract('month', Transaction.date) == target_month,
            )
        elif budget.period == "yearly":
            target_year = budget.year or date.today().year
            query = query.filter(extract('year', Transaction.date) == target_year)

        return query.scalar() or 0

    def get_budget_usage_for_range(
        self, db: Session, budget: Budget, start: date, end: date
    ) -> int:
        query = db.query(func.sum(Transaction.amount)).filter(
            Transaction.user_id == budget.user_id,
            Transaction.type == "expense",
            Transaction.date >= start,
            Transaction.date <= end,
        )
        if budget.category_id:
            query = query.filter(Transaction.category_id == budget.category_id)
        return int(query.scalar() or 0)
