"""
main.py — Entry point for the Adaptive Driver Drowsiness Monitoring System.
Bootstraps the PyQt6 application and launches the main window.
"""

import sys
import os
import ctypes

# Force proper Windows taskbar icon grouping
ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
    "neuroguard.ai.fatigue.monitor.1.0"
)

# Ensure the project root is on the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QFont, QIcon
from utils import resource_path

from gui import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon(resource_path("assets/favicon.ico")))
    self.setWindowIcon(QIcon(resource_path("assets/favicon.ico")))

    # Set a global application font
    app.setFont(QFont("Segoe UI", 10))

    # Apply a dark palette hint (supplement to the stylesheet)
    app.setStyle("Fusion")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
