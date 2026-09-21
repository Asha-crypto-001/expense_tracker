import pytest
from datetime import date, time
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from PySide6.QtWidgets import QApplication
from src.models import Base
from src.services import AuthService, AccountService, TransactionService, BudgetService, GoalService

# Setup Test DB
engine = create_engine("sqlite:///:memory:", echo=False)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture
def db():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    yield db
    db.close()
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def auth():
    return AuthService()

@pytest.fixture
def qt_app():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app

def test_auth_registration(db, auth):
    success, msg = auth.register(db, "testuser", "test@example.com", "password123")
    assert success == True
    
    # Check defaults were created
    user = auth.login(db, "testuser", "password123")
    assert user[0] == True
    assert auth.get_current_user().username == "testuser"
    
    # check default account
    acc_service = AccountService()
    accs = acc_service.get_accounts(db, auth.get_current_user().id)
    assert len(accs) == 1
    assert accs[0].name == "Cash"

def test_transaction_balance_engine(db, auth):
    auth.register(db, "usr1", "usr1@mail.com", "password")
    auth.login(db, "usr1", "password")
    user = auth.get_current_user()
    
    acc_service = AccountService()
    tx_service = TransactionService()
    
    acc1 = acc_service.create_account(db, user.id, "Bank", "Bank", 1000)
    acc2 = acc_service.create_account(db, user.id, "Savings", "Savings", 0)
    
    # 1. Income
    tx_service.create_transaction(db, user.id, acc1.id, 500, "income", date.today(), time(), "Salary")
    db.refresh(acc1)
    assert acc1.current_balance == 1500
    
    # 2. Expense
    tx_service.create_transaction(db, user.id, acc1.id, 200, "expense", date.today(), time(), "Groceries")
    db.refresh(acc1)
    assert acc1.current_balance == 1300
    
    # 3. Transfer
    tx_service.create_transaction(db, user.id, acc1.id, 300, "transfer", date.today(), time(), "To Savings", to_account_id=acc2.id)
    db.refresh(acc1)
    db.refresh(acc2)
    assert acc1.current_balance == 1000
    assert acc2.current_balance == 300
    
    # 4. Total Net position shouldn't be affected by transfer
    total = acc_service.get_total_balance(db, user.id)
    # default Cash is 0, Bank is 1000, Savings is 300 -> 1300
    assert total == 1300

def test_delete_transaction_reverts_balance(db, auth):
    auth.register(db, "usr2", "usr2@mail.com", "password")
    auth.login(db, "usr2", "password")
    user = auth.get_current_user()
    
    acc_service = AccountService()
    tx_service = TransactionService()
    
    acc = acc_service.create_account(db, user.id, "Wallet", "Cash", 500)
    
    tx = tx_service.create_transaction(db, user.id, acc.id, 100, "expense", date.today(), time(), "Coffee")
    db.refresh(acc)
    assert acc.current_balance == 400
    
    tx_service.delete_transaction(db, tx.id, user.id)
    db.refresh(acc)
    assert acc.current_balance == 500


def test_budget_and_goal_service_flow(db, auth):
    auth.register(db, "usr3", "usr3@mail.com", "password")
    auth.login(db, "usr3", "password")
    user = auth.get_current_user()

    acc_service = AccountService()
    tx_service = TransactionService()
    budget_service = BudgetService()
    goal_service = GoalService()

    account = acc_service.create_account(db, user.id, "Main", "Bank", 1000)
    default_category = db.query(__import__('src.models', fromlist=['Category']).Category).filter_by(user_id=user.id, name="Food").first()
    budget = budget_service.create_budget(db, user.id, 5000, "monthly", default_category.id)
    tx_service.create_transaction(db, user.id, account.id, 1500, "expense", date.today(), time(), "Groceries", category_id=default_category.id)

    assert budget.amount == 5000
    assert budget_service.get_budget_usage(db, budget) == 1500

    goal = goal_service.create_goal(db, user.id, "Emergency Fund", 20000)
    goal = goal_service.add_contribution(db, user.id, goal.id, 5000)
    assert goal.current_amount == 5000


