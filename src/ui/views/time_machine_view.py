from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QFrame, QPushButton
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from datetime import datetime, date
import calendar
from src.services import auth_service
from src.services import TransactionService
from src.core.config import SessionLocal

class TimeMachineView(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.transaction_service = TransactionService()
        self.setup_ui()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(60, 60, 60, 60)
        
        # Nostalgic Title
        title = QLabel("The Financial Time Machine")
        title.setFont(QFont("Canva Sans", 28, QFont.Weight.Bold))
        title.setStyleSheet("color: #D4AF37;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title)
        
        subtitle = QLabel("Look back through your financial photographs.")
        subtitle.setObjectName("subtitle")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(subtitle)
        
        main_layout.addSpacing(40)
        
        # Controls
        controls_layout = QHBoxLayout()
        controls_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.month_combo = QComboBox()
        for i in range(1, 13):
            self.month_combo.addItem(calendar.month_name[i], i)
            
        self.year_combo = QComboBox()
        current_year = datetime.now().year
        for y in range(current_year - 5, current_year + 1):
            self.year_combo.addItem(str(y), y)
            
        self.month_combo.setCurrentIndex(datetime.now().month - 1)
        self.year_combo.setCurrentText(str(current_year))
        
        btn = QPushButton("Travel")
        btn.setObjectName("primaryButton")
        btn.clicked.connect(self.travel)
        
        controls_layout.addWidget(self.month_combo)
        controls_layout.addWidget(self.year_combo)
        controls_layout.addWidget(btn)
        
        main_layout.addLayout(controls_layout)
        main_layout.addSpacing(40)
        
        # Result Card
        self.result_card = QFrame()
        self.result_card.setObjectName("card")
        self.result_card.setStyleSheet("""
            QFrame#card {
                background-color: #1A1A18;
                border: 1px solid #33332E;
                border-radius: 4px;
            }
        """)
        
        result_layout = QHBoxLayout(self.result_card)
        result_layout.setContentsMargins(40, 40, 40, 40)
        
        # Left side - THEN
        self.then_layout = QVBoxLayout()
        self.then_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        # Right side - NOW
        self.now_layout = QVBoxLayout()
        self.now_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        result_layout.addLayout(self.then_layout)
        result_layout.addSpacing(20)
        
        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setStyleSheet("color: #33332E;")
        result_layout.addWidget(sep)
        
        result_layout.addSpacing(20)
        result_layout.addLayout(self.now_layout)
        
        main_layout.addWidget(self.result_card)
        main_layout.addStretch()
        
        self.result_card.hide()

    def travel(self):
        user = auth_service.get_current_user()
        if not user: return
        
        m = self.month_combo.currentData()
        y = self.year_combo.currentData()
        
        now_m = datetime.now().month
        now_y = datetime.now().year
        
        db = SessionLocal()
        try:
            then_stats = self.get_stats(db, user.id, m, y)
            now_stats = self.get_stats(db, user.id, now_m, now_y)
            
            self.display_stats(then_stats, now_stats, m, y)
            self.result_card.show()
        finally:
            db.close()
            
    def get_stats(self, db, user_id, month, year):
        start = date(year, month, 1)
        end = date(year, month, calendar.monthrange(year, month)[1])
        summary = self.transaction_service.get_period_summary(db, user_id, start, end)
        return {
            "income": summary["income"],
            "expense": summary["expense"],
            "savings": summary["savings"],
            "top_category": summary["categories"][0][0] if summary["categories"] else "None",
        }
        
    def display_stats(self, then_stats, now_stats, m, y):
        # Clear layouts
        for layout in [self.then_layout, self.now_layout]:
            while layout.count():
                item = layout.takeAt(0)
                if item.widget(): item.widget().deleteLater()
                
        # Fill THEN
        month_name = calendar.month_name[m].upper()
        t1 = QLabel(f"WHERE YOU WERE ({month_name} {y})")
        t1.setObjectName("journalDate")
        self.then_layout.addWidget(t1)
        self.then_layout.addSpacing(20)
        
        self.add_stat_row(self.then_layout, "Income", f"UGX {then_stats['income']:,.0f}")
        self.add_stat_row(self.then_layout, "Expenses", f"UGX {then_stats['expense']:,.0f}")
        self.add_stat_row(self.then_layout, "Savings", f"UGX {then_stats['savings']:,.0f}")
        self.add_stat_row(self.then_layout, "Top Category", then_stats['top_category'])
        
        # Fill NOW
        t2 = QLabel("THEN → NOW")
        t2.setObjectName("journalDate")
        self.now_layout.addWidget(t2)
        self.now_layout.addSpacing(20)
        
        self.add_stat_row(self.now_layout, "Income", f"{self.format_k(then_stats['income'])} → {self.format_k(now_stats['income'])}")
        self.add_stat_row(self.now_layout, "Expenses", f"{self.format_k(then_stats['expense'])} → {self.format_k(now_stats['expense'])}")
        self.add_stat_row(self.now_layout, "Savings", f"{self.format_k(then_stats['savings'])} → {self.format_k(now_stats['savings'])}")
        
    def add_stat_row(self, layout, label_text, value_text):
        lbl = QLabel(label_text)
        lbl.setObjectName("subtitle")
        val = QLabel(value_text)
        val.setObjectName("h2")
        layout.addWidget(lbl)
        layout.addWidget(val)
        layout.addSpacing(10)
        
    def format_k(self, amount):
        if amount >= 1000000:
            return f"{amount/1000000:.1f}M"
        elif amount >= 1000:
            return f"{amount/1000:.0f}K"
        return str(amount)
