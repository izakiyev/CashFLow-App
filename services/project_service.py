from database.session import get_session
from database.models import Project, Transaction, PlannedPayment, Company
from sqlalchemy import func
from decimal import Decimal
from services.currency_service import convert_to_base


# ── CRUD ──────────────────────────────────────────────────────────────────────

def get_projects(company_id, status_filter=None):
    """Return all projects for a company, optionally filtered by status."""
    with get_session() as session:
        q = session.query(Project).filter(Project.company_id == company_id)
        if status_filter and status_filter != "all":
            q = q.filter(Project.status == status_filter)
        projects = q.order_by(Project.created_at.desc()).all()
        return [_to_dict(p) for p in projects]


def get_project(project_id):
    """Return a single project dict."""
    with get_session() as session:
        p = session.get(Project, project_id)
        return _to_dict(p) if p else None


def create_project(company_id, name, description="", color="#2970ff",
                   budget=None, start_date=None, end_date=None):
    with get_session() as session:
        p = Project(
            company_id=company_id,
            name=name,
            description=description,
            color=color,
            budget=Decimal(str(budget)) if budget else None,
            start_date=start_date,
            end_date=end_date,
            status="active",
        )
        session.add(p)
        session.commit()
        return p.id


def update_project(project_id, **kwargs):
    with get_session() as session:
        p = session.get(Project, project_id)
        if not p:
            return False
        for key, val in kwargs.items():
            if hasattr(p, key):
                if key == "budget":
                    val = Decimal(str(val)) if val is not None else None
                setattr(p, key, val)
        session.commit()
        return True


def delete_project(project_id):
    """Delete project. Transactions keep their data but project_id becomes NULL."""
    with get_session() as session:
        p = session.get(Project, project_id)
        if not p:
            return False
        session.delete(p)
        session.commit()
        return True


# ── Analytics ─────────────────────────────────────────────────────────────────

def get_project_summary(project_id):
    """
    Returns budget vs actual analytics for a project.
    {
        income, expenses, net, budgeted, spent, remaining,
        is_over_budget, planned_pending,
        base_currency, tx_count
    }
    """
    with get_session() as session:
        p = session.get(Project, project_id)
        if not p:
            return {}

        company = session.get(Company, p.company_id)
        bc = company.currency if company else "AZN"

        # All PAID transactions for this project
        txs = session.query(Transaction).filter(
            Transaction.project_id == project_id,
            Transaction.status != "pending"
        ).all()

        income = Decimal("0")
        expenses = Decimal("0")

        for tx in txs:
            # Use base_amount snapshot if available, else convert live
            if tx.base_amount is not None:
                amt = Decimal(str(tx.base_amount)) + Decimal(str(tx.base_edv_amount or 0))
            else:
                amt = convert_to_base(tx.amount, tx.currency, bc)
                if tx.edv_amount:
                    amt += Decimal(str(tx.edv_amount))

            if tx.type == "income":
                income += amt
            elif tx.type == "expense":
                expenses += amt

        # Pending planned payments for this project
        pending_planned = session.query(PlannedPayment).filter(
            PlannedPayment.project_id == project_id,
            PlannedPayment.status != "paid"
        ).all()

        planned_pending = sum(
            float(convert_to_base(pp.amount, pp.currency, bc))
            for pp in pending_planned
        )

        net = income - expenses
        budgeted = float(p.budget) if p.budget is not None else None
        spent = float(expenses)
        remaining = (budgeted - spent) if budgeted is not None else None
        is_over = (spent > budgeted) if budgeted is not None else False

        return {
            "income": float(income),
            "expenses": float(expenses),
            "net": float(net),
            "budgeted": budgeted,
            "spent": spent,
            "remaining": remaining,
            "is_over_budget": is_over,
            "planned_pending": planned_pending,
            "base_currency": bc,
            "tx_count": len(txs),
        }


def _to_dict(p):
    if p is None:
        return None
    return {
        "id": p.id,
        "company_id": p.company_id,
        "name": p.name,
        "description": p.description or "",
        "color": p.color or "#2970ff",
        "budget": float(p.budget) if p.budget is not None else None,
        "start_date": p.start_date,
        "end_date": p.end_date,
        "status": p.status or "active",
        "created_at": p.created_at,
    }
