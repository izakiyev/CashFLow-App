from database.session import get_session
from database.models import Budget, Transaction, Category, Company
from sqlalchemy import func, and_
from decimal import Decimal
from datetime import datetime
from services.currency_service import convert_to_base

def get_budgets(company_id, month=None, year=None, period_type="monthly"):
    """
    Returns a list of budgets for the given period (monthly or yearly), 
    including actual spending progress.
    """
    now = datetime.now()
    month = month or now.month
    year = year or now.year

    with get_session() as session:
        company = session.get(Company, company_id)
        base_currency = company.currency if company else "AZN"

        # 1. Fetch all expense categories for the company
        categories = session.query(Category).filter(
            Category.company_id == company_id,
            Category.type == 'expense'
        ).all()
        
        # 2 & 3. Fetch budgets and transactions based on period_type
        if period_type == "monthly":
            budgets = session.query(Budget).filter(
                Budget.company_id == company_id,
                Budget.period_type == "monthly",
                Budget.month == month,
                Budget.year == year
            ).all()
            
            txs = session.query(Transaction).filter(
                Transaction.company_id == company_id,
                Transaction.type == 'expense',
                func.extract('month', Transaction.date) == month,
                func.extract('year', Transaction.date) == year,
                Transaction.status != 'pending'
            ).all()
        else: # yearly
            budgets = session.query(Budget).filter(
                Budget.company_id == company_id,
                Budget.period_type == "yearly",
                Budget.year == year
            ).all()
            
            txs = session.query(Transaction).filter(
                Transaction.company_id == company_id,
                Transaction.type == 'expense',
                func.extract('year', Transaction.date) == year,
                Transaction.status != 'pending'
            ).all()
            
        budget_map = {b.category_id: b for b in budgets}

        # 4. Calculate actual spending per category
        # We need to map children to parents for aggregation
        cat_map = {c.id: c for c in categories}
        actual_spending = {c.id: Decimal("0.0") for c in categories}
        budgeted_amounts = {c.id: Decimal("0.0") for c in categories}
        
        # Calculate budgeted amounts (including rollups)
        for cat in categories:
            b = budget_map.get(cat.id)
            if b:
                budgeted_amounts[cat.id] += b.amount
                if cat.parent_id and cat.parent_id in budgeted_amounts:
                    budgeted_amounts[cat.parent_id] += b.amount
        
        for tx in txs:
            if not tx.category_id: continue
            
            # Normalize amount to base currency
            if tx.base_amount is not None:
                amt = Decimal(str(tx.base_amount)) + Decimal(str(tx.base_edv_amount or 0))
            else:
                amt = convert_to_base(tx.amount, tx.currency, base_currency)
                if tx.edv_amount: amt += Decimal(str(tx.edv_amount))
            
            # Add to the specific category
            if tx.category_id in actual_spending:
                actual_spending[tx.category_id] += amt
                
            # If it's a subcategory, also add to its parent
            cat = cat_map.get(tx.category_id)
            if cat and cat.parent_id and cat.parent_id in actual_spending:
                actual_spending[cat.parent_id] += amt

        # 5. Build results
        results = []
        for cat in categories:
            # We only show top-level categories or categories that have a budget set
            # Or maybe we show everything. Let's show everything but clearly distinguish.
            b = budget_map.get(cat.id)
            results.append({
                "category_id": cat.id,
                "category_name": cat.name,
                "category_color": cat.color,
                "parent_id": cat.parent_id,
                "budget_id": b.id if b else None,
                "budgeted_amount": float(budgeted_amounts[cat.id]),
                "actual_amount": float(actual_spending[cat.id]),
                "currency": base_currency
            })
            
        return results

def set_budget(company_id, category_id, amount, month, year, period_type="monthly"):
    with get_session() as session:
        if period_type == "yearly":
            month = None
            
        budget = session.query(Budget).filter(
            Budget.company_id == company_id,
            Budget.category_id == category_id,
            Budget.period_type == period_type,
            Budget.month == month,
            Budget.year == year
        ).first()
        
        if budget:
            budget.amount = Decimal(str(amount))
        else:
            budget = Budget(
                company_id=company_id,
                category_id=category_id,
                amount=Decimal(str(amount)),
                month=month,
                year=year,
                period_type=period_type
            )
            session.add(budget)
        
        session.commit()
        return True

def delete_budget(budget_id):
    with get_session() as session:
        budget = session.get(Budget, budget_id)
        if budget:
            session.delete(budget)
            session.commit()
            return True
        return False

def get_budget_summary(company_id, month=None, year=None, period_type="monthly"):
    budgets = get_budgets(company_id, month, year, period_type)
    
    total_budgeted = sum(b['budgeted_amount'] for b in budgets if b['parent_id'] is None)
    total_actual = sum(b['actual_amount'] for b in budgets if b['parent_id'] is None)
    
    return {
        "total_budgeted": total_budgeted,
        "total_actual": total_actual,
        "remaining": max(0, total_budgeted - total_actual),
        "status": "on_track" if total_actual <= total_budgeted else "over_budget"
    }
