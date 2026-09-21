from datetime import date, time

import pytest
from PySide6.QtWidgets import QApplication
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.models import Base, Category
from src.services import AccountService, AuthService, BudgetService, TransactionService
from src.ui.views.dashboard_view import DashboardView


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


@pytest.fixture
def qt_app():
    return QApplication.instance() or QApplication([])


def test_dashboard_snapshot_is_user_scoped_and_excludes_transfers(db):
    auth = AuthService()
    assert auth.register(db, "dash", "dash@example.com", "password")[0]
    user = db.query(__import__("src.models", fromlist=["User"]).User).filter_by(username="dash").first()
    account = AccountService().create_account(db, user.id, "Main", "Bank", 1000)
    savings = AccountService().create_account(db, user.id, "Savings", "Bank", 0)
    category = db.query(Category).filter_by(user_id=user.id, name="Food").first()
    service = TransactionService()
    today = date.today()
    service.create_transaction(db, user.id, account.id, 1000, "income", today, time(), "Salary")
    service.create_transaction(
        db, user.id, account.id, 250, "expense", today, time(), "Food",
        category_id=category.id,
    )
    service.create_transaction(
        db, user.id, account.id, 300, "transfer", today, time(), "Move",
        to_account_id=savings.id,
    )

    snapshot = service.get_dashboard_snapshot(db, user.id, "this_month")
    current = snapshot["current"]
    assert current["income"] == 1000
    assert current["expense"] == 250
    assert current["savings"] == 750
    assert current["categories"] == [("Food", 250)]
    assert current["transactions"][0].type == "transfer"


def test_dashboard_period_selector_and_empty_state(qt_app):
    view = DashboardView(None)
    assert view.period_combo.count() == 6
    view.period_combo.setCurrentIndex(5)
    assert not view.custom_start.isHidden()
    assert not view.custom_end.isHidden()
    view.cashflow_chart.set_points([])
    assert view.cashflow_chart.points == []


def test_dashboard_period_preferences_and_budget_range(db, qt_app, monkeypatch, tmp_path):
    import src.core.config as config

    monkeypatch.setattr(config, "PREFERENCES_PATH", str(tmp_path / "preferences.json"))
    view = DashboardView(None)
    view.period_combo.setCurrentIndex(5)
    view.custom_start.setDate(view.custom_start.date().addDays(-7))
    view.custom_start.editingFinished.emit()
    stored = config.load_preferences()
    assert stored["dashboard_period"] == "custom"
    assert stored["dashboard_custom_start"]
    reloaded = DashboardView(None)
    assert reloaded.period_combo.currentData() == "custom"
    assert reloaded.custom_start.date() == view.custom_start.date()

    auth = AuthService()
    assert auth.register(db, "budgetdash", "budgetdash@example.com", "password")[0]
    user = db.query(__import__("src.models", fromlist=["User"]).User).filter_by(
        username="budgetdash"
    ).first()
    category = db.query(Category).filter_by(user_id=user.id, name="Food").first()
    budget = BudgetService().create_budget(db, user.id, 1000, "monthly", category.id)
    account = AccountService().create_account(db, user.id, "Main", "Cash", 0)
    TransactionService().create_transaction(
        db, user.id, account.id, 250, "expense", date.today(), time(), "Food",
        category_id=category.id,
    )
    assert BudgetService().get_budget_usage_for_range(
        db, budget, date.today().replace(day=1), date.today()
    ) == 250
