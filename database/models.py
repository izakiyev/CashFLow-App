# CRITICAL: Use Numeric(15, 2) for ALL money fields.
# Never use Float. Float causes rounding errors in financial data.

from decimal import Decimal
from sqlalchemy import (
    Column, Integer, String, DateTime, Text,
    ForeignKey, Boolean, Numeric, Index
)
from sqlalchemy.orm import relationship, DeclarativeBase
from datetime import datetime

from sqlalchemy.types import TypeDecorator

class CentsInteger(TypeDecorator):
    impl = Integer
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is not None:
            # Round to nearest cent BEFORE converting to integer to prevent drift
            d_val = Decimal(str(value)).quantize(Decimal("0.01"), rounding="ROUND_HALF_UP")
            return int(d_val * 100)
        return None

    def process_result_value(self, value, dialect):
        if value is not None:
            return Decimal(value) / 100
        return None

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"
    id              = Column(Integer, primary_key=True)
    name            = Column(String(100), nullable=False)
    email           = Column(String(255), unique=True, nullable=False)
    active_company_id = Column(Integer,
                               ForeignKey("companies.id", use_alter=True),
                               nullable=True)
    created_at      = Column(DateTime, default=datetime.utcnow, nullable=False)
    companies       = relationship("Company",
                                   foreign_keys="Company.owner_id",
                                   back_populates="owner")
    __table_args__ = (
        Index("ix_users_email", "email"),
    )

class Company(Base):
    __tablename__ = "companies"
    id          = Column(Integer, primary_key=True)
    name        = Column(String(200), nullable=False)
    currency    = Column(String(10), default="AZN", nullable=False)
    owner_id    = Column(Integer, ForeignKey("users.id"), nullable=False)
    is_seeded   = Column(Boolean, default=False)
    ai_api_key  = Column(String(500), default="")
    ai_model    = Column(String(50), default="gemini-2.5-flash")
    ai_enabled  = Column(Boolean, default=True)
    created_at  = Column(DateTime, default=datetime.utcnow, nullable=False)
    owner       = relationship("User",
                               foreign_keys=[owner_id],
                               back_populates="companies")
    accounts    = relationship("Account",
                               back_populates="company",
                               cascade="all, delete-orphan")
    transactions = relationship("Transaction",
                                back_populates="company",
                                cascade="all, delete-orphan")
    categories  = relationship("Category",
                               back_populates="company",
                               cascade="all, delete-orphan")
    planned     = relationship("PlannedPayment",
                               back_populates="company",
                               cascade="all, delete-orphan")

class Account(Base):
    __tablename__ = "accounts"
    id          = Column(Integer, primary_key=True)
    company_id  = Column(Integer,
                         ForeignKey("companies.id", ondelete="CASCADE"),
                         nullable=False)
    name        = Column(String(200), nullable=False)
    type        = Column(String(50), nullable=False)
    currency    = Column(String(10), default="AZN", nullable=False)
    # MONEY: CentsInteger eliminates float rounding errors
    balance     = Column(CentsInteger, default=Decimal("0.00"), nullable=False)
    color       = Column(String(10), default="#1a9e75")
    identifier  = Column(String(255), default="")
    is_archived = Column(Boolean, default=False)
    created_at  = Column(DateTime, default=datetime.utcnow)
    company     = relationship("Company",
                               back_populates="accounts")
    transactions = relationship("Transaction",
                                foreign_keys="Transaction.account_id",
                                back_populates="account")
    __table_args__ = (
        Index("ix_accounts_company", "company_id"),
    )

