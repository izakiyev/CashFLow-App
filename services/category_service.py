from database.session import get_session
from database.models import Category

def get_categories(company_id, type_filter=None):
    with get_session() as session:
        query = session.query(Category).filter(Category.company_id == company_id)
        if type_filter:
            query = query.filter(Category.type == type_filter)
        # Serialize ORM objects before session closes to avoid DetachedInstanceError
        cats = query.order_by(Category.name).all()
        return [
            type('Cat', (), {
                'id': c.id, 'name': c.name, 'type': c.type,
                'color': c.color, 'icon': c.icon, 'is_default': c.is_default,
                'parent_id': c.parent_id, 'company_id': c.company_id
            })()
            for c in cats
        ]

def create_category(data):
    with get_session() as session:
        # Ensure parent_id is an integer or None
        if "parent_id" in data and data["parent_id"] == "":
            data["parent_id"] = None
            
        cat = Category(**data)
        session.add(cat)
        session.commit()
        session.refresh(cat)
        return cat

def update_category(category_id, data):
    with get_session() as session:
        cat = session.get(Category, category_id)
        if not cat: return None
        for k, v in data.items():
            setattr(cat, k, v)
        session.commit()
        return cat

def delete_category(category_id):
    from database.models import Transaction, PlannedPayment
    with get_session() as session:
        cat = session.query(Category).filter(Category.id == category_id).first()
        if cat:
            # Gracefully detach transactions and planned payments
            session.query(Transaction).filter(Transaction.category_id == category_id).update({"category_id": None})
            session.query(PlannedPayment).filter(PlannedPayment.category_id == category_id).update({"category_id": None})
            
            # Delete associated budgets
            from database.models import Budget
            session.query(Budget).filter(Budget.category_id == category_id).delete()
            
            session.delete(cat)
            session.commit()
            return True
        return False
