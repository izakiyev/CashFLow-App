from database.session import get_session
from database.models import Transaction, Account, Category, Company
from sqlalchemy import func, extract
from sqlalchemy.orm import joinedload
from datetime import datetime
from services.currency_service import convert_to_base
import logging
from decimal import Decimal, ROUND_HALF_UP

logger = logging.getLogger(__name__)

def _apply_balance_change(session, txn):
    """Helper to apply balance change for a PAID transaction."""
    amount = Decimal(str(txn.amount))
    edv_amount = Decimal(str(txn.edv_amount or 0))
    
    # Check if we have a separate EDV account
    has_separate_edv = txn.edv_account_id and txn.edv_account_id != txn.account_id
    
    # The main account gets the TOTAL if there's no separate EDV account,
    # otherwise it ONLY gets the NET amount (to avoid double-counting in Total Balance).
    main_amount = amount + (Decimal("0") if has_separate_edv else edv_amount)

    acc = session.get(Account, txn.account_id)
    if acc:
        amt = convert_to_base(main_amount, txn.currency, acc.currency)
        txn.account_amount = amt # SNAPSHOT exactly what we applied
        if txn.type == 'income':
            acc.balance = acc.balance + amt
        elif txn.type == 'expense':
            acc.balance = acc.balance - amt
        elif txn.type == 'transfer' and txn.to_account_id:
            to_acc = session.get(Account, txn.to_account_id)
            acc.balance = acc.balance - amt
            if to_acc:
                amt_to = convert_to_base(main_amount, txn.currency, to_acc.currency)
                txn.to_account_amount = amt_to # SNAPSHOT exact transfer amount
                to_acc.balance = to_acc.balance + amt_to

    # Handle separate EDV account tracking
    if has_separate_edv and txn.edv_amount:
        edv_acc = session.get(Account, txn.edv_account_id)
        if edv_acc:
            # EDV is recorded in base currency
            company = session.get(Company, txn.company_id)
            base_curr = company.currency if company else "AZN"
            amt_edv = convert_to_base(edv_amount, base_curr, edv_acc.currency)
            txn.edv_account_amount = amt_edv # SNAPSHOT exact EDV applied
            
            if txn.type == 'income':
                edv_acc.balance = edv_acc.balance + amt_edv
            elif txn.type == 'expense':
                edv_acc.balance = edv_acc.balance - amt_edv

def _revert_balance_change(session, txn):
    """Helper to revert balance change for a PAID transaction."""
    amount = Decimal(str(txn.amount))
    edv_amount = Decimal(str(txn.edv_amount or 0))
    
    has_separate_edv = txn.edv_account_id and txn.edv_account_id != txn.account_id
    main_amount = amount + (Decimal("0") if has_separate_edv else edv_amount)

    acc = session.get(Account, txn.account_id)
    if acc:
        # Use snapshot if available, otherwise fallback to recalculation (for legacy txns)
        if txn.account_amount is not None:
            amt = Decimal(str(txn.account_amount))
        else:
            amt = convert_to_base(main_amount, txn.currency, acc.currency)
            
        if txn.type == 'income':
            acc.balance = acc.balance - amt
        elif txn.type == 'expense':
            acc.balance = acc.balance + amt
        elif txn.type == 'transfer' and txn.to_account_id:
            to_acc = session.get(Account, txn.to_account_id)
            acc.balance = acc.balance + amt
            if to_acc:
                if txn.to_account_amount is not None:
                    amt_to = Decimal(str(txn.to_account_amount))
                else:
                    amt_to = convert_to_base(main_amount, txn.currency, to_acc.currency)
                to_acc.balance = to_acc.balance - amt_to

    # Revert separate EDV account tracking
    if has_separate_edv and txn.edv_amount:
        edv_acc = session.get(Account, txn.edv_account_id)
        if edv_acc:
            if txn.edv_account_amount is not None:
                amt_edv = Decimal(str(txn.edv_account_amount))
            else:
                company = session.get(Company, txn.company_id)
                base_curr = company.currency if company else "AZN"
                amt_edv = convert_to_base(edv_amount, base_curr, edv_acc.currency)
            
            if txn.type == 'income':
                edv_acc.balance = edv_acc.balance - amt_edv
            elif txn.type == 'expense':
                edv_acc.balance = edv_acc.balance + amt_edv

