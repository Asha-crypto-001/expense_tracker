from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QComboBox, QPushButton, QDateEdit, QTimeEdit, QSpinBox
)
from PySide6.QtCore import Qt, QDate, QTime
from datetime import datetime
from sqlalchemy.exc import SQLAlchemyError

from src.services import auth_service, TransactionService, AccountService
from src.core.config import SessionLocal
from src.models import Account, Category

class AddTransactionDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("New Transaction")
        self.setFixedSize(400, 500)
        
        self.tx_service = TransactionService()
        self.account_service = AccountService()
        
        self.setup_ui()
        self.load_data()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        title = QLabel("Record a transaction")
        title.setObjectName("h2")
        layout.addWidget(title)
        
        # Type
        self.type_combo = QComboBox()
        self.type_combo.addItems(["Expense", "Income", "Transfer"])
        self.type_combo.currentTextChanged.connect(self.on_type_changed)
        layout.addWidget(self.type_combo)
        
        # Amount
        amt_layout = QHBoxLayout()
        amt_label = QLabel("Amount (UGX):")
        self.amount_input = QSpinBox()
        self.amount_input.setRange(0, 1000000000)
        self.amount_input.setSingleStep(1000)
        amt_layout.addWidget(amt_label)
        amt_layout.addWidget(self.amount_input)
        layout.addLayout(amt_layout)
        
        # Account
        self.account_combo = QComboBox()
        layout.addWidget(QLabel("Account:"))
        layout.addWidget(self.account_combo)
        
        # Target Account (for transfers)
        self.to_account_label = QLabel("To Account:")
        self.to_account_combo = QComboBox()
        layout.addWidget(self.to_account_label)
        layout.addWidget(self.to_account_combo)
        self.to_account_label.hide()
        self.to_account_combo.hide()
        
        # Category
        self.category_label = QLabel("Category:")
        self.category_combo = QComboBox()
        layout.addWidget(self.category_label)
        layout.addWidget(self.category_combo)
        
        # Date & Time
        dt_layout = QHBoxLayout()
        self.date_input = QDateEdit(QDate.currentDate())
        self.date_input.setCalendarPopup(True)
        self.time_input = QTimeEdit(QTime.currentTime())
        dt_layout.addWidget(self.date_input)
        dt_layout.addWidget(self.time_input)
        layout.addLayout(dt_layout)
        
        # Description
        self.desc_input = QLineEdit()
        self.desc_input.setPlaceholderText("Description")
        layout.addWidget(self.desc_input)
        
        layout.addStretch()
        
        # Buttons
        btn_layout = QHBoxLayout()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("secondaryButton")
        cancel_btn.clicked.connect(self.reject)
        
        save_btn = QPushButton("Save")
        save_btn.setObjectName("primaryButton")
        save_btn.clicked.connect(self.on_save)
        self.save_btn = save_btn
        
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(save_btn)
        
        layout.addLayout(btn_layout)
        self.error_label = QLabel("")
        self.error_label.setStyleSheet("color: #E57373;")
        self.error_label.setWordWrap(True)
        layout.addWidget(self.error_label)

    def load_data(self):
        user = auth_service.get_current_user()
        if not user:
            self.save_btn.setEnabled(False)
            self.error_label.setText("Please sign in before recording a transaction.")
            return
        db = SessionLocal()
        try:
            self.accounts = self.account_service.get_accounts(db, user.id)
            for acc in self.accounts:
                self.account_combo.addItem(acc.name, acc.id)
                self.to_account_combo.addItem(acc.name, acc.id)
                
            # Categories (hardcoded defaults for now, usually load from DB)
            self.categories = db.query(Category).filter(Category.user_id == user.id).all()
            for cat in self.categories:
                self.category_combo.addItem(cat.name, cat.id)
                
            if not self.categories:
                # Add a dummy or ask user to create categories
                pass
        finally:
            db.close()

    def on_type_changed(self, text):
        is_transfer = text == "Transfer"
        self.to_account_label.setVisible(is_transfer)
        self.to_account_combo.setVisible(is_transfer)
        self.category_label.setVisible(not is_transfer)
        self.category_combo.setVisible(not is_transfer)

    def on_save(self):
        user = auth_service.get_current_user()
        if not user:
            self.error_label.setText("Your session has expired. Please sign in again.")
            return
        tx_type = self.type_combo.currentText().lower()
        amount = self.amount_input.value()
        
        acc_id = self.account_combo.currentData()
        to_acc_id = self.to_account_combo.currentData() if tx_type == "transfer" else None
        cat_id = self.category_combo.currentData() if tx_type != "transfer" else None
        
        d = self.date_input.date().toPython()
        t = self.time_input.time().toPython()
        desc = self.desc_input.text()
        
        if amount <= 0:
            self.error_label.setText("Amount must be greater than zero.")
            return
        if acc_id is None:
            self.error_label.setText("Select an account.")
            return
        if tx_type != "transfer" and cat_id is None:
            self.error_label.setText("Select a category.")
            return
        if tx_type == "transfer" and to_acc_id is None:
            self.error_label.setText("Select a target account.")
            return

        db = SessionLocal()
        try:
            self.tx_service.create_transaction(
                db, user.id, acc_id, amount, tx_type, d, t, desc, cat_id, to_acc_id
            )
            self.accept()
        except (ValueError, SQLAlchemyError) as e:
            self.error_label.setText(str(e))
        finally:
            db.close()
