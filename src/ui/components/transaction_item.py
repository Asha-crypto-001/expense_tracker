from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel, QFrame
from PySide6.QtCore import Qt

class TransactionItem(QFrame):
    def __init__(self, amount: int, type: str, category_name: str, time_str: str, desc: str):
        super().__init__()
        self.setObjectName("card")
        self.setMinimumHeight(80)
        
        layout = QHBoxLayout(self)
        
        # Left side - Time and Category
        left_layout = QVBoxLayout()
        time_label = QLabel(time_str)
        time_label.setObjectName("subtitle")
        
        cat_label = QLabel(category_name)
        cat_label.setStyleSheet("font-weight: bold;")
        cat_label.setWordWrap(True)
        
        left_layout.addWidget(time_label)
        left_layout.addWidget(cat_label)
        
        # Center - Description
        desc_label = QLabel(desc)
        desc_label.setWordWrap(True)
        
        # Right - Amount
        amount_label = QLabel(f"UGX {amount:,.0f}")
        amount_label.setObjectName("h2")
        if type == "expense":
            amount_label.setStyleSheet("color: #E2DFD8;") # neutral for expense
            amount_label.setText(f"UGX {amount:,.0f}")
        elif type == "income":
            amount_label.setStyleSheet("color: #81C784;")
            amount_label.setText(f"+UGX {amount:,.0f}")
        else: # transfer
            amount_label.setStyleSheet("color: #64B5F6;")
            amount_label.setText(f"↔ UGX {amount:,.0f}")
            
        amount_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        amount_label.setWordWrap(True)
        
        layout.addLayout(left_layout, 1)
        layout.addWidget(desc_label, 2)
        layout.addWidget(amount_label, 1)