def create_transaction(data):
    with get_session() as session:
        txn = Transaction(**data)
        
        # SNAPSHOT: Capture value in base currency at time of creation
        company = session.get(Company, txn.company_id)
        base_curr = company.currency if company else "AZN"
        txn.base_amount = convert_to_base(txn.amount, txn.currency, base_curr)
        txn.base_edv_amount = convert_to_base(txn.edv_amount or 0, txn.currency, base_curr)
        
        session.add(txn)

        # Update account balances atomically ONLY IF PAID
        if txn.status == 'paid':
            _apply_balance_change(session, txn)

        session.commit()
        session.refresh(txn)
        return txn
def get_transaction(tx_id):
    with get_session() as session:
        t = (session.query(Transaction)
             .options(joinedload(Transaction.category).joinedload(Category.parent))
             .filter(Transaction.id == tx_id)
             .first())
        if not t: return None
        return {
            "id": t.id,
            "company_id": t.company_id,
            "account_id": t.account_id,
            "to_account_id": t.to_account_id,
            "category_id": t.category_id,
            "project_id": t.project_id,
            "type": t.type,
            "amount": t.amount, # Keeps as Decimal
            "currency": t.currency,
            "description": t.description,
            "counterparty": t.counterparty,
            "date": t.date,
            "note": t.note,
            "edv_amount": t.edv_amount or 0,
            "edv_account_id": t.edv_account_id,
            "is_recurring": t.is_recurring,
            "recurring_type": t.recurring_type,
            "status": t.status,
            "category_name": f"{t.category.parent.name} > {t.category.name}" if t.category and t.category.parent else (t.category.name if t.category else None)
        }

def update_transaction(tx_id, new_data):
    with get_session() as session:
        txn = session.get(Transaction, tx_id)
        if not txn: return None

        # 1. Revert old balance ONLY IF it was PAID
        old_status = (txn.status or "").lower()
        if old_status == 'paid':
            logger.info(f"Reverting old balance for transaction {tx_id} before update")
            _revert_balance_change(session, txn)

        # 2. Update fields
        for k, v in new_data.items():
            if k == 'status' and v:
                v = v.lower()
            setattr(txn, k, v)

        # 3. Update snapshot if amount/currency changed
        company = session.get(Company, txn.company_id)
        base_curr = company.currency if company else "AZN"
        txn.base_amount = convert_to_base(txn.amount, txn.currency, base_curr)
        txn.base_edv_amount = convert_to_base(txn.edv_amount or 0, txn.currency, base_curr)

        # 4. Apply new balance ONLY IF it is now PAID
        new_status = (txn.status or "").lower()
        if new_status == 'paid':
            logger.info(f"Applying new balance for transaction {tx_id} after update")
            _apply_balance_change(session, txn)

        session.commit()
        return True
