from PySide6.QtWidgets import QApplication, QLabel, QMainWindow
import sys

app = QApplication(sys.argv)
window = QMainWindow()
window.setWindowTitle("Test")
window.setCentralWidget(QLabel("Hello World!"))
window.show()
window.raise_()
sys.exit(app.exec())