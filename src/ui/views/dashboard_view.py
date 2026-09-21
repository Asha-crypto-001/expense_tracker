from datetime import date, datetime

from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QProgressBar,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
    QToolTip,
)

from src.core.config import SessionLocal, load_preferences, save_preferences
from src.services import AccountService, BudgetService, GoalService, TransactionService, auth_service


def money(value: float) -> str:
    return f"UGX {value:,.0f}"


def comparison(current: float, previous: float, inverse: bool = False) -> str:
    if previous == 0:
        return "No prior-period data"
    change = ((current - previous) / abs(previous)) * 100
    direction = "up" if change >= 0 else "down"
    if inverse:
        direction = "down" if change >= 0 else "up"
    return f"{direction} {abs(change):.0f}% vs prior period"


class SummaryCard(QFrame):
    def __init__(self, title: str, accent: str):
        super().__init__()
        self.setObjectName("dashboardCard")
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        title_label = QLabel(title)
        title_label.setObjectName("dashboardLabel")
        layout.addWidget(title_label)
        self.value_label = QLabel("UGX 0")
        self.value_label.setObjectName("dashboardValue")
        layout.addWidget(self.value_label)
        self.comparison_label = QLabel("")
        self.comparison_label.setObjectName("dashboardMeta")
        self.comparison_label.setWordWrap(True)
        layout.addWidget(self.comparison_label)
        self.setStyleSheet(f"QFrame#dashboardCard {{ border-top: 3px solid {accent}; }}")
        self.setMinimumWidth(0)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def set_data(self, value: float, prior: float, inverse: bool = False):
        self.value_label.setText(money(value))
        self.comparison_label.setText(comparison(value, prior, inverse))