def get_transactions(company_id, filters=None, limit=None, offset=None):
    with get_session() as session:
        query = (session.query(Transaction)
                 .options(joinedload(Transaction.category).joinedload(Category.parent),
                          joinedload(Transaction.account))
                 .filter(Transaction.company_id == company_id)
                 .order_by(Transaction.date.desc(), Transaction.id.desc()))

        if filters:
            if filters.get('type') and filters['type'] != 'All':
                query = query.filter(Transaction.type == filters['type'].lower())
            if filters.get('account_id') and filters['account_id'] != 'All':
                query = query.filter(
                    (Transaction.account_id == filters['account_id']) |
                    (Transaction.to_account_id == filters['account_id'])
                )
            if filters.get('category_id') and filters['category_id'] != 'All':
                cat_id = filters['category_id']
                child_cats = session.query(Category.id).filter(Category.parent_id == cat_id).all()
                child_ids = [c[0] for c in child_cats]
                query = query.filter(Transaction.category_id.in_([cat_id] + child_ids))
            if filters.get('project_id') and filters['project_id'] != 'All':
                query = query.filter(Transaction.project_id == filters['project_id'])
            if filters.get('status') and filters['status'] != 'All':
                query = query.filter(Transaction.status == filters['status'].lower())
            if filters.get('search'):
                term = f"%{filters['search']}%"
                query = query.join(Category, isouter=True).join(Account, Transaction.account_id == Account.id).filter(
                    Transaction.description.ilike(term) |
                    Transaction.counterparty.ilike(term) |
                    Category.name.ilike(term) |
                    Account.name.ilike(term)
                )
            if filters.get('date_from') and filters.get('date_to'):
                query = query.filter(
                    Transaction.date >= filters['date_from'],
                    Transaction.date <= filters['date_to']
                )

        if offset:
            query = query.offset(offset)
        if limit:
            query = query.limit(limit)

        rows = query.all()
        # Serialize so data survives after session closes
        return [
            {
                "id": t.id,
                "account_id": t.account_id,
                "account_name": t.account.name if t.account else "Unknown",
                "to_account_id": t.to_account_id,
                "category_id": t.category_id,
                "project_id": t.project_id,
                "type": t.type,
                "amount": t.amount,
                "currency": t.currency,
                "description": t.description,
                "counterparty": t.counterparty,
                "date": t.date,
                "note": t.note,
                "edv_amount": t.edv_amount or 0,
                "edv_account_id": t.edv_account_id,
                "is_recurring": t.is_recurring,
                "recurring_type": t.recurring_type,
                "status": t.status,
                "category_name": f"{t.category.parent.name} > {t.category.name}" if t.category and t.category.parent else (t.category.name if t.category else None)
            }
            for t in rows
        ]

def delete_transaction(transaction_id):
    with get_session() as session:
        txn = session.query(Transaction).filter(Transaction.id == transaction_id).first()
        if not txn:
            return False

        # Revert account balance ONLY IF it was PAID
        status = (txn.status or "").lower()
        if status == 'paid':
            logger.info(f"Reverting balance for transaction {transaction_id} (Type: {txn.type}, Amount: {txn.amount})")
            _revert_balance_change(session, txn)
        else:
            logger.info(f"Deleting transaction {transaction_id} with status '{txn.status}' - no balance revert needed.")

        session.delete(txn)
        session.commit()
        return True

def pay_transaction(tx_id):
    """Marks a confirmed transaction as PAID and updates balance."""
    with get_session() as session:
        txn = session.get(Transaction, tx_id)
        if not txn or txn.status == 'paid':
            return False
        
        txn.status = 'paid'
        _apply_balance_change(session, txn)
        
        session.commit()
        return True

def get_spending_by_category(company_id, month=None, year=None, date_from=None, date_to=None, parent_category_id=None, tx_type='expense', status=None):
    from services.currency_service import convert_to_base
    from database.models import Company, Category
    
    with get_session() as session:
        now = datetime.now()
        company = session.get(Company, company_id)
        base_currency = company.currency if company else "AZN"
        
        q = session.query(Transaction).filter(
            Transaction.company_id == company_id,
            Transaction.type == tx_type
        )
        if status and status != 'All':
            st = status.lower()
            if st == 'pending':
                q = q.filter(Transaction.status.in_(['pending', 'qaime_gozleyir', 'confirmed']))
            else:
                q = q.filter(Transaction.status == st)
            
        if date_from and date_to:
            # Explicit date range
            q = q.filter(Transaction.date >= date_from, Transaction.date <= date_to)
        elif date_from is None and date_to is None:
            # All Time — no date filter
            pass
        else:
            # Default: current month
            month = month or now.month
            year  = year  or now.year
            q = q.filter(
                func.extract('month', Transaction.date) == month,
                func.extract('year',  Transaction.date) == year
            )
        txs = q.all()
        
        # Load all categories for the company to resolve parent names
        cats = session.query(Category).filter(Category.company_id == company_id).all()
        cat_map = {c.id: c for c in cats}
        
        data = {}
        for tx in txs:
            cat_name = "Uncategorized"
            cat_color = "#888888"
            cat_id = None
            
            if tx.category_id:
                cat = cat_map.get(tx.category_id)
                if cat:
                    if parent_category_id is not None:
                        # Drill-down mode: filter to only this parent
                        if cat.parent_id == parent_category_id:
                            # It is a subcategory of the requested parent
                            cat_name = cat.name
                            cat_color = cat.color
                            cat_id = cat.id
                        elif cat.id == parent_category_id:
                            # Transaction directly assigned to the parent category
                            cat_name = f"Directly in {cat.name}"
                            cat_color = cat.color
                            cat_id = cat.id
                        else:
                            # Belongs to a different parent entirely
                            continue
                    else:
                        # Top-level view (default aggregation)
                        if cat.parent_id:
                            parent = cat_map.get(cat.parent_id)
                            cat_name = parent.name if parent else cat.name
                            cat_color = parent.color if parent else cat.color
                            cat_id = parent.id if parent else cat.id
                        else:
                            cat_name = cat.name
                            cat_color = cat.color
                            cat_id = cat.id
            else:
                if parent_category_id is not None:
                    continue # Skip uncategorized in drill-down view

            # Use SNAPSHOT if available, fallback to current rate conversion
            if tx.base_amount is not None:
                amount = Decimal(str(tx.base_amount)) + Decimal(str(tx.base_edv_amount or 0))
            else:
                amount = convert_to_base(tx.amount, tx.currency, base_currency)
                if tx.edv_amount:
                    amount += Decimal(str(tx.edv_amount))
            
            if cat_name not in data:
                data[cat_name] = {"amount": Decimal("0.0"), "color": cat_color, "id": cat_id}
            data[cat_name]["amount"] += amount
            
        return [{"id": d["id"], "name": name, "amount": float(d["amount"]), "color": d["color"]} for name, d in data.items()]

