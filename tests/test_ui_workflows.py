import pytest
from PySide6.QtWidgets import QApplication

from src.ui.views.goals_view import GoalTransactionDialog, GoalsView
from src.ui.views.settings_view import SettingsView


@pytest.fixture
def qt_app():
    app = QApplication.instance() or QApplication([])
    return app


def test_goal_view_exposes_contribution_and_withdrawal_actions(qt_app):
    view = GoalsView(None)
    assert callable(view.show_goal_transaction_dialog)
    assert GoalTransactionDialog(1, "contribution").windowTitle() == "Contribution Goal"
    assert GoalTransactionDialog(1, "withdrawal").windowTitle() == "Withdrawal Goal"


def test_settings_view_loads_and_saves_versioned_preferences(qt_app, tmp_path, monkeypatch):
    import src.core.config as config

    preferences_path = tmp_path / "preferences.json"
    monkeypatch.setattr(config, "PREFERENCES_PATH", str(preferences_path))
    view = SettingsView(None)
    view.size_combo.setCurrentText("18px")
    view.apply_settings()
    stored = config.load_preferences()
    assert stored["version"] == config.PREFERENCES_VERSION
    assert stored["font_size"] == "18px"
    assert preferences_path.exists()
