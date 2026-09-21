from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QLineEdit, QPushButton, QFrame, QStackedWidget
)
from PySide6.QtCore import Qt
import os
import json

from src.services import auth_service
from src.core.config import SessionLocal, DB_PATH

class LoginView(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.setup_ui()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Login Card
        self.card = QFrame()
        self.card.setObjectName("card")
        self.card.setFixedSize(400, 500)
        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(40, 40, 40, 40)
        card_layout.setSpacing(20)

        # Title
        title = QLabel("ExPlan")
        title.setObjectName("brandLabel")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(title)

        subtitle = QLabel("Welcome back.\nYour financial story is waiting.")
        subtitle.setObjectName("subtitle")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(subtitle)
        
        card_layout.addSpacing(20)

        # Stack for Login / Register
        self.stack = QStackedWidget()
        card_layout.addWidget(self.stack)

        self.setup_login_page()
        self.setup_register_page()

        self.error_label = QLabel("")
        self.error_label.setStyleSheet("color: #E57373;")
        self.error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.error_label.hide()
        card_layout.addWidget(self.error_label)

        main_layout.addWidget(self.card)

    def setup_login_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0,0,0,0)

        self.login_ident = QLineEdit()
        self.login_ident.setPlaceholderText("Email or Username")
        
        # Pre-fill if exists
        self.config_path = os.path.join(os.path.dirname(DB_PATH), "config.json")
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r") as f:
                    conf = json.load(f)
                    if "last_username" in conf:
                        self.login_ident.setText(conf["last_username"])
            except:
                pass
                
        layout.addWidget(self.login_ident)

        self.login_pass = QLineEdit()
        self.login_pass.setPlaceholderText("Password")
        self.login_pass.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.login_pass)

        layout.addSpacing(10)

        btn = QPushButton("Sign In")
        btn.setObjectName("primaryButton")
        btn.clicked.connect(self.do_login)
        layout.addWidget(btn)

        switch_btn = QPushButton("Create an account")
        switch_btn.setObjectName("navButton")
        switch_btn.clicked.connect(lambda: self.stack.setCurrentIndex(1))
        layout.addWidget(switch_btn)

        self.stack.addWidget(page)

    def setup_register_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0,0,0,0)

        self.reg_user = QLineEdit()
        self.reg_user.setPlaceholderText("Username")
        layout.addWidget(self.reg_user)

        self.reg_email = QLineEdit()
        self.reg_email.setPlaceholderText("Email")
        layout.addWidget(self.reg_email)

        self.reg_pass = QLineEdit()
        self.reg_pass.setPlaceholderText("Password")
        self.reg_pass.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.reg_pass)

        layout.addSpacing(10)

        btn = QPushButton("Register")
        btn.setObjectName("primaryButton")
        btn.clicked.connect(self.do_register)
        layout.addWidget(btn)

        switch_btn = QPushButton("Back to Sign In")
        switch_btn.setObjectName("navButton")
        switch_btn.clicked.connect(lambda: self.stack.setCurrentIndex(0))
        layout.addWidget(switch_btn)

        self.stack.addWidget(page)

    def do_login(self):
        ident = self.login_ident.text().strip()
        pwd = self.login_pass.text()
        
        if not ident or not pwd:
            self.show_error("Please enter credentials.")
            return

        db = SessionLocal()
        try:
            success, msg = auth_service.login(db, ident, pwd)
            if success:
                self.error_label.hide()
                
                # Save to config
                try:
                    conf = {}
                    if os.path.exists(self.config_path):
                        with open(self.config_path, "r") as f:
                            conf = json.load(f)
                    conf["last_username"] = ident
                    with open(self.config_path, "w") as f:
                        json.dump(conf, f)
                except:
                    pass
                
                self.main_window.handle_login_success()
                # Clear password field only
                self.login_pass.clear()
            else:
                self.show_error(msg)
        except Exception as e:
            self.show_error(f"Error: {str(e)}")
        finally:
            db.close()

    def do_register(self):
        user = self.reg_user.text().strip()
        email = self.reg_email.text().strip()
        pwd = self.reg_pass.text()

        if not user or not email or not pwd:
            self.show_error("Please fill all fields.")
            return

        db = SessionLocal()
        try:
            success, msg = auth_service.register(db, user, email, pwd)
            if success:
                self.show_error("Registration successful. Please login.", color="#81C784")
                self.stack.setCurrentIndex(0)
                self.reg_user.clear()
                self.reg_email.clear()
                self.reg_pass.clear()
            else:
                self.show_error(msg)
        except Exception as e:
            self.show_error(f"Error: {str(e)}")
        finally:
            db.close()

    def show_error(self, msg: str, color: str = "#E57373"):
        self.error_label.setText(msg)
        self.error_label.setStyleSheet(f"color: {color};")
        self.error_label.show()