def get_daily_spending_trend(company_id, month=None, year=None, date_from=None, date_to=None):
    from services.currency_service import convert_to_base
    from database.models import Company
    import calendar
    
    with get_session() as session:
        now = datetime.now()
        company = session.get(Company, company_id)
        base_currency = company.currency if company else "AZN"

        q = session.query(Transaction).filter(
            Transaction.company_id == company_id,
            Transaction.type == 'expense'
        )
        if date_from and date_to:
            q = q.filter(Transaction.date >= date_from, Transaction.date <= date_to)
            end_day = (date_to - date_from).days + 1
            labels = list(range(1, end_day + 1))
            daily_sums = {i: Decimal("0.0") for i in labels}
            for tx in q.order_by(Transaction.date).all():
                offset = (tx.date.date() - date_from.date()).days + 1
                if offset in daily_sums:
                    if tx.base_amount is not None:
                        amt = Decimal(str(tx.base_amount)) + Decimal(str(tx.base_edv_amount or 0))
                    else:
                        amt = convert_to_base(tx.amount, tx.currency, base_currency)
                        if tx.edv_amount:
                            amt += Decimal(str(tx.edv_amount))
                    daily_sums[offset] += amt
        elif date_from is None and date_to is None:
            # All Time: bucket by month number across all history
            all_txs = q.order_by(Transaction.date).all()
            if not all_txs:
                return [], []
            first = all_txs[0].date.date()
            last  = all_txs[-1].date.date()
            end_day = (last - first).days + 1
            labels = list(range(1, end_day + 1))
            daily_sums = {i: Decimal("0.0") for i in labels}
            for tx in all_txs:
                offset = (tx.date.date() - first).days + 1
                if offset in daily_sums:
                    if tx.base_amount is not None:
                        amt = Decimal(str(tx.base_amount)) + Decimal(str(tx.base_edv_amount or 0))
                    else:
                        amt = convert_to_base(tx.amount, tx.currency, base_currency)
                        if tx.edv_amount:
                            amt += Decimal(str(tx.edv_amount))
                    daily_sums[offset] += amt
        else:
            month = month or now.month
            year  = year  or now.year
            q = q.filter(
                func.extract('month', Transaction.date) == month,
                func.extract('year',  Transaction.date) == year
            )
            days_in_month = calendar.monthrange(year, month)[1]
            if year == now.year and month == now.month:
                days_in_month = now.day
            labels = list(range(1, days_in_month + 1))
            daily_sums = {i: Decimal("0.0") for i in labels}
            for tx in q.order_by(Transaction.date).all():
                day = tx.date.day
                if day in daily_sums:
                    if tx.base_amount is not None:
                        amt = Decimal(str(tx.base_amount)) + Decimal(str(tx.base_edv_amount or 0))
                    else:
                        amt = convert_to_base(tx.amount, tx.currency, base_currency)
                        if tx.edv_amount:
                            amt += Decimal(str(tx.edv_amount))
                    daily_sums[day] += amt
                
        cumulative = []
        total = Decimal("0.0")
        for i in labels:
            total += daily_sums[i]
            cumulative.append(float(total))
            
        return labels, cumulative

