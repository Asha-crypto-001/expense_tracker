from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QScrollArea, QFrame,
    QGridLayout, QDialog, QLineEdit, QComboBox, QSpinBox, QSizePolicy
)
from PySide6.QtCore import Qt

from src.services import auth_service, AccountService
from src.core.config import SessionLocal
from sqlalchemy.exc import SQLAlchemyError


class AddAccountDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("New Account")
        self.setFixedSize(400, 300)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Account name")
        layout.addWidget(QLabel("Name:"))
        layout.addWidget(self.name_input)

        self.type_combo = QComboBox()
        self.type_combo.addItems(["Cash", "Bank", "Mobile Money", "Savings", "Other"])
        layout.addWidget(QLabel("Type:"))
        layout.addWidget(self.type_combo)

        self.currency_input = QLineEdit("UGX")
        self.currency_input.setMaxLength(3)
        layout.addWidget(QLabel("Currency:"))
        layout.addWidget(self.currency_input)

        self.balance_input = QSpinBox()
        self.balance_input.setRange(0, 1_000_000_000)
        self.balance_input.setSingleStep(1000)
        layout.addWidget(QLabel("Opening balance:"))
        layout.addWidget(self.balance_input)

        self.error_label = QLabel("")
        self.error_label.setStyleSheet("color: #E57373;")
        layout.addWidget(self.error_label)

        save_btn = QPushButton("Save")
        save_btn.setObjectName("primaryButton")
        save_btn.clicked.connect(self.on_save)
        layout.addWidget(save_btn)

    def on_save(self):
        user = auth_service.get_current_user()
        name = self.name_input.text().strip()
        currency = self.currency_input.text().strip().upper()
        if not user:
            self.error_label.setText("Please sign in first.")
            return
        if not name:
            self.error_label.setText("Account name is required.")
            return
        if len(currency) != 3 or not currency.isalpha():
            self.error_label.setText("Currency must be a three-letter code.")
            return
        db = SessionLocal()
        try:
            AccountService().create_account(
                db, user.id, name, self.type_combo.currentText(),
                self.balance_input.value(), currency
            )
            self.accept()
        except (ValueError, SQLAlchemyError) as e:
            self.error_label.setText(str(e))
        finally:
            db.close()

class AccountCard(QFrame):
    def __init__(self, name: str, balance: int, acc_type: str):
        super().__init__()
        self.setObjectName("card")
        self.setMinimumWidth(220)
        self.setMaximumWidth(420)
        self.setFixedHeight(150)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        
        layout = QVBoxLayout(self)
        
        type_label = QLabel(acc_type.upper())
        type_label.setObjectName("subtitle")
        layout.addWidget(type_label)
        
        name_label = QLabel(name)
        name_label.setObjectName("h2")
        name_label.setWordWrap(True)
        layout.addWidget(name_label)
        
        layout.addStretch()
        
        bal_label = QLabel(f"UGX {balance:,.0f}")
        bal_label.setObjectName("h1")
        bal_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        layout.addWidget(bal_label)

class AccountsView(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.account_service = AccountService()
        self.cards = []
        self.setup_ui()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(40, 40, 40, 40)
        
        header_layout = QHBoxLayout()
        title = QLabel("Accounts")
        title.setObjectName("h1")
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        self.add_btn = QPushButton("New Account")
        self.add_btn.setObjectName("primaryButton")
        self.add_btn.clicked.connect(self.show_add_dialog)
        header_layout.addWidget(self.add_btn)
        
        main_layout.addLayout(header_layout)
        main_layout.addSpacing(30)
        
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setStyleSheet("background-color: transparent;")
        
        self.content = QWidget()
        self.content.setStyleSheet("background-color: transparent;")
        self.grid = QGridLayout(self.content)
        self.grid.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.grid.setHorizontalSpacing(14)
        self.grid.setVerticalSpacing(14)
        
        self.scroll.setWidget(self.content)
        main_layout.addWidget(self.scroll)

    def show_add_dialog(self):
        dialog = AddAccountDialog(self)
        if dialog.exec():
            self.refresh()

    def refresh(self):
        user = auth_service.get_current_user()
        if not user:
            return
            
        # clear grid
        while self.grid.count():
            item = self.grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.cards = []
                
        db = SessionLocal()
        try:
            accounts = self.account_service.get_accounts(db, user.id)
            for acc in accounts:
                card = AccountCard(acc.name, acc.current_balance, acc.account_type)
                self.cards.append(card)
            self._layout_cards()
        finally:
            db.close()

    def _layout_cards(self):
        while self.grid.count():
            self.grid.takeAt(0)
        columns = 3 if self.scroll.viewport().width() >= 1040 else 2 if self.scroll.viewport().width() >= 680 else 1
        for index, card in enumerate(self.cards):
            self.grid.addWidget(card, index // columns, index % columns)
        for column in range(columns):
            self.grid.setColumnStretch(column, 1)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "scroll"):
            self._layout_cards()
