from sqlalchemy.orm import Session
from datetime import date, time, timedelta
import calendar
from typing import Optional, List
from sqlalchemy.sql import func, extract
from src.models import Transaction, Account, Category

class TransactionService:
    def get_dashboard_snapshot(
        self,
        db: Session,
        user_id: int,
        period: str = "this_month",
        custom_start: Optional[date] = None,
        custom_end: Optional[date] = None,
    ) -> dict:
        start, end = self._period_bounds(period, custom_start, custom_end)
        previous_end = start - timedelta(days=1)
        previous_start = previous_end - (end - start)
        current = self._period_data(db, user_id, start, end)
        previous = self._period_data(db, user_id, previous_start, previous_end)
        return {
            "start": start,
            "end": end,
            "previous_start": previous_start,
            "previous_end": previous_end,
            "current": current,
            "previous": previous,
        }

    def get_period_summary(
        self, db: Session, user_id: int, start: date, end: date
    ) -> dict:
        return self._period_data(db, user_id, start, end)

    def _period_bounds(
        self,
        period: str,
        custom_start: Optional[date],
        custom_end: Optional[date],
    ) -> tuple[date, date]:
        today = date.today()
        if period == "custom":
            if not custom_start or not custom_end or custom_start > custom_end:
                raise ValueError("Custom period dates are invalid.")
            return custom_start, custom_end
        if period == "this_year":
            return date(today.year, 1, 1), today
        month_offset = {
            "this_month": 0,
            "last_month": -1,
            "three_months": -2,
            "six_months": -5,
        }.get(period)
        if month_offset is None:
            raise ValueError("Unknown dashboard period.")
        month_index = today.year * 12 + today.month - 1 + month_offset
        year, month_zero = divmod(month_index, 12)
        month = month_zero + 1
        start = date(year, month, 1)
        if period in {"three_months", "six_months"}:
            end = today
        elif period == "last_month":
            end = date(year, month, calendar.monthrange(year, month)[1])
        else:
            end = today
        return start, end

    def _period_data(self, db: Session, user_id: int, start: date, end: date) -> dict:
        transactions = db.query(Transaction).filter(
            Transaction.user_id == user_id,
            Transaction.date >= start,
            Transaction.date <= end,
        ).order_by(Transaction.date, Transaction.time).all()
        financial = [tx for tx in transactions if tx.type in {"income", "expense"}]
        income = sum(tx.amount for tx in financial if tx.type == "income")
        expense = sum(tx.amount for tx in financial if tx.type == "expense")
        span_days = max((end - start).days + 1, 1)
        if span_days <= 31:
            bucket = lambda tx: tx.date.strftime("%d %b")
        elif span_days <= 180:
            bucket = lambda tx: f"Week {(tx.date - start).days // 7 + 1}"
        else:
            bucket = lambda tx: tx.date.strftime("%b")
        cashflow = {}
        for tx in financial:
            key = bucket(tx)
            point = cashflow.setdefault(key, {"income": 0, "expense": 0})
            point[tx.type] += tx.amount
        categories = {}
        for tx in financial:
            if tx.type != "expense":
                continue
            name = tx.category.name if tx.category else "Uncategorized"
            categories[name] = categories.get(name, 0) + tx.amount
        recent = list(reversed(transactions[-8:]))
        return {
            "income": income,
            "expense": expense,
            "savings": income - expense,
            "cashflow": list(cashflow.items()),
            "categories": sorted(categories.items(), key=lambda item: item[1], reverse=True),
            "transactions": recent,
            "average_daily_spending": expense / span_days,
        }
    def create_transaction(
        self, db: Session, user_id: int, account_id: int, amount: int, 
        tx_type: str, tx_date: date, tx_time: time, description: str,
        category_id: Optional[int] = None, to_account_id: Optional[int] = None
    ) -> Transaction:
        if amount <= 0:
            raise ValueError("Transaction amount must be greater than zero.")
        if tx_type not in {"income", "expense", "transfer"}:
            raise ValueError("Invalid transaction type.")

        account = db.query(Account).filter(Account.id == account_id, Account.user_id == user_id).first()
        if not account:
            raise ValueError("Invalid account.")

        if category_id is not None:
            category = db.query(Category).filter(
                Category.id == category_id,
                Category.user_id == user_id,
            ).first()
            if not category:
                raise ValueError("Invalid category.")

        if tx_type == "income":
            account.current_balance += amount
        elif tx_type == "expense":
            account.current_balance -= amount
        elif tx_type == "transfer":
            if to_account_id is None:
                raise ValueError("Target account is required for transfer.")
            if to_account_id == account_id:
                raise ValueError("Transfer target must differ from source account.")
            to_account = db.query(Account).filter(Account.id == to_account_id, Account.user_id == user_id).first()
            if not to_account:
                raise ValueError("Invalid target account.")

            account.current_balance -= amount
            to_account.current_balance += amount

        tx = Transaction(
            user_id=user_id,
            account_id=account_id,
            category_id=category_id,
            amount=amount,
            type=tx_type,
            to_account_id=to_account_id,
            date=tx_date,
            time=tx_time,
            description=description
        )
        db.add(tx)
        db.commit()
        db.refresh(tx)
        return tx

    def delete_transaction(self, db: Session, tx_id: int, user_id: int) -> bool:
        tx = db.query(Transaction).filter(Transaction.id == tx_id, Transaction.user_id == user_id).first()
        if not tx:
            return False
            
        # Reverse balance impact
        account = db.query(Account).filter(
            Account.id == tx.account_id,
            Account.user_id == user_id,
        ).first()
        if not account:
            raise ValueError("Transaction account is invalid.")

        if tx.type == "income":
            account.current_balance -= tx.amount
        elif tx.type == "expense":
            account.current_balance += tx.amount
        elif tx.type == "transfer":
            account.current_balance += tx.amount
            to_account = db.query(Account).filter(
                Account.id == tx.to_account_id,
                Account.user_id == user_id,
            ).first()
            if not to_account:
                raise ValueError("Transfer target account is invalid.")
            to_account.current_balance -= tx.amount
                
        db.delete(tx)
        db.commit()
        return True
        
    def get_recent(self, db: Session, user_id: int, limit: int = 50) -> List[Transaction]:
        return db.query(Transaction).filter(Transaction.user_id == user_id).order_by(Transaction.date.desc(), Transaction.time.desc()).limit(limit).all()

    def get_monthly_summary(self, db: Session, user_id: int, year: int, month: int) -> dict[str, int]:
        totals = db.query(
            Transaction.type,
            func.sum(Transaction.amount),
        ).filter(
            Transaction.user_id == user_id,
            Transaction.type.in_(("income", "expense")),
            extract("year", Transaction.date) == year,
            extract("month", Transaction.date) == month,
        ).group_by(Transaction.type).all()
        values = {tx_type: int(total or 0) for tx_type, total in totals}
        income = values.get("income", 0)
        expense = values.get("expense", 0)
        return {
            "income": income,
            "expense": expense,
            "savings": income - expense,
        }
