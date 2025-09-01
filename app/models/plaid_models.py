"""
Pydantic models for Plaid API.
"""

from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from enum import Enum


class LinkTokenRequest(BaseModel):
    user_id: str
    client_name: str = "Plaid Integration App"


class PublicTokenExchangeRequest(BaseModel):
    public_token: str
    metadata: Optional[Dict[str, Any]] = None


class ItemInfo(BaseModel):
    access_token: str
    item_id: str
    institution_id: Optional[str] = None
    institution_name: Optional[str] = None


class AccountInfo(BaseModel):
    account_id: str
    name: str
    type: str
    subtype: Optional[str] = None
    balance: float
    item_id: Optional[str] = None
    institution_name: Optional[str] = None
    last_synced_at: Optional[str] = None
    status: Optional[str] = None


class TransactionInfo(BaseModel):
    transaction_id: str
    account_id: str
    amount: float
    date: str
    name: str
    category: List[str] = []
    merchant_name: Optional[str] = None
    pending: bool = False
    payment_channel: Optional[str] = None
    iso_currency_code: Optional[str] = None


class AccountType(str, Enum):
    depository = "depository"
    credit = "credit"
    loan = "loan"
    investment = "investment"
    brokerage = "brokerage"
    other = "other"


class AccountSubtype(str, Enum):
    checking = "checking"
    savings = "savings"
    credit_card = "credit card"
    money_market = "money market"
    certificate_of_deposit = "certificate of deposit"
    brokerage = "brokerage"
    ira = "ira"
    _401k = "401k"
    student = "student"
    mortgage = "mortgage"
    auto = "auto"
    personal = "personal"
    business = "business"
    commercial = "commercial"
    construction = "construction"
    home_equity = "home equity"
    other = "other"


class InvestmentHolding(BaseModel):
    security_id: str
    account_id: str
    ticker: Optional[str] = None
    name: Optional[str] = None
    quantity: float
    price: Optional[float] = None
    value: Optional[float] = None
    cost_basis: Optional[float] = None


class InvestmentTransaction(BaseModel):
    investment_transaction_id: str
    account_id: str
    security_id: Optional[str] = None
    ticker: Optional[str] = None
    name: Optional[str] = None
    type: str
    date: str
    quantity: Optional[float] = None
    price: Optional[float] = None
    amount: float
    fees: Optional[float] = None


class BankItemStatus(str, Enum):
    good = "good"
    error = "error"
    pending = "pending"
    unknown = "unknown"