def get_daily_cashflow_series(company_id, date_from=None, date_to=None, status=None):
    from services.currency_service import convert_to_base
    from database.models import Company
    
    with get_session() as session:
        now = datetime.now()
        company = session.get(Company, company_id)
        base_currency = company.currency if company else "AZN"

        q = session.query(Transaction).filter(
            Transaction.company_id == company_id,
            Transaction.type.in_(['income', 'expense'])
        )
        if status and status != 'All':
            st = status.lower()
            if st == 'pending':
                q = q.filter(Transaction.status.in_(['pending', 'qaime_gozleyir', 'confirmed']))
            else:
                q = q.filter(Transaction.status == st)
        
        if date_from and date_to:
            q = q.filter(Transaction.date >= date_from, Transaction.date <= date_to)
            start_date = date_from.date()
            end_date = date_to.date()
        else:
            # fallback to current month
            start_date = datetime(now.year, now.month, 1).date()
            import calendar
            last_day = calendar.monthrange(now.year, now.month)[1]
            end_date = datetime(now.year, now.month, last_day).date()
            q = q.filter(
                extract('month', Transaction.date) == now.month,
                extract('year',  Transaction.date) == now.year
            )

        days_count = (end_date - start_date).days + 1
        labels = []
        for i in range(days_count):
            d = start_date + __import__('datetime').timedelta(days=i)
            labels.append(d.strftime("%b %d"))
            
        daily_inc = {i: Decimal("0.0") for i in range(days_count)}
        daily_exp = {i: Decimal("0.0") for i in range(days_count)}
        
        for tx in q.order_by(Transaction.date).all():
            offset = (tx.date.date() - start_date).days
            if 0 <= offset < days_count:
                if tx.base_amount is not None:
                    amt = Decimal(str(tx.base_amount)) + Decimal(str(tx.base_edv_amount or 0))
                else:
                    amt = convert_to_base(tx.amount, tx.currency, base_currency)
                    if tx.edv_amount:
                        amt += Decimal(str(tx.edv_amount))
                
                if tx.type == 'income':
                    daily_inc[offset] += amt
                else:
                    daily_exp[offset] += amt
                    
        inc_series = [float(daily_inc[i]) for i in range(days_count)]
        exp_series = [float(daily_exp[i]) for i in range(days_count)]
        
        return labels, inc_series, exp_series


