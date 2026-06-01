from database.session import get_session
from database.models import Company, Account, Transaction


def create_company(name, currency, owner_id):
    """Creates a new Company."""
    with get_session() as session:
        company = Company(name=name, currency=currency, owner_id=owner_id)
        session.add(company)
        session.flush() # get company.id
        
        session.commit()
        return company.id

def get_all_companies():
    """Returns a list of all Company records as dicts."""
    with get_session() as session:
        companies = session.query(Company).order_by(Company.name).all()
        return [{"id": c.id, "name": c.name, "currency": c.currency} for c in companies]

def get_company(company_id):
    """Returns the Company record as a dict."""
    if not company_id:
        return None
    with get_session() as session:
        c = session.get(Company, company_id)
        if not c:
            return None
        return {
            "id": c.id, 
            "name": c.name, 
            "currency": c.currency, 
            "ai_api_key": c.ai_api_key,
            "ai_model": c.ai_model or "gemini-2.5-flash",
            "ai_enabled": c.ai_enabled if c.ai_enabled is not None else True
        }

def update_company_ai_key(company_id, ai_key: str):
    """Updates the AI API key for the company."""
    with get_session() as session:
        company = session.get(Company, company_id)
        if not company:
            return False
        company.ai_api_key = ai_key.strip()
        session.commit()
        return True

def update_company_ai_model(company_id, model_name: str):
    """Updates the preferred AI model for the company."""
    with get_session() as session:
        company = session.get(Company, company_id)
        if not company:
            return False
        company.ai_model = model_name.strip()
        session.commit()
        return True

def update_company_ai_enabled(company_id, enabled: bool):
    """Updates whether AI features are enabled for the company."""
    with get_session() as session:
        company = session.get(Company, company_id)
        if not company:
            return False
        company.ai_enabled = enabled
        session.commit()
        return True


def update_company_currency(company_id, new_currency: str):
    """
    Updates the base/reporting currency of a company.
    Also migrates all accounts and transactions that still carry the OLD
    currency code so they are recorded natively in the new base currency.
    """
    new_currency = new_currency.strip().upper()
    with get_session() as session:
        company = session.get(Company, company_id)
        if not company:
            return False
        old_currency = company.currency
        company.currency = new_currency

        # Migrate accounts and transactions that used the old base currency
        session.query(Account).filter(
            Account.company_id == company_id,
            Account.currency == old_currency
        ).update({"currency": new_currency})

        session.query(Transaction).filter(
            Transaction.company_id == company_id,
            Transaction.currency == old_currency
        ).update({"currency": new_currency})

        session.commit()
        return True

def update_company_name(company_id, new_name: str):
    """Updates the name of a company."""
    new_name = new_name.strip()
    if not new_name:
        return False
    with get_session() as session:
        company = session.get(Company, company_id)
        if not company:
            return False
        company.name = new_name
        session.commit()
        return True

def delete_company(company_id):
    """
    Deletes the company and all its associated data (accounts, transactions,
    categories, planned payments) via cascade. Clears any User.active_company_id
    references first to avoid SQLite IntegrityError.
    """
    from database.models import User
    with get_session() as session:
        # 1. Null out any user that has this as their active company to avoid FK violation
        session.query(User).filter(
            User.active_company_id == company_id
        ).update({"active_company_id": None})

        # 2. Now safely delete the company (cascade handles children)
        company = session.get(Company, company_id)
        if company:
            session.delete(company)
            session.commit()
            return True
        return False
