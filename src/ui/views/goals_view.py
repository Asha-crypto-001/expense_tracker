from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QScrollArea,
    QFrame, QGridLayout, QProgressBar, QDialog, QLineEdit, QSpinBox, QDateEdit, QSizePolicy
)
from PySide6.QtCore import Qt, QDate
from src.services import auth_service, GoalService
from src.core.config import SessionLocal
from sqlalchemy.exc import SQLAlchemyError

class AddGoalDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("New Savings Goal")
        self.setFixedSize(420, 260)
        self.goal_service = GoalService()
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Goal name")
        layout.addWidget(QLabel("Name:"))
        layout.addWidget(self.name_input)

        self.target_input = QSpinBox()
        self.target_input.setRange(1, 1000000000)
        self.target_input.setSingleStep(1000)
        layout.addWidget(QLabel("Target amount (UGX):"))
        layout.addWidget(self.target_input)

        self.deadline_edit = QDateEdit(QDate.currentDate().addMonths(3))
        self.deadline_edit.setCalendarPopup(True)
        layout.addWidget(QLabel("Deadline:"))
        layout.addWidget(self.deadline_edit)

        save_btn = QPushButton("Save")
        save_btn.setObjectName("primaryButton")
        save_btn.clicked.connect(self.on_save)
        layout.addWidget(save_btn)
        self.error_label = QLabel("")
        self.error_label.setStyleSheet("color: #E57373;")
        self.error_label.setWordWrap(True)
        layout.addWidget(self.error_label)

    def on_save(self):
        user = auth_service.get_current_user()
        if not user:
            return

        name = self.name_input.text().strip()
        target = self.target_input.value()
        deadline = self.deadline_edit.date().toPython()

        if not name:
            self.error_label.setText("Goal name is required.")
            return

        db = SessionLocal()
        try:
            self.goal_service.create_goal(db, user.id, name, target, deadline)
            self.accept()
        except (ValueError, SQLAlchemyError) as e:
            self.error_label.setText(str(e))
        finally:
            db.close()


class GoalTransactionDialog(QDialog):
    def __init__(self, goal_id: int, action: str, parent=None):
        super().__init__(parent)
        self.goal_id = goal_id
        self.action = action
        self.goal_service = GoalService()
        self.setWindowTitle(f"{action.title()} Goal")
        self.setFixedSize(360, 180)
        layout = QVBoxLayout(self)
        self.amount_input = QSpinBox()
        self.amount_input.setRange(1, 1_000_000_000)
        self.amount_input.setSingleStep(1000)
        layout.addWidget(QLabel(f"{action.title()} amount (UGX):"))
        layout.addWidget(self.amount_input)
        self.error_label = QLabel("")
        self.error_label.setStyleSheet("color: #E57373;")
        layout.addWidget(self.error_label)
        save_btn = QPushButton(action.title())
        save_btn.setObjectName("primaryButton")
        save_btn.clicked.connect(self.on_save)
        layout.addWidget(save_btn)

    def on_save(self):
        user = auth_service.get_current_user()
        if not user:
            self.error_label.setText("Please sign in first.")
            return
        db = SessionLocal()
        try:
            if self.action == "contribution":
                self.goal_service.add_contribution(
                    db, user.id, self.goal_id, self.amount_input.value()
                )
            else:
                self.goal_service.withdraw(
                    db, user.id, self.goal_id, self.amount_input.value()
                )
            self.accept()
        except (ValueError, SQLAlchemyError) as exc:
            self.error_label.setText(str(exc))
        finally:
            db.close()

class GoalCard(QFrame):
    def __init__(self, goal, action_callback):
        super().__init__()
        self.setObjectName("card")
        self.setMinimumWidth(220)
        self.setMaximumWidth(420)
        self.setFixedHeight(210)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        
        layout = QVBoxLayout(self)
        
        t_label = QLabel(goal.name)
        t_label.setObjectName("h2")
        t_label.setWordWrap(True)
        layout.addWidget(t_label)
        
        layout.addStretch()
        
        stats = QLabel(f"Saved: UGX {goal.current_amount:,.0f} / UGX {goal.target_amount:,.0f}")
        stats.setObjectName("subtitle")
        layout.addWidget(stats)
        
        progress = QProgressBar()
        progress.setMaximum(goal.target_amount)
        progress.setValue(min(goal.current_amount, goal.target_amount))
        progress.setStyleSheet("QProgressBar::chunk { background-color: #4DB6AC; }")
            
        layout.addWidget(progress)
        actions = QHBoxLayout()
        contribute = QPushButton("Contribute")
        withdraw = QPushButton("Withdraw")
        contribute.clicked.connect(
            lambda: action_callback(goal.id, "contribution")
        )
        withdraw.clicked.connect(
            lambda: action_callback(goal.id, "withdrawal")
        )
        actions.addWidget(contribute)
        actions.addWidget(withdraw)
        layout.addLayout(actions)

class GoalsView(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.goal_service = GoalService()
        self.cards = []
        self.setup_ui()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(40, 40, 40, 40)
        
        header = QHBoxLayout()
        title = QLabel("Savings Goals")
        title.setObjectName("h1")
        header.addWidget(title)
        header.addStretch()
        
        btn = QPushButton("New Goal")
        btn.setObjectName("primaryButton")
        btn.clicked.connect(self.show_add_goal_dialog)
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

    def show_add_goal_dialog(self):
        dialog = AddGoalDialog(self)
        if dialog.exec():
            self.refresh()

    def show_goal_transaction_dialog(self, goal_id: int, action: str):
        dialog = GoalTransactionDialog(goal_id, action, self)
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
            goals = self.goal_service.get_goals(db, user.id)
            if not goals:
                empty = QLabel("No savings goals set.")
                empty.setObjectName("subtitle")
                self.grid.addWidget(empty, 0, 0)
                return

            for g in goals:
                card = GoalCard(g, self.show_goal_transaction_dialog)
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
