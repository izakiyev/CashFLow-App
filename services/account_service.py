from database.session import get_session
from database.models import Account, Transaction
from sqlalchemy import func

def create_account(data):
    with get_session() as session:
        account = Account(**data)
        session.add(account)
        session.commit()
        session.refresh(account)
        return account

def update_account(account_id, new_data):
    """Updates an existing account's details."""
    with get_session() as session:
        account = session.query(Account).filter(Account.id == account_id).first()
        if not account:
            return None
        
        for k, v in new_data.items():
            if hasattr(account, k):
                setattr(account, k, v)
                
        session.commit()
        session.refresh(account)
        return account

def update_balance(account_id, amount, operation):
    """Updates the account balance. operation is either 'add' or 'subtract'."""
    from decimal import Decimal
    with get_session() as session:
        account = session.query(Account).filter(Account.id == account_id).first()
        if not account:
            return None
        amt = Decimal(str(amount))  # Safe conversion: avoids Decimal+float TypeError
        if operation == 'add':
            account.balance = account.balance + amt
        elif operation == 'subtract':
            account.balance = account.balance - amt
        session.commit()
        return {"id": account.id, "balance": float(account.balance)}

def get_accounts(company_id, include_archived=False):
    with get_session() as session:
        q = session.query(Account).filter(Account.company_id == company_id)
        if not include_archived:
            q = q.filter(Account.is_archived != True)
        accounts = q.order_by(Account.name).all()
        # Eagerly load data before session closes
        return [
            {
                "id": a.id,
                "name": a.name,
                "type": a.type,
                "currency": a.currency,
                "balance": float(a.balance),
                "color": a.color,
                "identifier": a.identifier,
                "is_archived": a.is_archived,
            }
            for a in accounts
        ]

def get_accounts_summary(company_id):
    """Returns total assets, liabilities and net worth all converted to base currency."""
    from services.currency_service import convert_to_base
    from database.models import Company
    with get_session() as session:
        company = session.get(Company, company_id)
        base_currency = company.currency if company else "AZN"
        accounts = session.query(Account).filter(
            Account.company_id == company_id,
            Account.is_archived != True
        ).all()
        
        assets = sum(
            float(convert_to_base(a.balance, a.currency, base_currency))
            for a in accounts if float(a.balance) >= 0
        )
        liabilities = sum(
            float(convert_to_base(abs(a.balance), a.currency, base_currency))
            for a in accounts if float(a.balance) < 0
        )
        return {
            "assets": assets,
            "liabilities": liabilities,
            "net_worth": assets - liabilities,
            "base_currency": base_currency,
            "count": len(accounts),
        }

def delete_account(account_id):
    from sqlalchemy.exc import IntegrityError
    from database.models import PlannedPayment
    with get_session() as session:
        tx_count = session.query(func.count(Transaction.id)).filter(
            (Transaction.account_id == account_id) | 
            (Transaction.to_account_id == account_id) |
            (Transaction.edv_account_id == account_id)
        ).scalar()

        if tx_count and tx_count > 0:
            return False

        account = session.query(Account).filter(Account.id == account_id).first()
        if account:
            try:
                # Clear edv_account_id on planned payments to prevent FK constraints
                session.query(PlannedPayment).filter(PlannedPayment.edv_account_id == account_id).update({
                    PlannedPayment.edv_account_id: None,
                    PlannedPayment.edv_amount: 0
                })
                # Delete any associated planned payments to satisfy foreign key constraints
                session.query(PlannedPayment).filter(PlannedPayment.account_id == account_id).delete()
                
                session.delete(account)
                session.commit()
                return True
            except IntegrityError:
                session.rollback()
                return False
        return False

def get_balance_history(company_id, months=6):
    # Stub: Return empty history for now
    return {}

def get_currency_exposure(company_id):
    """Returns a breakdown of account balances grouped by native currency."""
    with get_session() as session:
        accounts = session.query(Account).filter(
            Account.company_id == company_id,
            Account.is_archived == False
        ).all()
        exposure = {}
        for a in accounts:
            curr = a.currency
            bal = float(a.balance)
            if curr not in exposure:
                exposure[curr] = 0.0
            exposure[curr] += bal
        # Sort by descending absolute balance
        return sorted(
            [{"currency": k, "balance": v} for k, v in exposure.items()],
            key=lambda x: abs(x["balance"]), reverse=True
        )