def get_dashboard_summary(company_id, date_from=None, date_to=None, status=None):
    """Calculates Income, Expenses, and Total Balance for the Dashboard.
    Optionally filters by date_from / date_to; defaults to current month.
    """
    from services.currency_service import convert_to_base
    from database.models import Company

    with get_session() as session:
        if not company_id:
            return {
                "total_balance": 0.0, "total_income": 0.0, "total_expenses": 0.0, 
                "net_profit": 0.0, "base_currency": "AZN",
                "top_expense_category": "None", "avg_daily_spend": 0.0, "savings_rate": 0.0
            }

        company = session.get(Company, company_id)
        base_currency = company.currency if company else "AZN"

        # Calculate normalized total balance (always real-time)
        accounts = session.query(Account).filter(
            Account.company_id == company_id,
            Account.is_archived != True
        ).all()
        total_balance = sum(float(convert_to_base(acc.balance, acc.currency, base_currency)) for acc in accounts)

        # Build period filter
        now = datetime.now()
        q = (session.query(Transaction)
             .options(joinedload(Transaction.category))
             .filter(Transaction.company_id == company_id))

        if date_from and date_to:
            # Explicit date range
            q = q.filter(Transaction.date >= date_from, Transaction.date <= date_to)
            days_in_period = max(1, (date_to.date() - date_from.date()).days + 1)
        elif date_from is None and date_to is None:
            # All Time — no date filter, use total days span
            first_tx_record = session.query(Transaction).filter(
                Transaction.company_id == company_id
            ).order_by(Transaction.date.asc()).first()
            first_tx = first_tx_record.date if first_tx_record else None
            
            last_tx_record = session.query(Transaction).filter(
                Transaction.company_id == company_id
            ).order_by(Transaction.date.desc()).first()
            last_tx = last_tx_record.date if last_tx_record else now
            
            if first_tx:
                end_date = max(last_tx.date(), now.date())
                days_in_period = max(1, (end_date - first_tx.date()).days + 1)
            else:
                days_in_period = 1
        else:
            # Default: current month
            month, year = now.month, now.year
            q = q.filter(
                extract('month', Transaction.date) == month,
                extract('year',  Transaction.date) == year
            )
            days_in_period = now.day

        if status and status != 'All':
            st = status.lower()
            if st == 'pending':
                q = q.filter(Transaction.status.in_(['pending', 'qaime_gozleyir', 'confirmed']))
            else:
                q = q.filter(Transaction.status == st)

        month_txs = q.all()
        
        total_income = Decimal("0.0")
        total_expenses = Decimal("0.0")
        cat_spending = {}
        
        for tx in month_txs:
            if tx.base_amount is not None:
                total_amt = Decimal(str(tx.base_amount)) + Decimal(str(tx.base_edv_amount or 0))
            else:
                amt = convert_to_base(tx.amount, tx.currency, base_currency)
                edv = Decimal(str(tx.edv_amount or 0))
                total_amt = amt + edv

            if tx.type == 'income':
                total_income += total_amt
            elif tx.type == 'expense':
                total_expenses += total_amt
                cat = tx.category
                if cat and cat.parent_id:
                    parent = getattr(cat, 'parent', None)
                    cat_name = parent.name if parent else cat.name
                else:
                    cat_name = cat.name if cat else "Uncategorized"
                cat_spending[cat_name] = cat_spending.get(cat_name, Decimal("0.0")) + total_amt

        top_cat = "None"
        if cat_spending:
            top_cat = max(cat_spending, key=cat_spending.get)
            
        avg_daily = total_expenses / days_in_period if days_in_period > 0 else Decimal("0.0")
        savings_rate = ((total_income - total_expenses) / total_income * 100) if total_income > 0 else Decimal("0.0")

        return {
            "total_balance":   float(total_balance),
            "total_income":    float(total_income),
            "total_expenses":  float(total_expenses),
            "net_profit":      float(total_income - total_expenses),
            "base_currency":   base_currency,
            "top_expense_category": top_cat,
            "avg_daily_spend": float(avg_daily),
            "savings_rate":    float(max(0, savings_rate))
        }

