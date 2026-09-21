from sqlalchemy import String, Integer, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import List, Optional

from .base import Base, TimestampMixin

class Category(Base, TimestampMixin):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    name: Mapped[str] = mapped_column(String(100))
    type: Mapped[str] = mapped_column(String(20)) # income or expense
    icon: Mapped[Optional[str]] = mapped_column(String(50))
    color: Mapped[Optional[str]] = mapped_column(String(20))
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False)

    # Relationships
    user: Mapped["User"] = relationship(back_populates="categories")
    transactions: Mapped[List["Transaction"]] = relationship(back_populates="category")
    budgets: Mapped[List["Budget"]] = relationship(back_populates="category", cascade="all, delete-orphan")
