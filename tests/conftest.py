import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from database.models import Base, Company, Account, User

@pytest.fixture(scope="session")
def test_engine():
    # Use StaticPool so all connections (and thus sessions) share the same in-memory db
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False
    )
    yield engine

@pytest.fixture(autouse=True)
def mock_session_local(monkeypatch, test_engine):
    # Setup tables
    Base.metadata.create_all(bind=test_engine)
    
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    
    # Patch the canonical source used by get_session() — this covers ALL services
    import database.engine
    monkeypatch.setattr(database.engine, "SessionLocal", SessionLocal)
    
    # Patch the session module's imported reference as well
    import database.session as session_module
    monkeypatch.setattr(session_module, "SessionLocal", SessionLocal)
    
    yield
    
    # Teardown tables after each test
    Base.metadata.drop_all(bind=test_engine)

@pytest.fixture
def seed_company():
    import database.engine
    session = database.engine.SessionLocal()
    user = User(name="Test User", email="test@local.machine")
    session.add(user)
    session.flush()
    company = Company(name="Test Company", currency="USD", owner_id=user.id)
    session.add(company)
    session.commit()
    session.refresh(company)
    company_id = company.id
    session.close()
    return company_id

@pytest.fixture
def seed_account(seed_company):
    import database.engine
    session = database.engine.SessionLocal()
    account = Account(
        company_id=seed_company,
        name="Test Account",
        type="Bank",
        currency="USD",
        balance=100.0
    )
    session.add(account)
    session.commit()
    session.refresh(account)
    account_id = account.id
    session.close()
    return account_id
