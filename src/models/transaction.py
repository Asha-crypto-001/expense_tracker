from sqlalchemy import String, Integer, ForeignKey, Date, Time
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import date, time
from typing import Optional

from .base import Base, TimestampMixin

class Transaction(Base, TimestampMixin):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"))
    category_id: Mapped[Optional[int]] = mapped_column(ForeignKey("categories.id"), nullable=True)
    
    amount: Mapped[int] = mapped_column(Integer) # For UGX, integer is perfectly fine
    type: Mapped[str] = mapped_column(String(20)) # income, expense, transfer
    
    # Optional fields for transfers
    to_account_id: Mapped[Optional[int]] = mapped_column(ForeignKey("accounts.id"), nullable=True)
    
    date: Mapped[date] = mapped_column(Date)
    time: Mapped[time] = mapped_column(Time)
    
    description: Mapped[str] = mapped_column(String(255))
    location: Mapped[Optional[str]] = mapped_column(String(255))
    notes: Mapped[Optional[str]] = mapped_column(String)
    receipt_path: Mapped[Optional[str]] = mapped_column(String(500))
    recurring_id: Mapped[Optional[int]] = mapped_column(ForeignKey("recurring_transactions.id"), nullable=True)

    # Relationships
    user: Mapped["User"] = relationship()
    account: Mapped["Account"] = relationship(foreign_keys=[account_id], back_populates="transactions")
    to_account: Mapped[Optional["Account"]] = relationship(foreign_keys=[to_account_id])
    category: Mapped[Optional["Category"]] = relationship(back_populates="transactions")
    recurring: Mapped[Optional["RecurringTransaction"]] = relationship(back_populates="transactions")
