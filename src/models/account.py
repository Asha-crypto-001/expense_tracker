from sqlalchemy import String, Integer, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import List, Optional

from .base import Base, TimestampMixin

class Account(Base, TimestampMixin):
    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    name: Mapped[str] = mapped_column(String(100))
    account_type: Mapped[str] = mapped_column(String(50)) # Cash, Bank, Mobile Money, etc.
    currency: Mapped[str] = mapped_column(String(3), default="UGX")
    opening_balance: Mapped[int] = mapped_column(Integer, default=0) # using integer for minor units or whole UGX
    current_balance: Mapped[int] = mapped_column(Integer, default=0)
    description: Mapped[Optional[str]] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    user: Mapped["User"] = relationship(back_populates="accounts")
    transactions: Mapped[List["Transaction"]] = relationship(back_populates="account", cascade="all, delete-orphan", foreign_keys="[Transaction.account_id]")
