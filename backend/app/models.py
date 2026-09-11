from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    # RBAC: "viewer" (read-only) or "admin" (full CRUD on orders)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="viewer")


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    # Store a hash of the token, never the raw value — same principle as passwords.
    # If the DB leaks, the hashes alone can't be used to authenticate.
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)




class SuperstoreSale(Base):
    __tablename__ = "superstore_sales"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    ship_mode: Mapped[str] = mapped_column(String(50))
    segment: Mapped[str] = mapped_column(String(50), index=True)
    country: Mapped[str] = mapped_column(String(100))
    city: Mapped[str] = mapped_column(String(100), index=True)
    state: Mapped[str] = mapped_column(String(100), index=True)
    postal_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    region: Mapped[str] = mapped_column(String(50), index=True)
    category: Mapped[str] = mapped_column(String(100), index=True)
    sub_category: Mapped[str] = mapped_column(String(100), index=True)
    sales: Mapped[float] = mapped_column(Numeric(12, 4))
    quantity: Mapped[int] = mapped_column(Integer)
    discount: Mapped[float] = mapped_column(Numeric(5, 2))
    profit: Mapped[float] = mapped_column(Numeric(12, 4))
