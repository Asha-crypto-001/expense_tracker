from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QPushButton, QFrame, QApplication
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from pathlib import Path
from src.core.config import load_preferences, save_preferences

class SettingsView(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.setup_ui()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(40, 40, 40, 40)
        
        title = QLabel("Settings")
        title.setObjectName("h1")
        main_layout.addWidget(title)
        
        main_layout.addSpacing(30)
        
        # Appearance Card
        self.card = QFrame()
        self.card.setObjectName("card")
        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(30, 30, 30, 30)
        card_layout.setSpacing(20)
        
        app_label = QLabel("Appearance")
        app_label.setObjectName("h2")
        card_layout.addWidget(app_label)
        
        # Font Family
        font_layout = QHBoxLayout()
        font_layout.addWidget(QLabel("Primary Font Family:"))
        self.font_combo = QComboBox()
        self.font_combo.addItems([
            "Canva Sans, IBM Plex Sans Arabic, Noto Sans Variable, Noto Sans, -apple-system, BlinkMacSystemFont, Segoe UI, Helvetica, Arial, sans-serif",
            "IBM Plex Sans Arabic, Noto Sans, Segoe UI, Arial, sans-serif",
            "Noto Sans, Segoe UI, Arial, sans-serif",
            "Courier New, monospace"
        ])
        font_layout.addWidget(self.font_combo)
        card_layout.addLayout(font_layout)
        
        # Base Font Size
        size_layout = QHBoxLayout()
        size_layout.addWidget(QLabel("Base Font Size:"))
        self.size_combo = QComboBox()
        self.size_combo.addItems(["12px", "14px", "16px", "18px"])
        self.size_combo.setCurrentText("14px")
        size_layout.addWidget(self.size_combo)
        card_layout.addLayout(size_layout)
        
        # Accent Color
        accent_layout = QHBoxLayout()
        accent_layout.addWidget(QLabel("Accent Color:"))
        self.accent_combo = QComboBox()
        self.accent_combo.addItems(["Gold (#D4AF37)", "Green (#4DB6AC)", "Blue (#64B5F6)", "Coral (#FF8A65)"])
        accent_layout.addWidget(self.accent_combo)
        card_layout.addLayout(accent_layout)
        
        # Apply button
        apply_btn = QPushButton("Apply Appearance Settings")
        apply_btn.setObjectName("primaryButton")
        apply_btn.clicked.connect(self.apply_settings)
        card_layout.addWidget(apply_btn)
        self.status_label = QLabel("")
        self.status_label.setObjectName("subtitle")
        card_layout.addWidget(self.status_label)
        
        main_layout.addWidget(self.card)
        main_layout.addStretch()
        self.refresh()

    def apply_settings(self):
        font_fam = self.font_combo.currentText()
        font_size = self.size_combo.currentText()
        accent_color = self.accent_combo.currentText().split("(")[1].strip(")")
        
        try:
            preferences = {
                "font_family": font_fam,
                "font_size": font_size,
                "accent_color": accent_color,
            }
            self._apply_preferences(preferences)
            save_preferences(preferences)
            self.status_label.setText("Appearance settings saved.")
            
        except (OSError, ValueError) as e:
            self.status_label.setText(f"Unable to save settings: {e}")

    def _apply_preferences(self, preferences):
        stylesheet_path = Path(__file__).resolve().parents[1] / "styles" / "main.qss"
        with stylesheet_path.open("r", encoding="utf-8") as stylesheet_file:
            base_qss = stylesheet_file.read()
        app = QApplication.instance()
        app.setStyleSheet(base_qss.replace("#D4AF37", str(preferences["accent_color"])))
        app.setFont(QFont(
            str(preferences["font_family"]).split(",")[0],
            int(str(preferences["font_size"]).replace("px", "")),
        ))
            
    def refresh(self):
        preferences = load_preferences()
        self.font_combo.setCurrentText(str(preferences["font_family"]))
        self.size_combo.setCurrentText(str(preferences["font_size"]))
        accent = str(preferences["accent_color"])
        for index in range(self.accent_combo.count()):
            if accent in self.accent_combo.itemText(index):
                self.accent_combo.setCurrentIndex(index)
                break
        try:
            self._apply_preferences(preferences)
        except (OSError, ValueError) as exc:
            self.status_label.setText(f"Unable to load settings: {exc}")
