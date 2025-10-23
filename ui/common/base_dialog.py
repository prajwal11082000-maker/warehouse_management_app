from PyQt5.QtWidgets import QDialog
from PyQt5.QtCore import Qt


class BaseDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setModal(True)

        # Apply dark theme
        self.setStyleSheet("""
            QDialog {
                background-color: #2b2b2b;
                color: #ffffff;
            }
        """)