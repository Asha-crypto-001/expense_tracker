from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QScrollArea, QFrame,
    QGridLayout, QProgressBar, QDialog, QComboBox, QSpinBox, QLineEdit, QSizePolicy
)
from PySide6.QtCore import Qt
from src.services import auth_service, BudgetService
from src.core.config import SessionLocal
from src.models import Category
from sqlalchemy.exc import SQLAlchemyError

class AddBudgetDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("New Budget")
        self.setFixedSize(420, 260)
        self.budget_service = BudgetService()
        self.setup_ui()
        self.load_categories()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        self.category_combo = QComboBox()
        self.category_combo.addItem("Overall spending", None)
        layout.addWidget(QLabel("Category:"))
        layout.addWidget(self.category_combo)

        self.period_combo = QComboBox()
        self.period_combo.addItems(["monthly", "yearly"])
        layout.addWidget(QLabel("Period:"))
        layout.addWidget(self.period_combo)

        self.amount_input = QSpinBox()
        self.amount_input.setRange(1, 1000000000)
        self.amount_input.setSingleStep(1000)
        layout.addWidget(QLabel("Amount (UGX):"))
        layout.addWidget(self.amount_input)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Optional label")
        layout.addWidget(QLabel("Label:"))
        layout.addWidget(self.name_input)

        save_btn = QPushButton("Save")
        save_btn.setObjectName("primaryButton")
        save_btn.clicked.connect(self.on_save)
        layout.addWidget(save_btn)
        self.error_label = QLabel("")
        self.error_label.setStyleSheet("color: #E57373;")
        self.error_label.setWordWrap(True)
        layout.addWidget(self.error_label)

    def load_categories(self):
        user = auth_service.get_current_user()
        if not user:
            return
        db = SessionLocal()
        try:
            for category in db.query(Category).filter(Category.user_id == user.id, Category.type == "expense").all():
                self.category_combo.addItem(category.name, category.id)
        finally:
            db.close()

    def on_save(self):
        user = auth_service.get_current_user()
        if not user:
            return

        category_id = self.category_combo.currentData()
        amount = self.amount_input.value()
        period = self.period_combo.currentText()
        label = self.name_input.text().strip()

        db = SessionLocal()
        try:
            self.budget_service.create_budget(db, user.id, amount, period, category_id)
            self.accept()
        except (ValueError, SQLAlchemyError) as e:
            self.error_label.setText(str(e))
        finally:
            db.close()

class BudgetCard(QFrame):
    def __init__(self, title: str, spent: int, total: int):
        super().__init__()
        self.setObjectName("card")
        self.setMinimumWidth(220)
        self.setMaximumWidth(420)
        self.setFixedHeight(200)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        
        layout = QVBoxLayout(self)
        
        t_label = QLabel(title)
        t_label.setObjectName("h2")
        t_label.setWordWrap(True)
        layout.addWidget(t_label)
        
        layout.addStretch()
        
        stats = QLabel(f"Spent: UGX {spent:,.0f} / UGX {total:,.0f}")
        stats.setObjectName("subtitle")
        layout.addWidget(stats)
        
        progress = QProgressBar()
        progress.setMaximum(total)
        progress.setValue(min(spent, total))
        if spent > total:
            progress.setStyleSheet("QProgressBar::chunk { background-color: #E57373; }")
        elif spent > total * 0.8:
            progress.setStyleSheet("QProgressBar::chunk { background-color: #FFB74D; }")
        else:
            progress.setStyleSheet("QProgressBar::chunk { background-color: #81C784; }")
            
        layout.addWidget(progress)

class BudgetsView(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.budget_service = BudgetService()
        self.cards = []
        self.setup_ui()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(40, 40, 40, 40)
        
        header = QHBoxLayout()
        title = QLabel("Budgets")
        title.setObjectName("h1")
        header.addWidget(title)
        header.addStretch()
        
        btn = QPushButton("New Budget")
        btn.setObjectName("primaryButton")
        btn.clicked.connect(self.show_add_budget_dialog)
        header.addWidget(btn)
        
        main_layout.addLayout(header)
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

    def show_add_budget_dialog(self):
        dialog = AddBudgetDialog(self)
        if dialog.exec():
            self.refresh()

    def refresh(self):
        user = auth_service.get_current_user()
        if not user: return

        while self.grid.count():
            item = self.grid.takeAt(0)
            if item.widget(): item.widget().deleteLater()
        self.cards = []

        db = SessionLocal()
        try:
            budgets = self.budget_service.get_budgets(db, user.id)
            if not budgets:
                empty = QLabel("No budgets set.")
                empty.setObjectName("subtitle")
                self.grid.addWidget(empty, 0, 0)
                return

            for b in budgets:
                usage = self.budget_service.get_budget_usage(db, b)
                name = b.category.name if b.category else "Overall Spending"
                card = BudgetCard(name, usage, b.amount)
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
