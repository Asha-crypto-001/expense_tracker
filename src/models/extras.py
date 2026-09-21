from sqlalchemy import Integer, String, ForeignKey, Date
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import date
from typing import List, Optional

from .base import Base, TimestampMixin

class Budget(Base, TimestampMixin):
    __tablename__ = "budgets"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    category_id: Mapped[Optional[int]] = mapped_column(ForeignKey("categories.id"), nullable=True) # if null, it's an overall budget
    
    period: Mapped[str] = mapped_column(String(20)) # monthly, yearly
    amount: Mapped[int] = mapped_column(Integer)
    month: Mapped[Optional[int]] = mapped_column(Integer, nullable=True) # 1-12
    year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    user: Mapped["User"] = relationship(back_populates="budgets")
    category: Mapped[Optional["Category"]] = relationship(back_populates="budgets")


class RecurringTransaction(Base, TimestampMixin):
    __tablename__ = "recurring_transactions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"))
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"))
    
    amount: Mapped[int] = mapped_column(Integer)
    type: Mapped[str] = mapped_column(String(20)) # income, expense
    
    frequency: Mapped[str] = mapped_column(String(20)) # daily, weekly, monthly, yearly
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    next_occurrence: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    description: Mapped[str] = mapped_column(String(255))
    
    user: Mapped["User"] = relationship()
    account: Mapped["Account"] = relationship()
    category: Mapped["Category"] = relationship()
    transactions: Mapped[List["Transaction"]] = relationship(back_populates="recurring")


class SavingsGoal(Base, TimestampMixin):
    __tablename__ = "savings_goals"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    
    name: Mapped[str] = mapped_column(String(100))
    target_amount: Mapped[int] = mapped_column(Integer)
    current_amount: Mapped[int] = mapped_column(Integer, default=0)
    deadline: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    description: Mapped[Optional[str]] = mapped_column(String(255))
    image_path: Mapped[Optional[str]] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(20), default="active") # active, completed, archived
    
    user: Mapped["User"] = relationship(back_populates="savings_goals")
    goal_transactions: Mapped[List["GoalTransaction"]] = relationship(back_populates="goal", cascade="all, delete-orphan")


class GoalTransaction(Base, TimestampMixin):
    __tablename__ = "goal_transactions"

    id: Mapped[int] = mapped_column(primary_key=True)
    goal_id: Mapped[int] = mapped_column(ForeignKey("savings_goals.id"))
    
    amount: Mapped[int] = mapped_column(Integer)
    date: Mapped[date] = mapped_column(Date)
    type: Mapped[str] = mapped_column(String(20)) # contribution, withdrawal
    
    goal: Mapped["SavingsGoal"] = relationship(back_populates="goal_transactions")
