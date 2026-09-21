from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QLineEdit, QPushButton, QFrame
)
from PySide6.QtCore import Qt

from src.services import auth_service
from src.core.config import SessionLocal

class LockView(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.setup_ui()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Lock Card
        self.card = QFrame()
        self.card.setObjectName("card")
        self.card.setFixedSize(400, 450)
        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(40, 40, 40, 40)
        card_layout.setSpacing(20)

        # Title
        title = QLabel("ExPlan")
        title.setObjectName("brandLabel")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(title)

        self.subtitle = QLabel("Application Locked.")
        self.subtitle.setObjectName("subtitle")
        self.subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(self.subtitle)
        
        card_layout.addSpacing(20)

        self.login_pass = QLineEdit()
        self.login_pass.setPlaceholderText("Password")
        self.login_pass.setEchoMode(QLineEdit.EchoMode.Password)
        self.login_pass.returnPressed.connect(self.do_unlock)
        card_layout.addWidget(self.login_pass)

        layout_btns = QVBoxLayout()
        btn = QPushButton("Unlock")
        btn.setObjectName("primaryButton")
        btn.clicked.connect(self.do_unlock)
        layout_btns.addWidget(btn)

        switch_btn = QPushButton("Sign Out Completely")
        switch_btn.setObjectName("navButton")
        switch_btn.clicked.connect(self.do_logout)
        layout_btns.addWidget(switch_btn)
        
        card_layout.addLayout(layout_btns)

        self.error_label = QLabel("")
        self.error_label.setStyleSheet("color: #E57373;")
        self.error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.error_label.hide()
        card_layout.addWidget(self.error_label)

        main_layout.addWidget(self.card)

    def refresh(self):
        self.login_pass.clear()
        self.error_label.hide()
        user = auth_service.get_current_user()
        if user:
            self.subtitle.setText(f"Locked.\nWelcome back, {user.username}.")
        else:
            # Not logged in, shouldn't be here
            self.main_window.navigate_to("login")

    def do_unlock(self):
        pwd = self.login_pass.text()
        if not pwd:
            self.show_error("Please enter password.")
            return

        user = auth_service.get_current_user()
        if not user:
            self.main_window.navigate_to("login")
            return

        db = SessionLocal()
        try:
            # verify without logging out
            success, msg = auth_service.login(db, user.username, pwd)
            if success:
                self.error_label.hide()
                self.login_pass.clear()
                self.main_window.navigate_to("dashboard")
            else:
                self.show_error("Incorrect password.")
        except Exception as e:
            self.show_error(f"Error: {str(e)}")
        finally:
            db.close()

    def do_logout(self):
        self.main_window.handle_logout()

    def show_error(self, msg: str):
        self.error_label.setText(msg)
        self.error_label.show()
