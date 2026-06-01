from database.session import get_session
from database.models import PlannedPayment, Transaction, Account, Category
from sqlalchemy.orm import joinedload
from datetime import datetime
from types import SimpleNamespace

def get_planned_payments(company_id):
    """Returns planned payments as SimpleNamespace objects (safe after session closes)."""
    with get_session() as session:
        query = (
            session.query(PlannedPayment)
            .options(joinedload(PlannedPayment.category).joinedload(Category.parent))
            .filter(PlannedPayment.company_id == company_id)
        )
        
        rows = query.order_by(PlannedPayment.status.desc(), PlannedPayment.due_date).all()
        return [
            SimpleNamespace(
                id=p.id,
                company_id=p.company_id,
                account_id=p.account_id,
                category_id=p.category_id,
                type=p.type,
                amount=p.amount,
                currency=p.currency,
                description=p.description,
                counterparty=p.counterparty,
                due_date=p.due_date,
                status=p.status,
                recurring=p.recurring,
                next_due_date=p.next_due_date,
                paid_at=p.paid_at,
                edv_amount=p.edv_amount,
                edv_account_id=p.edv_account_id,
                category_name=f"{p.category.parent.name} > {p.category.name}" if p.category and p.category.parent else (p.category.name if p.category else None)
            )
            for p in rows
        ]

def create_planned_payment(data):
    with get_session() as session:
        planned = PlannedPayment(**data)
        session.add(planned)
        session.commit()
        session.refresh(planned)
        return planned

def confirm_planned_payment(payment_id):
    """
    Moves a planned payment to the main Transactions ledger with 'confirmed' status.
    Does NOT update account balance yet (that happens in 'pay_transaction').
    """
    def _add_months(d, months):
        month = d.month - 1 + months
        year = d.year + month // 12
        month = month % 12 + 1
        is_leap = (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0)
        day = min(d.day, [31, 29 if is_leap else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month - 1])
        return d.replace(year=year, month=month, day=day)

    with get_session() as session:
        payment = session.query(PlannedPayment).filter(PlannedPayment.id == payment_id).first()
        if payment and payment.status != 'paid':
            payment.status = 'paid' # Mark planned item as handled
            payment.paid_at = datetime.utcnow()
            
            # Move to Transactions ledger as CONFIRMED
            # SNAPSHOT: Capture value in base currency at time of confirmation
            from database.models import Company
            from services.currency_service import convert_to_base
            
            company = session.get(Company, payment.company_id)
            base_curr = company.currency if company else "AZN"
            base_amount = convert_to_base(payment.amount, payment.currency, base_curr)
            base_edv_amount = convert_to_base(payment.edv_amount or 0, payment.currency, base_curr)

            txn = Transaction(
                company_id=payment.company_id,
                account_id=payment.account_id,
                category_id=payment.category_id,
                type=payment.type,
                amount=payment.amount,
                currency=payment.currency,
                description=f"Planned: {payment.description}",
                counterparty=payment.counterparty,
                date=payment.paid_at,
                edv_amount=payment.edv_amount,
                edv_account_id=payment.edv_account_id,
                status="confirmed",
                base_amount=base_amount,
                base_edv_amount=base_edv_amount
            )
            session.add(txn)
            
            # NOTE: We NO LONGER update account balance here. 
            # Balance update is now deferred until the transaction itself is marked as 'paid'.

            # Auto-spawn next recurring payment
            if payment.recurring and payment.recurring != 'none':
                from datetime import timedelta
                next_due = payment.due_date
                if payment.recurring == 'weekly':
                    next_due += timedelta(days=7)
                elif payment.recurring == 'monthly':
                    next_due = _add_months(next_due, 1)
                elif payment.recurring == 'yearly':
                    next_due = _add_months(next_due, 12)
                
                new_payment = PlannedPayment(
                    company_id=payment.company_id,
                    account_id=payment.account_id,
                    category_id=payment.category_id,
                    type=payment.type,
                    amount=payment.amount,
                    description=payment.description,
                    counterparty=payment.counterparty,
                    due_date=next_due,
                    status="pending",
                    recurring=payment.recurring,
                    currency=payment.currency,
                    edv_amount=payment.edv_amount,
                    edv_account_id=payment.edv_account_id
                )
                session.add(new_payment)
            
            session.commit()
            return True
        return False


def delete_planned_payment(payment_id):
    with get_session() as session:
        payment = session.query(PlannedPayment).filter(PlannedPayment.id == payment_id).first()
        if payment:
            session.delete(payment)
            session.commit()
            return True
        return False