def get_filtered_transactions_summary(company_id, filters=None):
    from services.currency_service import convert_to_base
    from database.models import Company, Category, Account

    with get_session() as session:
        if not company_id:
            return {"total_income": 0.0, "total_expenses": 0.0, "net_profit": 0.0, "total_vat": 0.0, "base_currency": "AZN"}

        company = session.get(Company, company_id)
        base_currency = company.currency if company else "AZN"

        query = session.query(Transaction.type, Transaction.amount, Transaction.currency, 
                              Transaction.edv_amount, Transaction.base_amount, Transaction.base_edv_amount)\
                       .filter(Transaction.company_id == company_id)

        if filters:
            if filters.get('type') and filters['type'] != 'All':
                query = query.filter(Transaction.type == filters['type'].lower())
            if filters.get('account_id') and filters['account_id'] != 'All':
                query = query.filter(
                    (Transaction.account_id == filters['account_id']) |
                    (Transaction.to_account_id == filters['account_id'])
                )
            if filters.get('category_id') and filters['category_id'] != 'All':
                cat_id = filters['category_id']
                child_cats = session.query(Category.id).filter(Category.parent_id == cat_id).all()
                child_ids = [c[0] for c in child_cats]
                query = query.filter(Transaction.category_id.in_([cat_id] + child_ids))
            if filters.get('project_id') and filters['project_id'] != 'All':
                query = query.filter(Transaction.project_id == filters['project_id'])
            if filters.get('status') and filters['status'] != 'All':
                query = query.filter(Transaction.status == filters['status'].lower())
            if filters.get('search'):
                term = f"%{filters['search']}%"
                query = query.join(Category, Transaction.category_id == Category.id, isouter=True)\
                             .join(Account, Transaction.account_id == Account.id)\
                             .filter(
                    Transaction.description.ilike(term) |
                    Transaction.counterparty.ilike(term) |
                    Category.name.ilike(term) |
                    Account.name.ilike(term)
                )
            if filters.get('date_from') and filters.get('date_to'):
                query = query.filter(
                    Transaction.date >= filters['date_from'],
                    Transaction.date <= filters['date_to']
                )

        txs = query.all()

        total_income = Decimal("0.0")
        total_expenses = Decimal("0.0")
        income_vat = Decimal("0.0")
        expense_vat = Decimal("0.0")

        for t_type, t_amount, t_curr, t_edv, b_amt, b_edv in txs:
            vat_norm = Decimal("0.0")
            if b_amt is not None:
                norm = Decimal(str(b_amt)) + Decimal(str(b_edv or 0))
                vat_norm = Decimal(str(b_edv or 0))
            else:
                norm = convert_to_base(t_amount, t_curr, base_currency)
                if t_edv:
                    vat_norm = Decimal(str(t_edv))
                    norm += vat_norm
            
            if t_type == 'income':
                total_income += norm
                income_vat += vat_norm
            elif t_type == 'expense':
                total_expenses += norm
                expense_vat += vat_norm

        return {
            "total_income":    float(total_income),
            "total_expenses":  float(total_expenses),
            "net_profit":      float(total_income - total_expenses),
            "income_vat":      float(income_vat),
            "expense_vat":     float(expense_vat),
            "base_currency":   base_currency,
        }


def get_projected_balance(company_id):
    """Returns current balance adjusted by all pending/unpaid transactions for different timeframes.
    Only uses unpaid Transactions - PlannedPayments are not considered.
    """
    from services.currency_service import convert_to_base
    from database.models import Company
    from datetime import datetime, timedelta

    with get_session() as session:
        company = session.get(Company, company_id)
        base_currency = company.currency if company else "AZN"

        accounts = session.query(Account).filter(
            Account.company_id == company_id,
            Account.is_archived != True
        ).all()
        total_balance = sum(float(convert_to_base(acc.balance, acc.currency, base_currency)) for acc in accounts)

        # Only unpaid/pending transactions
        unpaid_txs = session.query(Transaction).filter(
            Transaction.company_id == company_id,
            Transaction.status != 'paid',
            Transaction.type.in_(['income', 'expense'])
        ).all()

        now = datetime.now()
        thirty_days = now + timedelta(days=30)
        ninety_days = now + timedelta(days=90)

        tot_inc_all = Decimal("0.0")
        tot_out_all = Decimal("0.0")
        tot_inc_30  = Decimal("0.0")
        tot_out_30  = Decimal("0.0")
        tot_inc_90  = Decimal("0.0")
        tot_out_90  = Decimal("0.0")

        for t in unpaid_txs:
            # Use snapshot if available, else convert at current rate
            if t.base_amount is not None:
                converted = Decimal(str(t.base_amount)) + Decimal(str(t.base_edv_amount or 0))
            else:
                amt = Decimal(str(t.amount)) + Decimal(str(t.edv_amount or 0))
                converted = convert_to_base(amt, t.currency, base_currency)

            tx_date = t.date  # datetime

            if t.type == 'expense':
                tot_out_all += converted
            elif t.type == 'income':
                tot_inc_all += converted

            if tx_date <= thirty_days:
                if t.type == 'expense':
                    tot_out_30 += converted
                elif t.type == 'income':
                    tot_inc_30 += converted

            if tx_date <= ninety_days:
                if t.type == 'expense':
                    tot_out_90 += converted
                elif t.type == 'income':
                    tot_inc_90 += converted

        cur_bal = Decimal(str(total_balance))
        return {
            "current_balance":        float(total_balance),
            "projected_balance_all":  float(cur_bal + tot_inc_all - tot_out_all),
            "projected_balance_30d":  float(cur_bal + tot_inc_30 - tot_out_30),
            "projected_balance_90d":  float(cur_bal + tot_inc_90 - tot_out_90),
            "base_currency":          base_currency
        }

