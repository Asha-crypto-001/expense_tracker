from sqlalchemy import String, Integer, Boolean, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from typing import List, Optional

from .base import Base, TimestampMixin

class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    display_name: Mapped[Optional[str]] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    failed_login_attempts: Mapped[int] = mapped_column(Integer, default=0)

    # Relationships
    accounts: Mapped[List["Account"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    categories: Mapped[List["Category"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    budgets: Mapped[List["Budget"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    savings_goals: Mapped[List["SavingsGoal"]] = relationship(back_populates="user", cascade="all, delete-orphan")
