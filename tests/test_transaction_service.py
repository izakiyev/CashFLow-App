import pytest
from datetime import datetime
from services.transaction_service import create_transaction
from database.models import Transaction

def test_create_income_transaction(seed_company, seed_account):
    data = {
        "company_id": seed_company,
        "account_id": seed_account,
        "type": "income",
        "amount": 500.0,
        "currency": "USD",
        "description": "Test Income",
        "date": datetime.utcnow(),
        "status": "paid",  # Must be 'paid' for balance update to apply
    }
    
    transaction = create_transaction(data)
    assert transaction.id is not None
    assert transaction.amount == 500.0
    
    # Verify account balance was updated
    import database.engine
    from database.models import Account
    session = database.engine.SessionLocal()
    account = session.query(Account).filter(Account.id == seed_account).first()
    session.close()
    
    # 100 initial + 500 income = 600
    assert account.balance == 600.0

def test_create_transfer_transaction(seed_company, seed_account):
    # First create a target account
    import database.engine
    from database.models import Account
    session = database.engine.SessionLocal()
    target = Account(company_id=seed_company, name="Target", type="Bank", currency="USD", balance=0.0)
    session.add(target)
    session.commit()
    session.refresh(target)
    target_id = target.id
    session.close()

    data = {
        "company_id": seed_company,
        "account_id": seed_account,
        "to_account_id": target_id,
        "type": "transfer",
        "amount": 50.0,
        "currency": "USD",
        "description": "Test Transfer",
        "date": datetime.utcnow(),
        "status": "paid",  # Must be 'paid' for balance update to apply
    }
    
    transaction = create_transaction(data)
    assert transaction.id is not None
    assert transaction.type == "transfer"
    
    session = database.engine.SessionLocal()
    source_acc = session.query(Account).filter(Account.id == seed_account).first()
    target_acc = session.query(Account).filter(Account.id == target_id).first()
    session.close()
    
    # Source account should be decreased by 50 (100 - 50 = 50)
    assert source_acc.balance == 50.0
    # Target account should be increased by 50 (0 + 50 = 50)
    assert target_acc.balance == 50.0
