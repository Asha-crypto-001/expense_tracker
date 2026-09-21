import sys
from pathlib import Path
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QStackedWidget, QPushButton, QLabel, QFrame
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QFont, QIcon

from src.core.config import init_db
from src.services import auth_service
from .views.login_view import LoginView
from .views.dashboard_view import DashboardView
from .views.transactions_view import TransactionsView
from .views.accounts_view import AccountsView
from .views.time_machine_view import TimeMachineView
from .views.budgets_view import BudgetsView
from .views.goals_view import GoalsView
from .views.analytics_view import AnalyticsView
from .views.settings_view import SettingsView
from .views.lock_view import LockView

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ExPlan - Financial Journal")
        self.setMinimumSize(1024, 768)
        self.setup_ui()

    def setup_ui(self):
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        self.main_layout = QHBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # Sidebar
        self.sidebar = QFrame()
        self.sidebar.setObjectName("sidebar")
        self.sidebar.setFixedWidth(250)
        self.sidebar_layout = QVBoxLayout(self.sidebar)
        self.sidebar_layout.setContentsMargins(20, 30, 20, 30)
        self.sidebar_layout.setSpacing(15)

        # App Brand
        self.brand_label = QLabel("ExPlan")
        self.brand_label.setObjectName("brandLabel")
        self.brand_label.setFont(QFont("Georgia", 24, QFont.Weight.Bold)) # Nostalgic premium serif
        self.sidebar_layout.addWidget(self.brand_label)
        
        self.sidebar_layout.addSpacing(30)

        # Navigation Buttons
        self.nav_buttons = {}
        nav_items = [
            ("Dashboard", "dashboard"),
            ("Transactions", "transactions"),
            ("Accounts", "accounts"),
            ("Budgets", "budgets"),
            ("Goals", "goals"),
            ("Analytics", "analytics"),
            ("Time Machine", "time_machine")
        ]

        for label, name in nav_items:
            btn = QPushButton(label)
            btn.setObjectName("navButton")
            btn.setCheckable(True)
            btn.clicked.connect(lambda checked, n=name: self.navigate_to(n))
            self.sidebar_layout.addWidget(btn)
            self.nav_buttons[name] = btn

        self.sidebar_layout.addStretch()

        # Settings & Logout
        self.settings_btn = QPushButton("Settings")
        self.settings_btn.setObjectName("navButton")
        self.settings_btn.clicked.connect(lambda: self.navigate_to("settings"))
        self.sidebar_layout.addWidget(self.settings_btn)

        self.logout_btn = QPushButton("Lock App")
        self.logout_btn.setObjectName("navButton")
        self.logout_btn.clicked.connect(self.handle_lock)
        self.sidebar_layout.addWidget(self.logout_btn)

        # Main Content Area
        self.content_area = QStackedWidget()
        self.content_area.setObjectName("contentArea")
        
        # Add layout
        self.main_layout.addWidget(self.sidebar)
        self.main_layout.addWidget(self.content_area)

        # Setup Views
        self.setup_views()

        # Initial state
        self.sidebar.hide()
        self.navigate_to("login")

    def setup_views(self):
        self.views = {
            "login": LoginView(self),
            "dashboard": DashboardView(self),
            "transactions": TransactionsView(self),
            "accounts": AccountsView(self),
            "budgets": BudgetsView(self),
            "goals": GoalsView(self),
            "analytics": AnalyticsView(self),
            "time_machine": TimeMachineView(self),
            "settings": SettingsView(self),
            "lock": LockView(self)
        }
        
        for name, view in self.views.items():
            self.content_area.addWidget(view)

    def navigate_to(self, view_name: str):
        if view_name in self.views:
            self.content_area.setCurrentWidget(self.views[view_name])
            if view_name in ("login", "lock"):
                self.sidebar.hide()
            else:
                self.sidebar.show()
                # Update sidebar button states
                for name, btn in self.nav_buttons.items():
                    btn.setChecked(name == view_name)
                    
            # Trigger view refresh if it has one
            if hasattr(self.views[view_name], "refresh"):
                self.views[view_name].refresh()

    def handle_login_success(self):
        self.navigate_to("dashboard")

    def handle_lock(self):
        # We don't clear the auth session, just lock the UI
        self.navigate_to("lock")

    def handle_logout(self):
        auth_service.logout()
        self.navigate_to("login")

def main():
    app = QApplication(sys.argv)
    
    # Load stylesheet
    try:
        stylesheet_path = Path(__file__).with_name("styles") / "main.qss"
        with stylesheet_path.open("r", encoding="utf-8") as f:
            app.setStyleSheet(f.read())
    except FileNotFoundError:
        pass
        
    init_db()
    
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