class Transaction(Base):
    __tablename__ = "transactions"
    id              = Column(Integer, primary_key=True)
    company_id      = Column(Integer,
                             ForeignKey("companies.id", ondelete="CASCADE"),
                             nullable=False)
    account_id      = Column(Integer,
                             ForeignKey("accounts.id"),
                             nullable=False)
    to_account_id   = Column(Integer,
                             ForeignKey("accounts.id"),
                             nullable=True)   # transfers only
    category_id     = Column(Integer,
                             ForeignKey("categories.id"),
                             nullable=True)
    type            = Column(String(20), nullable=False)
    # MONEY: CentsInteger eliminates float rounding errors
    amount          = Column(CentsInteger, nullable=False)
    currency        = Column(String(10), default="AZN", nullable=False)
    description     = Column(String(500), default="")
    counterparty    = Column(String(200), default="")
    date            = Column(DateTime, nullable=False)
    note            = Column(Text, default="")
    is_recurring    = Column(Boolean, default=False)
    recurring_type  = Column(String(20), default="none")
    status          = Column(String(20), default="confirmed")
    
    # EDV (VAT) support
    edv_amount      = Column(CentsInteger, nullable=True, default=0)
    edv_account_id  = Column(Integer, ForeignKey("accounts.id"), nullable=True)

    # SNAPSHOT: Captures the value in Base Currency at the time of transaction
    # This prevents exchange rate changes from affecting historical reports.
    base_amount     = Column(CentsInteger, nullable=True)
    base_edv_amount = Column(CentsInteger, nullable=True)

    # EXACT APPLIED AMOUNTS: To prevent balance drift when reverting
    account_amount      = Column(CentsInteger, nullable=True)
    to_account_amount   = Column(CentsInteger, nullable=True)
    edv_account_amount  = Column(CentsInteger, nullable=True)
    
    created_at      = Column(DateTime, default=datetime.utcnow)
    updated_at      = Column(DateTime, default=datetime.utcnow,
                             onupdate=datetime.utcnow)
    company         = relationship("Company",
                                   back_populates="transactions")
    account         = relationship("Account",
                                   foreign_keys=[account_id],
                                   back_populates="transactions")
    to_account      = relationship("Account",
                                   foreign_keys=[to_account_id])
    edv_account     = relationship("Account",
                                   foreign_keys=[edv_account_id])
    category        = relationship("Category",
                                   back_populates="transactions")
    __table_args__ = (
        Index("ix_transactions_company_date", "company_id", "date"),
        Index("ix_transactions_type", "type"),
        Index("ix_transactions_account", "account_id"),
    )

class Category(Base):
    __tablename__ = "categories"
    id          = Column(Integer, primary_key=True)
    company_id  = Column(Integer,
                         ForeignKey("companies.id", ondelete="CASCADE"),
                         nullable=False)
    parent_id   = Column(Integer,
                         ForeignKey("categories.id", ondelete="CASCADE"),
                         nullable=True)
    name        = Column(String(100), nullable=False)
    type        = Column(String(20), nullable=False)
    color       = Column(String(10), default="#888888")
    icon        = Column(String(50), default="")
    is_default  = Column(Boolean, default=False)
    created_at  = Column(DateTime, default=datetime.utcnow)
    
    company     = relationship("Company",
                               back_populates="categories")
    transactions = relationship("Transaction",
                                back_populates="category")
    
    # Self-referential relationship for subcategories
    subcategories = relationship("Category",
                                 back_populates="parent",
                                 cascade="all, delete-orphan")
    parent        = relationship("Category",
                                 back_populates="subcategories",
                                 remote_side=[id])

class PlannedPayment(Base):
    __tablename__ = "planned_payments"
    id              = Column(Integer, primary_key=True)
    company_id      = Column(Integer,
                             ForeignKey("companies.id", ondelete="CASCADE"),
                             nullable=False)
    account_id      = Column(Integer,
                             ForeignKey("accounts.id"),
                             nullable=False)
    category_id     = Column(Integer,
                             ForeignKey("categories.id"),
                             nullable=True)
    type            = Column(String(20), nullable=False)
    # MONEY: CentsInteger eliminates float rounding errors
    amount          = Column(CentsInteger, nullable=False)
    currency        = Column(String(10), default="AZN", nullable=False)

    # EDV (VAT) support
    edv_amount      = Column(CentsInteger, nullable=True, default=0)
    edv_account_id  = Column(Integer, ForeignKey("accounts.id"), nullable=True)

    description     = Column(String(500), default="")
    counterparty    = Column(String(200), default="")
    due_date        = Column(DateTime, nullable=False)
    status          = Column(String(20), default="pending")
    recurring       = Column(String(20), default="none")
    next_due_date   = Column(DateTime, nullable=True)
    paid_at         = Column(DateTime, nullable=True)
    created_at      = Column(DateTime, default=datetime.utcnow)
    company         = relationship("Company",
                                   back_populates="planned")
    account         = relationship("Account", foreign_keys=[account_id])
    edv_account     = relationship("Account", foreign_keys=[edv_account_id])
    category        = relationship("Category")
    __table_args__ = (
        Index("ix_planned_company_due", "company_id", "due_date"),
    )

class Budget(Base):
    __tablename__ = "budgets"
    id          = Column(Integer, primary_key=True)
    company_id  = Column(Integer,
                         ForeignKey("companies.id", ondelete="CASCADE"),
                         nullable=False)
    category_id = Column(Integer,
                         ForeignKey("categories.id", ondelete="CASCADE"),
                         nullable=False)
    amount      = Column(CentsInteger, nullable=False)
    period_type = Column(String(20), default="monthly", nullable=False) # 'monthly' or 'yearly'
    month       = Column(Integer, nullable=True) # 1-12, nullable for yearly budgets
    year        = Column(Integer, nullable=False)
    created_at  = Column(DateTime, default=datetime.utcnow)

    company     = relationship("Company")
    category    = relationship("Category")

    __table_args__ = (
        Index("ix_budgets_lookup", "company_id", "category_id", "year", "month"),
    )