def get_summary(company_id, period="all"):
    """Wrapper that maps a period string to get_dashboard_summary date ranges."""
    if period == "all":
        return get_dashboard_summary(company_id, date_from=None, date_to=None)
    elif period == "monthly":
        now = datetime.now()
        import calendar
        last_day = calendar.monthrange(now.year, now.month)[1]
        date_from = datetime(now.year, now.month, 1)
        date_to = datetime(now.year, now.month, last_day, 23, 59, 59)
        return get_dashboard_summary(company_id, date_from=date_from, date_to=date_to)
    else:
        return get_dashboard_summary(company_id)

def get_monthly_series(company_id, months=6, date_from=None, date_to=None, status=None):
    """Returns labels (month names) and income/expense series for the last N months or a specific date range."""
    from services.currency_service import convert_to_base
    from database.models import Company
    
    with get_session() as session:
        now = datetime.now()
        company = session.get(Company, company_id)
        base_currency = company.currency if company else "AZN"

        labels = []
        income_series = []
        expense_series = []

        if date_from and date_to:
            start_m, start_y = date_from.month, date_from.year
            end_m, end_y = date_to.month, date_to.year
            month_list = []
            curr_m, curr_y = start_m, start_y
            while (curr_y < end_y) or (curr_y == end_y and curr_m <= end_m):
                month_list.append((curr_m, curr_y))
                curr_m += 1
                if curr_m > 12:
                    curr_m = 1
                    curr_y += 1
        elif date_from is None and date_to is None:
            # All Time - dynamically calculate based on first transaction
            first_tx_record = session.query(Transaction).filter(
                Transaction.company_id == company_id
            ).order_by(Transaction.date.asc()).first()
            first_tx = first_tx_record.date if first_tx_record else None
            
            last_tx_record = session.query(Transaction).filter(
                Transaction.company_id == company_id
            ).order_by(Transaction.date.desc()).first()
            last_tx = last_tx_record.date if last_tx_record else now

            month_list = []
            if first_tx:
                start_m, start_y = first_tx.month, first_tx.year
                end_m, end_y = last_tx.month, last_tx.year
                
                # Ensure we at least show up to the current month if all txs are in the past
                if (end_y < now.year) or (end_y == now.year and end_m < now.month):
                    end_m, end_y = now.month, now.year
                    
                curr_m, curr_y = start_m, start_y
                while (curr_y < end_y) or (curr_y == end_y and curr_m <= end_m):
                    month_list.append((curr_m, curr_y))
                    curr_m += 1
                    if curr_m > 12:
                        curr_m = 1
                        curr_y += 1
            else:
                month_list = [(now.month, now.year)]
        else:
            month_list = []
            for i in range(months - 1, -1, -1):
                m = now.month - i
                y = now.year
                while m <= 0:
                    m += 12
                    y -= 1
                month_list.append((m, y))

        for m, y in month_list:
            dt = datetime(y, m, 1)
            labels.append(dt.strftime("%b %Y"))

            q = session.query(Transaction.type, Transaction.amount, Transaction.currency, 
                                 Transaction.edv_amount, Transaction.base_amount, Transaction.base_edv_amount).filter(
                Transaction.company_id == company_id,
                extract('month', Transaction.date) == m,
                extract('year', Transaction.date) == y,
                Transaction.type.in_(['income', 'expense'])
            )
            if status and status != 'All':
                st = status.lower()
                if st == 'pending':
                    q = q.filter(Transaction.status.in_(['pending', 'qaime_gozleyir', 'confirmed']))
                else:
                    q = q.filter(Transaction.status == st)
                
            txs = q.all()

            m_inc = Decimal("0.0")
            m_exp = Decimal("0.0")
            for t_type, t_amount, t_curr, t_edv, b_amt, b_edv in txs:
                if b_amt is not None:
                    norm = Decimal(str(b_amt)) + Decimal(str(b_edv or 0))
                else:
                    norm = convert_to_base(t_amount, t_curr, base_currency)
                    if t_edv:
                        norm += Decimal(str(t_edv))
                
                if t_type == 'income': m_inc += norm
                else: m_exp += norm
            
            income_series.append(float(m_inc))
            expense_series.append(float(m_exp))

        return labels, income_series, expense_series