from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QScrollArea, QFrame, QLineEdit, QComboBox
)
from PySide6.QtCore import Qt
from datetime import date
from collections import defaultdict
import string

from src.services import auth_service, TransactionService
from src.core.config import SessionLocal
from src.models import Category
from src.ui.components.transaction_item import TransactionItem

class TransactionsView(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.tx_service = TransactionService()
        self.setup_ui()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(40, 40, 40, 40)
        
        # Header
        header_layout = QHBoxLayout()
        
        title = QLabel("Transaction History")
        title.setObjectName("h1")
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        self.add_btn = QPushButton("Add Transaction")
        self.add_btn.setObjectName("primaryButton")
        self.add_btn.clicked.connect(self.show_add_dialog)
        header_layout.addWidget(self.add_btn)
        
        main_layout.addLayout(header_layout)
        
        # Filters (Search, Category)
        filters_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search transactions...")
        self.search_input.textChanged.connect(self.refresh)
        filters_layout.addWidget(self.search_input)
        
        self.cat_filter = QComboBox()
        self.cat_filter.addItem("All Categories")
        self.cat_filter.currentIndexChanged.connect(self.refresh)
        filters_layout.addWidget(self.cat_filter)
        
        main_layout.addLayout(filters_layout)
        main_layout.addSpacing(20)
        
        # Scroll Area
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setStyleSheet("background-color: transparent;")
        
        self.content = QWidget()
        self.content.setStyleSheet("background-color: transparent;")
        self.timeline_layout = QVBoxLayout(self.content)
        self.timeline_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        self.scroll.setWidget(self.content)
        main_layout.addWidget(self.scroll)

    def refresh(self):
        user = auth_service.get_current_user()
        if not user:
            return
            
        # clear timeline
        while self.timeline_layout.count():
            item = self.timeline_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
                
        db = SessionLocal()
        try:
            current_category = self.cat_filter.currentData()
            self.cat_filter.blockSignals(True)
            self.cat_filter.clear()
            self.cat_filter.addItem("All Categories", None)
            for category in db.query(Category).filter(
                Category.user_id == user.id,
                Category.is_archived == False,
            ).order_by(Category.name).all():
                self.cat_filter.addItem(category.name, category.id)
            if current_category is not None:
                index = self.cat_filter.findData(current_category)
                if index >= 0:
                    self.cat_filter.setCurrentIndex(index)
            self.cat_filter.blockSignals(False)

            transactions = self.tx_service.get_recent(db, user.id, limit=100)
            search = self.search_input.text().strip().lower()
            selected_category = self.cat_filter.currentData()
            if search:
                transactions = [
                    tx for tx in transactions
                    if search in tx.description.lower()
                    or (tx.category and search in tx.category.name.lower())
                ]
            if selected_category is not None:
                transactions = [
                    tx for tx in transactions if tx.category_id == selected_category
                ]
            
            if not transactions:
                empty = QLabel("Your financial journal is still quiet.\nAdd your first transaction and begin building your history.")
                empty.setObjectName("subtitle")
                empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
                self.timeline_layout.addWidget(empty)
                return
                
            # Group by date
            grouped = defaultdict(list)
            for tx in transactions:
                grouped[tx.date].append(tx)
                
            # Display sorted by date desc
            for tx_date in sorted(grouped.keys(), reverse=True):
                # Date Header
                date_str = tx_date.strftime("%A · %d %B %Y").upper()
                if tx_date == date.today():
                    date_str = "TODAY · " + date_str
                    
                date_label = QLabel(date_str)
                date_label.setObjectName("journalDate")
                date_label.setContentsMargins(0, 20, 0, 10)
                self.timeline_layout.addWidget(date_label)
                
                # Items
                for tx in grouped[tx_date]:
                    cat_name = tx.category.name if tx.category else "Uncategorized"
                    if tx.type == "transfer":
                        cat_name = "Transfer"
                        
                    item = TransactionItem(
                        amount=tx.amount,
                        type=tx.type,
                        category_name=cat_name,
                        time_str=tx.time.strftime("%H:%M"),
                        desc=tx.description
                    )
                    self.timeline_layout.addWidget(item)
                    
        finally:
            db.close()

    def show_add_dialog(self):
        from src.ui.dialogs.add_transaction_dialog import AddTransactionDialog
        dialog = AddTransactionDialog(self)
        if dialog.exec():
            self.refresh()
            # Also refresh dashboard if possible
            if hasattr(self.main_window, 'navigate_to'):
                # just updating state, but we are on transactions view
                pass
