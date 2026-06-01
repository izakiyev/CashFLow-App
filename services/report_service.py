from database.session import get_session
from database.models import Transaction, Category, Account
from sqlalchemy.orm import joinedload
from decimal import Decimal

def get_pl_statement(company_id, date_from=None, date_to=None):
    """Returns Profit & Loss statement data grouped by category in base currency,
    filtered to the specific date range."""
    from services.currency_service import convert_to_base
    from database.models import Company
    from datetime import datetime
    from sqlalchemy import func

    with get_session() as session:
        company = session.get(Company, company_id)
        base_currency = company.currency if company else "AZN"

        q = (
            session.query(Transaction)
            .outerjoin(Category, Transaction.category_id == Category.id)
            .options(joinedload(Transaction.category).joinedload(Category.parent))
            .filter(Transaction.company_id == company_id)
        )

        if date_from and date_to:
            q = q.filter(Transaction.date >= date_from, Transaction.date <= date_to)
        elif date_from is None and date_to is None:
            # All Time
            pass
        else:
            now = datetime.now()
            q = q.filter(
                func.extract('month', Transaction.date) == now.month,
                func.extract('year',  Transaction.date) == now.year
            )

        txs = q.all()

        cat_sums = {}
        for tx in txs:
            if tx.base_amount is not None:
                norm_amount = Decimal(str(tx.base_amount)) + Decimal(str(tx.base_edv_amount or 0))
            else:
                norm_amount = convert_to_base(tx.amount, tx.currency, base_currency)
                if tx.edv_amount:
                    norm_amount += Decimal(str(tx.edv_amount))
            
            cat = tx.category
            if cat:
                if cat.parent_id:
                    # Resolve parent via relationship (should be loaded via joinedload)
                    parent = getattr(cat, 'parent', None)
                    name = parent.name if parent else cat.name
                    color = parent.color if parent else cat.color
                else:
                    name = cat.name
                    color = cat.color
                key = (cat.type, name, color)
            else:
                # Handle Uncategorized correctly
                key = (tx.type, "Uncategorized", "#888888")
            
            cat_sums[key] = cat_sums.get(key, Decimal("0.0")) + norm_amount

        income = []
        expenses = []
        total_income = Decimal("0.0")
        total_expenses = Decimal("0.0")

        for (type_, name, color), amount in cat_sums.items():
            if type_ == 'income':
                income.append({"name": name, "amount": float(amount), "color": color})
                total_income += amount
            elif type_ == 'expense':
                expenses.append({"name": name, "amount": float(amount), "color": color})
                total_expenses += amount

        return {
            "income": income,
            "expenses": expenses,
            "total_income": float(total_income),
            "total_expenses": float(total_expenses),
            "net_profit": float(total_income - total_expenses),
            "base_currency": base_currency
        }

def get_vat_report(company_id, date_from=None, date_to=None):
    """Calculates VAT Collected vs Paid for a specific period in base currency.
    Uses the base_edv_amount snapshot for accuracy; falls back to convert_to_base
    for legacy transactions recorded before the snapshot field existed.
    """
    from datetime import datetime
    from sqlalchemy import func
    from database.models import Company
    from services.currency_service import convert_to_base

    with get_session() as session:
        now = datetime.now()
        
        company = session.get(Company, company_id)
        base_currency = company.currency if company else "AZN"

        q = session.query(Transaction).filter(
            Transaction.company_id == company_id,
            Transaction.status == 'paid',
            Transaction.edv_amount > 0
        )

        if date_from and date_to:
            q = q.filter(Transaction.date >= date_from, Transaction.date <= date_to)
        elif date_from is None and date_to is None:
            pass  # All Time
        else:
            q = q.filter(
                func.extract('month', Transaction.date) == now.month,
                func.extract('year', Transaction.date) == now.year
            )

        txs = q.all()

        collected = Decimal("0.0")  # VAT from Income
        paid = Decimal("0.0")       # VAT from Expenses

        for tx in txs:
            # Use the base-currency snapshot if available (recorded at transaction time).
            # Fall back to current-rate conversion for legacy records.
            if tx.base_edv_amount is not None:
                val = Decimal(str(tx.base_edv_amount))
            else:
                val = convert_to_base(
                    Decimal(str(tx.edv_amount)), tx.currency, base_currency
                )

            if tx.type == 'income':
                collected += val
            elif tx.type == 'expense':
                paid += val

        return {
            "collected": float(collected),
            "paid": float(paid),
            "net": float(collected - paid),
            "currency": base_currency,
        }

