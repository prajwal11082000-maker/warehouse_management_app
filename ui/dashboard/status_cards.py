from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame
from PyQt5.QtCore import Qt, QPropertyAnimation, QEasingCurve
from PyQt5.QtGui import QFont


class StatusCardWidget(QWidget):
    def __init__(self, title, value, color, icon=""):
        super().__init__()
        self.title = title
        self.current_value = value
        self.color = color
        self.icon = icon

        self.setup_ui()
        self.setup_animation()

    def setup_ui(self):
        """Setup status card UI with proper visibility"""
        self.setFixedSize(280, 120)  # Made wider for better text visibility
        self.setSizePolicy(self.sizePolicy().Expanding, self.sizePolicy().Fixed)

        # Main frame with visible styling
        frame = QFrame()
        frame.setStyleSheet(f"""
            QFrame {{
                background-color: #404040;
                border: 2px solid {self.color};
                border-radius: 8px;
                padding: 0px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(frame)

        # Card content
        card_layout = QVBoxLayout(frame)
        card_layout.setContentsMargins(15, 12, 15, 12)
        card_layout.setSpacing(8)

        # Top row - icon and value
        top_layout = QHBoxLayout()
        top_layout.setSpacing(10)

        # Icon
        if self.icon:
            icon_label = QLabel(self.icon)
            icon_label.setFont(QFont("Arial", 24))
            icon_label.setFixedSize(40, 40)
            icon_label.setAlignment(Qt.AlignCenter)
            icon_label.setStyleSheet("color: #ffffff; background: transparent;")
            top_layout.addWidget(icon_label)

        top_layout.addStretch()

        # Value - make it VERY visible
        self.value_label = QLabel(self.current_value)
        self.value_label.setFont(QFont("Arial", 32, QFont.Bold))
        self.value_label.setStyleSheet(f"""
            color: {self.color}; 
            background: transparent; 
            font-weight: bold;
            text-align: right;
        """)
        self.value_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        top_layout.addWidget(self.value_label)

        card_layout.addLayout(top_layout)

        # Title - make it clearly visible
        title_label = QLabel(self.title)
        title_label.setFont(QFont("Arial", 12, QFont.Bold))
        title_label.setStyleSheet("""
            color: #ffffff; 
            background: transparent;
            font-weight: bold;
            padding: 0px;
            margin: 0px;
        """)
        title_label.setWordWrap(True)
        title_label.setAlignment(Qt.AlignLeft | Qt.AlignBottom)
        card_layout.addWidget(title_label)

    def setup_animation(self):
        """Setup value change animation"""
        self.animation = QPropertyAnimation(self, b"windowOpacity")
        self.animation.setDuration(300)
        self.animation.setEasingCurve(QEasingCurve.InOutQuad)

    def update_value(self, new_value):
        """Update the card value with animation"""
        if new_value != self.current_value:
            old_value = self.current_value
            self.current_value = new_value

            # Animate opacity change
            self.animation.setStartValue(1.0)
            self.animation.setEndValue(0.7)
            self.animation.finished.connect(lambda: self._update_text(old_value))
            self.animation.start()

    def _update_text(self, old_value):
        """Update text after fade out"""
        self.value_label.setText(self.current_value)

        # Fade back in
        self.animation.finished.disconnect()
        self.animation.setStartValue(0.7)
        self.animation.setEndValue(1.0)
        self.animation.start()

    def set_color(self, color):
        """Change card accent color"""
        self.color = color
        self.value_label.setStyleSheet(f"""
            color: {color}; 
            background: transparent; 
            font-weight: bold;
            text-align: right;
        """)

        # Update frame border
        frame = self.findChild(QFrame)
        if frame:
            frame.setStyleSheet(f"""
                QFrame {{
                    background-color: #404040;
                    border: 2px solid {color};
                    border-radius: 8px;
                    padding: 0px;
                }}
            """)