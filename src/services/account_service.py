from sqlalchemy.orm import Session
from typing import List
from src.models import Account
from sqlalchemy.sql import func

class AccountService:
    def create_account(self, db: Session, user_id: int, name: str, account_type: str, opening_balance: int, currency: str = "UGX") -> Account:
        account = Account(
            user_id=user_id,
            name=name,
            account_type=account_type,
            currency=currency,
            opening_balance=opening_balance,
            current_balance=opening_balance
        )
        db.add(account)
        db.commit()
        db.refresh(account)
        return account

    def get_accounts(self, db: Session, user_id: int) -> List[Account]:
        return db.query(Account).filter(Account.user_id == user_id, Account.is_active == True).all()

    def get_total_balance(self, db: Session, user_id: int) -> int:
        total = db.query(func.sum(Account.current_balance)).filter(Account.user_id == user_id, Account.is_active == True).scalar()
        return total or 0