def test_service_rejects_invalid_transaction_and_cross_user_data(db, auth):
    auth.register(db, "owner", "owner@example.com", "password")
    auth.login(db, "owner", "password")
    owner = auth.get_current_user()
    owner_account = AccountService().create_account(db, owner.id, "Owner", "Cash", 100)
    owner_category = db.query(__import__("src.models", fromlist=["Category"]).Category).filter_by(
        user_id=owner.id, name="Food"
    ).first()

    other_auth = AuthService()
    other_auth.register(db, "other", "other@example.com", "password")
    other = db.query(__import__("src.models", fromlist=["User"]).User).filter_by(username="other").first()
    other_account = AccountService().create_account(db, other.id, "Other", "Cash", 100)

    tx_service = TransactionService()
    for amount in (0, -1):
        with pytest.raises(ValueError, match="greater than zero"):
            tx_service.create_transaction(
                db, owner.id, owner_account.id, amount, "expense",
                date.today(), time(), "Invalid"
            )

    with pytest.raises(ValueError, match="Invalid account"):
        tx_service.create_transaction(
            db, owner.id, other_account.id, 10, "expense",
            date.today(), time(), "Cross-user"
        )
    with pytest.raises(ValueError, match="Invalid category"):
        tx_service.create_transaction(
            db, owner.id, owner_account.id, 10, "expense",
            date.today(), time(), "Cross-user", category_id=999999
        )
    with pytest.raises(ValueError, match="differ"):
        tx_service.create_transaction(
            db, owner.id, owner_account.id, 10, "transfer",
            date.today(), time(), "Same account", to_account_id=owner_account.id
        )
    assert owner_account.current_balance == 100
    assert owner_category is not None


def test_goal_contribution_requires_owner(db, auth):
    auth.register(db, "goalowner", "goalowner@example.com", "password")
    owner = db.query(__import__("src.models", fromlist=["User"]).User).filter_by(username="goalowner").first()
    goal = GoalService().create_goal(db, owner.id, "Goal", 1000)

    with pytest.raises(ValueError, match="Goal not found"):
        GoalService().add_contribution(db, owner.id + 999, goal.id, 100)


def test_goal_withdrawal_reduces_saved_amount_and_reactivates(db, auth):
    auth.register(db, "withdraw", "withdraw@example.com", "password")
    owner = db.query(__import__("src.models", fromlist=["User"]).User).filter_by(username="withdraw").first()
    service = GoalService()
    goal = service.create_goal(db, owner.id, "Goal", 1000)
    service.add_contribution(db, owner.id, goal.id, 1000)
    goal = service.withdraw(db, owner.id, goal.id, 250)
    assert goal.current_amount == 750
    assert goal.status == "active"
    with pytest.raises(ValueError, match="exceed"):
        service.withdraw(db, owner.id, goal.id, 751)


def test_password_policy_and_login_lockout(db, auth):
    success, message = auth.register(db, "short", "short@example.com", "short")
    assert success is False
    assert "8 characters" in message

    success, _ = auth.register(db, "locked", "locked@example.com", "password")
    assert success is True
    for _ in range(5):
        success, _ = auth.login(db, "locked", "wrongpass")
        assert success is False
    success, message = auth.login(db, "locked", "password")
    assert success is False
    assert "temporarily locked" in message


def test_monthly_summary_excludes_transfers_and_other_months(db, auth):
    auth.register(db, "summary", "summary@example.com", "password")
    auth.login(db, "summary", "password")
    user = auth.get_current_user()
    account = AccountService().create_account(db, user.id, "Main", "Bank", 1000)
    tx_service = TransactionService()
    current = date.today()
    previous_month = 12 if current.month == 1 else current.month - 1
    previous_year = current.year - 1 if current.month == 1 else current.year

    tx_service.create_transaction(
        db, user.id, account.id, 500, "income", current, time(), "Salary"
    )
    tx_service.create_transaction(
        db, user.id, account.id, 125, "expense", current, time(), "Food"
    )
    tx_service.create_transaction(
        db, user.id, account.id, 999, "income",
        date(previous_year, previous_month, 1), time(), "Old salary"
    )
    target = AccountService().create_account(db, user.id, "Savings", "Bank", 0)
    tx_service.create_transaction(
        db, user.id, account.id, 200, "transfer", current, time(), "Move",
        to_account_id=target.id
    )

    assert tx_service.get_monthly_summary(
        db, user.id, current.year, current.month
    ) == {"income": 500, "expense": 125, "savings": 375}


def test_budget_and_goal_views_expose_add_dialogs(qt_app):
    from src.ui.views.budgets_view import BudgetsView
    from src.ui.views.goals_view import GoalsView

    budgets_view = BudgetsView(None)
    goals_view = GoalsView(None)

    assert hasattr(budgets_view, "show_add_budget_dialog")
    assert callable(budgets_view.show_add_budget_dialog)
    assert hasattr(goals_view, "show_add_goal_dialog")
    assert callable(goals_view.show_add_goal_dialog)


def test_transaction_dialog_is_safe_without_authentication(qt_app):
    from src.ui.dialogs.add_transaction_dialog import AddTransactionDialog

    dialog = AddTransactionDialog()
    assert not dialog.save_btn.isEnabled()
    assert "sign in" in dialog.error_label.text().lower()


def test_accounts_view_exposes_account_creation(qt_app):
    from src.ui.views.accounts_view import AccountsView

    view = AccountsView(None)
    assert callable(view.show_add_dialog)