class CashflowChart(QFrame):
    def __init__(self):
        super().__init__()
        self.setObjectName("dashboardCard")
        self.setMinimumHeight(250)
        self.points = []
        self.setMouseTracking(True)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def set_points(self, points):
        self.points = points
        self.update()

    def mouseMoveEvent(self, event):
        if not self.points or self.width() <= 64:
            QToolTip.hideText()
            return
        chart_left = 32
        chart_width = max(self.width() - 64, 1)
        index = int((event.position().x() - chart_left) / (chart_width / len(self.points)))
        if 0 <= index < len(self.points):
            label, values = self.points[index]
            QToolTip.showText(
                event.globalPosition().toPoint(),
                f"{label}\nIncome: {money(values['income'])}\nExpenses: {money(values['expense'])}",
                self,
            )
        else:
            QToolTip.hideText()
        super().mouseMoveEvent(event)

    def paintEvent(self, event):
        event.accept()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor("#20201D"))
        if not self.points:
            painter.setPen(QColor("#A09E96"))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "No cash-flow activity in this period.")
            return
        margin = 32
        chart = QRectF(margin, 24, max(self.width() - margin * 2, 1), max(self.height() - 64, 1))
        maximum = max([max(item["income"], item["expense"]) for _, item in self.points] + [1])
        painter.setPen(QPen(QColor("#33332E"), 1))
        painter.drawLine(chart.left(), chart.bottom(), chart.right(), chart.bottom())
        width = chart.width() / len(self.points)
        for index, (label, values) in enumerate(self.points):
            x = chart.left() + index * width
            bar_width = max(width * 0.26, 3)
            income_height = chart.height() * values["income"] / maximum
            expense_height = chart.height() * values["expense"] / maximum
            painter.setBrush(QColor("#4DB6AC"))
            painter.drawRoundedRect(QRectF(x + width * 0.18, chart.bottom() - income_height, bar_width, income_height), 2, 2)
            painter.setBrush(QColor("#D4AF37"))
            painter.drawRoundedRect(QRectF(x + width * 0.52, chart.bottom() - expense_height, bar_width, expense_height), 2, 2)
            if len(self.points) <= 12 or index % max(len(self.points) // 8, 1) == 0:
                painter.setPen(QColor("#A09E96"))
                painter.drawText(QRectF(x, chart.bottom() + 8, width, 20), Qt.AlignmentFlag.AlignCenter, label)
        painter.setPen(QColor("#4DB6AC"))
        painter.drawText(12, 18, "Income")
        painter.setPen(QColor("#D4AF37"))
        painter.drawText(72, 18, "Expenses")


class DashboardView(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.account_service = AccountService()
        self.transaction_service = TransactionService()
        self.budget_service = BudgetService()
        self.goal_service = GoalService()
        self.setup_ui()

    def setup_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(28, 24, 28, 24)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setObjectName("dashboardScroll")
        content = QWidget()
        self.content_layout = QVBoxLayout(content)
        self.content_layout.setSpacing(18)

        header = QGridLayout()
        header.setHorizontalSpacing(10)
        header.setVerticalSpacing(8)
        self.header_layout = header
        welcome = QVBoxLayout()
        self.greeting = QLabel("Welcome back")
        self.greeting.setObjectName("dashboardTitle")
        self.journal_date = QLabel("")
        self.journal_date.setObjectName("dashboardMeta")
        welcome.addWidget(self.greeting)
        welcome.addWidget(self.journal_date)
        self.header_welcome = welcome
        self.period_combo = QComboBox()
        self.period_combo.addItem("This Month", "this_month")
        self.period_combo.addItem("Last Month", "last_month")
        self.period_combo.addItem("3 Months", "three_months")
        self.period_combo.addItem("6 Months", "six_months")
        self.period_combo.addItem("This Year", "this_year")
        self.period_combo.addItem("Custom", "custom")
        self.period_combo.currentIndexChanged.connect(self._period_changed)
        self.header_controls = [
            self.period_combo,
        ]
        self.custom_start = QDateEdit()
        self.custom_start.setCalendarPopup(True)
        self.custom_start.setDate(date.today().replace(day=1))
        self.custom_start.hide()
        self.custom_end = QDateEdit()
        self.custom_end.setCalendarPopup(True)
        self.custom_end.setDate(date.today())
        self.custom_end.hide()
        self.custom_start.dateChanged.connect(self._custom_period_changed)
        self.custom_end.dateChanged.connect(self._custom_period_changed)
        self._load_dashboard_preferences()
        self.header_controls.extend([self.custom_start, self.custom_end])
        self.add_transaction_button = QPushButton("+ Add Transaction")
        self.add_transaction_button.setObjectName("primaryButton")
        self.add_transaction_button.clicked.connect(self._open_transaction_dialog)
        self.header_controls.append(self.add_transaction_button)
        self.content_layout.addLayout(header)

        summary = QGridLayout()
        summary.setSpacing(12)
        self.summary_layout = summary
        self.summary_cards = []
        self.balance_card = SummaryCard("TOTAL BALANCE", "#D4AF37")
        self.income_card = SummaryCard("INCOME", "#4DB6AC")
        self.expense_card = SummaryCard("EXPENSES", "#D4AF37")
        self.savings_card = SummaryCard("NET SAVINGS / CASH FLOW", "#64B5F6")
        for card in (self.balance_card, self.income_card, self.expense_card, self.savings_card):
            self.summary_cards.append(card)
        self.content_layout.addLayout(summary)

        self.insight_label = QLabel("")
        self.insight_label.setObjectName("insightCard")
        self.insight_label.setWordWrap(True)
        self.content_layout.addWidget(self.insight_label)

        analytics = QGridLayout()
        analytics.setSpacing(14)
        self.analytics_layout = analytics
        cashflow_panel = QVBoxLayout()
        cashflow_title = QLabel("Cash flow")
        cashflow_title.setObjectName("sectionTitle")
        cashflow_panel.addWidget(cashflow_title)
        self.cashflow_chart = CashflowChart()
        cashflow_panel.addWidget(self.cashflow_chart)
        category_panel = QVBoxLayout()
        category_title = QLabel("Where your money goes")
        category_title.setObjectName("sectionTitle")
        category_panel.addWidget(category_title)
        self.category_list = QVBoxLayout()
        category_panel.addLayout(self.category_list)
        category_panel.addStretch()
        self.cashflow_panel = cashflow_panel
        self.category_panel = category_panel
        analytics.addLayout(cashflow_panel, 0, 0)
        analytics.addLayout(category_panel, 0, 1)
        self.content_layout.addLayout(analytics)

        lower = QGridLayout()
        lower.setSpacing(14)
        self.lower_layout = lower
        self.budget_panel = self._panel("Budget health")
        self.goal_panel = self._panel("Savings goals")
        self.accounts_panel = self._panel("Accounts")
        self.activity_panel = self._panel("Recent activity")
        lower.addWidget(self.budget_panel, 0, 0)
        lower.addWidget(self.goal_panel, 0, 1)
        lower.addWidget(self.accounts_panel, 1, 0)
        lower.addWidget(self.activity_panel, 1, 1)
        self.content_layout.addLayout(lower)

        self.time_machine_label = QLabel("")
        self.time_machine_label.setObjectName("insightCard")
        self.time_machine_label.setWordWrap(True)
        self.content_layout.addWidget(self.time_machine_label)
        time_machine = QPushButton("Open Financial Time Machine  →")
        time_machine.setObjectName("secondaryButton")
        time_machine.clicked.connect(lambda: self.main_window.navigate_to("time_machine"))
        self.content_layout.addWidget(time_machine, alignment=Qt.AlignmentFlag.AlignLeft)
        self.content_layout.addStretch()
        scroll.setWidget(content)
        outer.addWidget(scroll)
        self._apply_responsive_layout()

    def _panel(self, title: str) -> QFrame:
        panel = QFrame()
        panel.setObjectName("dashboardCard")
        layout = QVBoxLayout(panel)
        label = QLabel(title)
        label.setObjectName("sectionTitle")
        layout.addWidget(label)
        panel.body = QVBoxLayout()
        layout.addLayout(panel.body)
        return panel

    def _apply_responsive_layout(self):
        width = max(self.width(), 1)
        if width >= 1100:
            self.header_layout.addLayout(self.header_welcome, 0, 0)
            for column, widget in enumerate(self.header_controls, start=1):
                self.header_layout.addWidget(widget, 0, column)
            self.header_layout.setColumnStretch(0, 1)
        elif width >= 900:
            self.header_layout.addLayout(self.header_welcome, 0, 0, 1, 4)
            self.header_layout.addWidget(self.header_controls[0], 1, 0, 1, 2)
            self.header_layout.addWidget(self.header_controls[1], 1, 2)
            self.header_layout.addWidget(self.header_controls[2], 1, 3)
            self.header_layout.addWidget(self.header_controls[3], 1, 4)
            self.header_layout.setColumnStretch(0, 1)
        else:
            self.header_layout.addLayout(self.header_welcome, 0, 0, 1, 4)
            self.header_layout.addWidget(self.header_controls[0], 1, 0, 1, 2)
            self.header_layout.addWidget(self.header_controls[3], 1, 2, 1, 2)
            self.header_layout.addWidget(self.header_controls[1], 2, 0, 1, 2)
            self.header_layout.addWidget(self.header_controls[2], 2, 2, 1, 2)
            self.header_layout.setColumnStretch(0, 1)

        summary_columns = 4 if width >= 1280 else 2
        for index, card in enumerate(self.summary_cards):
            self.summary_layout.addWidget(
                card, index // summary_columns, index % summary_columns
            )
        for column in range(summary_columns):
            self.summary_layout.setColumnStretch(column, 1)

        analytics_columns = 2 if width >= 1100 else 1
        self.analytics_layout.addLayout(self.cashflow_panel, 0, 0)
        self.analytics_layout.addLayout(
            self.category_panel, 0, 1 if analytics_columns == 2 else 0
        )

        lower_columns = 2 if width >= 1200 else 1
        panels = (
            self.budget_panel,
            self.goal_panel,
            self.accounts_panel,
            self.activity_panel,
        )
        for index, panel in enumerate(panels):
            self.lower_layout.addWidget(panel, index // lower_columns, index % lower_columns)
        for column in range(lower_columns):
            self.lower_layout.setColumnStretch(column, 1)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "summary_layout"):
            self._apply_responsive_layout()

    def _period_changed(self):
        is_custom = self.period_combo.currentData() == "custom"
        self.custom_start.setVisible(is_custom)
        self.custom_end.setVisible(is_custom)
        self._save_dashboard_preferences()
        self.refresh()

    def _custom_period_changed(self):
        if self.period_combo.currentData() == "custom":
            self._save_dashboard_preferences()
            self.refresh()

    def _load_dashboard_preferences(self):
        preferences = load_preferences()
        period = str(preferences.get("dashboard_period", "this_month"))
        index = self.period_combo.findData(period)
        if index >= 0:
            self.period_combo.blockSignals(True)
            self.period_combo.setCurrentIndex(index)
            self.period_combo.blockSignals(False)
        is_custom = self.period_combo.currentData() == "custom"
        self.custom_start.setVisible(is_custom)
        self.custom_end.setVisible(is_custom)
        for widget, key in (
            (self.custom_start, "dashboard_custom_start"),
            (self.custom_end, "dashboard_custom_end"),
        ):
            value = str(preferences.get(key, ""))
            if value:
                parsed = widget.date().fromString(value, "yyyy-MM-dd")
                if parsed.isValid():
                    widget.setDate(parsed)

    def _save_dashboard_preferences(self):
        try:
            save_preferences({
                "dashboard_period": self.period_combo.currentData(),
                "dashboard_custom_start": self.custom_start.date().toString("yyyy-MM-dd"),
                "dashboard_custom_end": self.custom_end.date().toString("yyyy-MM-dd"),
            })
        except OSError:
            pass

    def _open_transaction_dialog(self):
        transactions_view = self.main_window.views.get("transactions")
        if transactions_view:
            self.main_window.navigate_to("transactions")
            transactions_view.show_add_dialog()

    def _clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def refresh(self):
        user = auth_service.get_current_user()
        if not user:
            return
        now = datetime.now()
        greeting = "Good morning" if now.hour < 12 else "Good afternoon" if now.hour < 17 else "Good evening"
        self.greeting.setText(f"{greeting}, {user.display_name or user.username}")
        self.journal_date.setText(now.strftime("%A, %d %B %Y"))
        db = SessionLocal()
        try:
            period = self.period_combo.currentData()
            custom_start = self.custom_start.date().toPython() if period == "custom" else None
            custom_end = self.custom_end.date().toPython() if period == "custom" else None
            snapshot = self.transaction_service.get_dashboard_snapshot(
                db, user.id, period, custom_start, custom_end
            )
            current = snapshot["current"]
            previous = snapshot["previous"]
            self.balance_card.set_data(self.account_service.get_total_balance(db, user.id), 0)
            self.income_card.set_data(current["income"], previous["income"])
            self.expense_card.set_data(current["expense"], previous["expense"], inverse=True)
            self.savings_card.set_data(current["savings"], previous["savings"])
            self.cashflow_chart.set_points(current["cashflow"])
            self._render_categories(current["categories"], current["expense"])
            self._render_budgets(db, user.id, snapshot["start"], snapshot["end"])
            self._render_goals(db, user.id)
            self._render_accounts(db, user.id)
            self._render_activity(current["transactions"])
            self._render_insight(current, previous)
            self.time_machine_label.setText(
                f"Time Machine · selected period: {snapshot['start'].strftime('%d %b %Y')} "
                f"→ {snapshot['end'].strftime('%d %b %Y')} | "
                f"prior: {snapshot['previous_start'].strftime('%d %b %Y')} "
                f"→ {snapshot['previous_end'].strftime('%d %b %Y')}"
            )
        except ValueError as exc:
            self.insight_label.setText(str(exc))
        finally:
            db.close()

    def _render_categories(self, categories, total):
        self._clear_layout(self.category_list)
        if not categories:
            self.category_list.addWidget(QLabel("No spending in this period."))
            return
        for name, amount in categories[:6]:
            percentage = amount / total * 100 if total else 0
            row = QHBoxLayout()
            label = QLabel(f"{name}  ·  {percentage:.0f}%")
            label.setObjectName("dashboardMeta")
            value = QLabel(money(amount))
            value.setObjectName("dashboardLabel")
            row.addWidget(label)
            row.addStretch()
            row.addWidget(value)
            self.category_list.addLayout(row)

    def _render_budgets(self, db, user_id, start, end):
        self._clear_layout(self.budget_panel.body)
        budgets = self.budget_service.get_budgets(db, user_id)
        if not budgets:
            self.budget_panel.body.addWidget(QLabel("No budgets configured."))
            return
        for budget in budgets[:4]:
            used = self.budget_service.get_budget_usage_for_range(db, budget, start, end)
            bar = QProgressBar()
            bar.setMaximum(budget.amount)
            bar.setValue(min(used, budget.amount))
            bar.setFormat(f"{used:,.0f} / {budget.amount:,.0f}")
            if used > budget.amount:
                bar.setObjectName("budgetExceeded")
            elif used >= budget.amount * 0.8:
                bar.setObjectName("budgetWarning")
            self.budget_panel.body.addWidget(QLabel(budget.category.name if budget.category else "Overall spending"))
            self.budget_panel.body.addWidget(bar)

    def _render_goals(self, db, user_id):
        self._clear_layout(self.goal_panel.body)
        goals = self.goal_service.get_goals(db, user_id)
        active = [goal for goal in goals if goal.status == "active"][:4]
        if not active:
            self.goal_panel.body.addWidget(QLabel("No active goals."))
            return
        for goal in active:
            percentage = min(goal.current_amount / goal.target_amount * 100, 100)
            self.goal_panel.body.addWidget(QLabel(f"{goal.name}  ·  {percentage:.0f}%"))
            bar = QProgressBar()
            bar.setMaximum(goal.target_amount)
            bar.setValue(min(goal.current_amount, goal.target_amount))
            bar.setFormat(f"{money(goal.current_amount)} / {money(goal.target_amount)}")
            self.goal_panel.body.addWidget(bar)

    def _render_accounts(self, db, user_id):
        self._clear_layout(self.accounts_panel.body)
        accounts = self.account_service.get_accounts(db, user_id)
        if not accounts:
            self.accounts_panel.body.addWidget(QLabel("No active accounts."))
            return
        for account in accounts[:6]:
            row = QHBoxLayout()
            row.addWidget(QLabel(f"{account.name}  ·  {account.account_type}"))
            row.addStretch()
            row.addWidget(QLabel(money(account.current_balance)))
            self.accounts_panel.body.addLayout(row)

    def _render_activity(self, transactions):
        self._clear_layout(self.activity_panel.body)
        if not transactions:
            self.activity_panel.body.addWidget(QLabel("No recent activity."))
            return
        for tx in transactions:
            label = "+" if tx.type == "income" else "↔" if tx.type == "transfer" else "−"
            category = tx.category.name if tx.category else tx.account.name
            row = QHBoxLayout()
            row.addWidget(QLabel(f"{tx.date.strftime('%d %b')}  {tx.description}"))
            row.addWidget(QLabel(category))
            row.addStretch()
            row.addWidget(QLabel(f"{label} {money(tx.amount)}"))
            self.activity_panel.body.addLayout(row)
        link = QPushButton("View all transactions →")
        link.setObjectName("secondaryButton")
        link.clicked.connect(lambda: self.main_window.navigate_to("transactions"))
        self.activity_panel.body.addWidget(link)

    def _render_insight(self, current, previous):
        insights = []
        if current["expense"] and previous["expense"]:
            direction = "increased" if current["expense"] > previous["expense"] else "decreased"
            insights.append(f"Spending {direction} {abs((current['expense'] - previous['expense']) / previous['expense'] * 100):.0f}% vs the previous period.")
        if current["categories"]:
            insights.append(f"Largest category: {current['categories'][0][0]} ({money(current['categories'][0][1])}).")
        if current["income"]:
            insights.append(f"Savings rate: {current['savings'] / current['income'] * 100:.0f}%.")
        insights.append(f"Average daily spending: {money(current['average_daily_spending'])}.")
        self.insight_label.setText("  •  ".join(insights))
