from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Qt
import matplotlib
matplotlib.use('QtAgg')
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from src.services import auth_service
from src.core.config import SessionLocal
from src.models import Transaction, Category
from sqlalchemy import func, extract
from datetime import date

class AnalyticsView(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.setup_ui()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(40, 40, 40, 40)
        
        title = QLabel("Analytics")
        title.setObjectName("h1")
        main_layout.addWidget(title)
        
        self.subtitle = QLabel("Spending by Category (This Month)")
        self.subtitle.setObjectName("subtitle")
        main_layout.addWidget(self.subtitle)
        
        self.figure = Figure(facecolor="#1A1A18")
        self.canvas = FigureCanvas(self.figure)
        main_layout.addWidget(self.canvas)
        
    def refresh(self):
        user = auth_service.get_current_user()
        if not user: return
        
        db = SessionLocal()
        try:
            today = date.today()
            results = db.query(Category.name, func.sum(Transaction.amount)) \
                .join(Transaction, Transaction.category_id == Category.id) \
                .filter(
                    Transaction.user_id == user.id,
                    Transaction.type == "expense",
                    extract('month', Transaction.date) == today.month,
                    extract('year', Transaction.date) == today.year
                ).group_by(Category.name).all()
                
            self.figure.clear()
            ax = self.figure.add_subplot(111)
            ax.set_facecolor("#1A1A18")
            
            if not results:
                ax.text(0.5, 0.5, "No expense data for this month.", 
                        color="#E2DFD8", ha="center", va="center")
                ax.axis('off')
            else:
                labels = [r[0] for r in results]
                sizes = [r[1] for r in results]
                
                # Dark mode pie chart
                wedges, texts, autotexts = ax.pie(
                    sizes, labels=labels, autopct='%1.1f%%', startangle=90,
                    textprops=dict(color="#E2DFD8")
                )
                
                # Style wedges with subtle borders
                for w in wedges:
                    w.set_edgecolor('#1A1A18')
                    w.set_linewidth(1.5)
                    
            self.canvas.draw()
            
        finally:
            db.close()
