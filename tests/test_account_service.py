import pytest
from services.account_service import create_account, update_balance, get_accounts, delete_account
from database.models import Account

def test_create_account(seed_company):
    data = {
        "company_id": seed_company,
        "name": "Savings",
        "type": "Bank",
        "currency": "USD",
        "balance": 1500.0,
    }
    
    account = create_account(data)
    assert account.id is not None
    assert account.name == "Savings"
    assert account.balance == 1500.0

def test_update_balance(seed_account):
    # Add amount — update_balance returns a dict
    account = update_balance(seed_account, 50.0, "add")
    assert account is not None
    assert account["balance"] == 150.0
    
    # Subtract amount
    account = update_balance(seed_account, 30.0, "subtract")
    assert account["balance"] == 120.0

def test_get_accounts(seed_company, seed_account):
    accounts = get_accounts(seed_company)
    assert len(accounts) == 1
    assert accounts[0]["id"] == seed_account      # get_accounts returns dicts
    assert accounts[0]["name"] == "Test Account"

def test_delete_account_no_transactions(seed_account):
    # Since there are no transactions, it should delete successfully
    result = delete_account(seed_account)
    assert result is True
    
    # Verify it's actually deleted
    import database.engine
    session = database.engine.SessionLocal()
    account = session.query(Account).filter(Account.id == seed_account).first()
    session.close()
    assert account is None