def get_cash_flow_forecast(company_id, days=90):
    """Predicts future cash position based on current balance + planned payments."""
    from datetime import datetime, timedelta
    from database.models import Company, PlannedPayment
    from services.currency_service import convert_to_base

    with get_session() as session:
        company = session.get(Company, company_id)
        base_currency = company.currency if company else "AZN"

        # 1. Start with current total balance
        accounts = session.query(Account).filter(Account.company_id == company_id).all()
        current_balance = sum(convert_to_base(a.balance, a.currency, base_currency) for a in accounts)

        # 2. Get all pending planned payments
        planned = session.query(PlannedPayment).filter(
            PlannedPayment.company_id == company_id,
            PlannedPayment.status == 'pending'
            # Removed the >= now() check to include overdue payments
        ).order_by(PlannedPayment.due_date).all()

        # 3. Project day by day
        dates = []
        balances = []
        
        running_balance = current_balance
        now = datetime.now().date()
        
        # Group planned by date
        p_map = {}
        for p in planned:
            # Overdue payments are treated as due "Today" in the forecast
            d = max(p.due_date.date(), now)
            if d not in p_map: p_map[d] = Decimal("0.0")
            
            # Convert planned amount to base currency (using CURRENT rate for forecast)
            amt = convert_to_base(p.amount, p.currency, base_currency)
            if p.edv_amount:
                amt += Decimal(str(p.edv_amount))
                
            if p.type == 'income':
                p_map[d] += amt
            else:
                p_map[d] -= amt

        for i in range(days):
            curr_date = now + timedelta(days=i)
            if curr_date in p_map:
                running_balance += p_map[curr_date]
            
            dates.append(curr_date.strftime("%b %d"))
            balances.append(float(running_balance))

        return dates, balances

def get_balance_summary(company_id):
    from services.currency_service import convert_to_base
    from database.models import Company
    with get_session() as session:
        company = session.get(Company, company_id)
        base_currency = company.currency if company else "AZN"
        
        accounts = session.query(Account).filter(Account.company_id == company_id).all()
        summary = [{"name": a.name, "type": a.type, "balance": float(a.balance), "currency": a.currency, "color": a.color} for a in accounts]
        total = sum(convert_to_base(a.balance, a.currency, base_currency) for a in accounts)
        return {"accounts": summary, "total": float(total), "base_currency": base_currency}

def get_cashflow_statement(company_id, date_from=None, date_to=None):
    return get_pl_statement(company_id, date_from, date_to)

def get_fx_gain_loss(company_id, date_from=None, date_to=None):
    """Calculates realized/unrealized gain/loss due to currency fluctuations."""
    from services.currency_service import convert_to_base
    from database.models import Company
    from datetime import datetime
    from sqlalchemy import func

    with get_session() as session:
        company = session.get(Company, company_id)
        base_currency = company.currency if company else "AZN"

        q = session.query(Transaction).filter(
            Transaction.company_id == company_id,
            Transaction.currency != base_currency
        )
        
        if date_from and date_to:
            q = q.filter(Transaction.date >= date_from, Transaction.date <= date_to)
        elif date_from is None and date_to is None:
            pass # All Time
        else:
            now = datetime.now()
            q = q.filter(
                func.extract('month', Transaction.date) == now.month,
                func.extract('year', Transaction.date) == now.year
            )

        txs = q.all()

        total_gain_loss = Decimal("0.0")
        
        for tx in txs:
            if tx.base_amount is None: continue
            
            # 1. Historical Value (what we recorded at the time)
            historical_base = Decimal(str(tx.base_amount))
            
            # 2. Current Value (what it would be worth at today's rate)
            current_base = convert_to_base(tx.amount, tx.currency, base_currency)
            
            # 3. Difference
            diff = current_base - historical_base
            
            # For expenses, a HIGHER current base means we "lost" money (it would cost more now)
            # For income, a HIGHER current base means we "gained" money.
            if tx.type == 'income':
                total_gain_loss += diff
            elif tx.type == 'expense':
                total_gain_loss -= diff
                
        return {
            "total_gain_loss": float(total_gain_loss),
            "currency": base_currency
        }
