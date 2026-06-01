import os
import logging
from database.session import get_session
from database.models import User, Company

logger = logging.getLogger(__name__)

# Module-level variable to store current session
_current_user = None

def _get_windows_identity():
    """Retrieve Windows username and build a local email."""
    try:
        username = os.getlogin()
    except Exception:
        username = os.environ.get("USERNAME", "default_user")
        
    domain = os.environ.get("USERDOMAIN", "local.machine")
    email = f"{username}@{domain}".lower()
    
    return username, email

def auto_login():
    """
    Automatically log in using the Windows username.
    Returns the user dict if found, or None if no user/workspace exists yet.
    Does NOT auto-create users or workspaces — that is always manual via setup screen.
    """
    global _current_user
    username, email = _get_windows_identity()
    
    with get_session() as session:
        user = session.query(User).filter(User.email == email).first()
        
        if not user:
            logger.info(f"No user record found for {email}. Onboarding required.")
            return None
        
        logger.info(f"Auto-logged in as {email}")

        # If user exists but has no active company (e.g., all workspaces deleted)
        if not user.active_company_id:
            first_comp = session.query(Company).filter(Company.owner_id == user.id).first()
            if first_comp:
                user.active_company_id = first_comp.id
                session.commit()
            else:
                # No workspaces at all — signal to show setup screen
                _current_user = {"id": user.id, "name": user.name, "email": user.email, "company_id": None}
                return _current_user
        
        _current_user = {"id": user.id, "name": user.name, "email": user.email, "company_id": user.active_company_id}
        
    return _current_user

def setup_new_user_and_workspace(user_name: str, workspace_name: str, currency: str = "AZN"):
    """
    Called from the onboarding screen to manually create a user + first workspace.
    If a user record for the current Windows identity already exists (e.g., they deleted
    all workspaces), only a new Company is created for them.
    """
    username, email = _get_windows_identity()

    with get_session() as session:
        user = session.query(User).filter(User.email == email).first()

        if not user:
            user = User(name=user_name.strip(), email=email)
            session.add(user)
            session.flush()
        else:
            user.name = user_name.strip()

        company = Company(name=workspace_name.strip(), currency=currency, owner_id=user.id)
        session.add(company)
        session.flush()

        user.active_company_id = company.id
        session.commit()

        global _current_user
        _current_user = {"id": user.id, "name": user.name, "email": user.email, "company_id": company.id}

    return _current_user

def set_active_company(company_id):
    """Update the current user's active company in the session and database."""
    global _current_user
    if not _current_user:
        return False
        
    with get_session() as session:
        user = session.get(User, _current_user["id"])
        if user:
            user.active_company_id = company_id
            session.commit()
            _current_user["company_id"] = company_id
            return True
    return False

def get_current_user():
    """Return the currently authenticated user dictionary."""
    return _current_user

def get_current_user_id():
    return _current_user["id"] if _current_user else None

def logout():
    """Clears the in-memory session state."""
    global _current_user
    _current_user = None
