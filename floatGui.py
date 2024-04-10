import sys
import serial
import serial.tools.list_ports
from PyQt5.QtCore import QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QIcon
from PyQt5 import QtCore
from PyQt5.QtCore import Qt
from PyQt5 import QtGui
from PyQt5.QtGui import QMouseEvent
from PyQt5.QtWidgets import QApplication
from PyQt5.QtWidgets import (QApplication, QDialog, QComboBox, QPushButton,
                             QTextEdit, QVBoxLayout, QHBoxLayout, QLabel, QMessageBox)

style_sheet = """QDialog {
    background-color: #252525;
    color: #f0f0f0;
}

QLabel {
    color: #f0f0f0;
}

QComboBox, QPushButton {
    background-color: #1e1e1e;
    border: none;
    color: #f0f0f0;
    padding: 5px;
}

QComboBox:hover, QPushButton:hover {
    background-color: #3d3d3d;
}

QTextEdit {
    background-color: #1e1e1e;
    border: none;
    color: #f0f0f0;
}

QTextEdit:hover {
    background-color: #3d3d3d;
}

QComboBox::drop-down, QComboBox::down-arrow, QPushButton::down-arrow {
    image: url(down-arrow.png);
}

QComboBox::drop-down:hover, QComboBox::down-arrow:hover, QPushButton::down-arrow:hover {
    background-color: #3d3d3d;
}

QComboBox::drop-down:on {
    background-color: #3d3d3d;
}

QPushButton:pressed {
    background-color: #4c4c4c;
    padding-left: 4px;
    padding-top: 4px;
}

QMessageBox {
    background-color: #1e1e1e;
    color: #f0f0f0;
}

QMessageBox QPushButton {
    background-color: #3d3d3d;
    color: #f0f0f0;
    border: none;
    padding: 5px;
}

QMessageBox QPushButton:hover {
    background-color: #4c4c4c;
}

QcomboBox QAbstractItemView {
    background-color: #1e1e1e;
    color: #f0f0f0;
    border: none;
    selection-background-color: #3d3d3d;
}
"""


class SerialReaderThread(QThread):
    new_packet = pyqtSignal(str)

    def __init__(self, serial_port, parent=None):
        super().__init__(parent)
        self.serial_port = serial_port

    def run(self):
        while True:
            try:
                if self.serial_port.in_waiting:
                    packet = self.serial_port.readline()
                    msg = packet.decode('utf-8').rstrip('\n')
                    self.new_packet.emit(msg)
            except Exception as e:
                self.new_packet.emit(str(e))
                break


class DraggableDialog(QDialog):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._is_dragging = False
        self._mouse_pos = None

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            self._is_dragging = True
            self._mouse_pos = event.pos()

    def mouseMoveEvent(self, event: QMouseEvent):
        if self._is_dragging:
            diff = event.pos() - self._mouse_pos
            new_pos = self.pos() + diff
            self.move(new_pos)

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            self._is_dragging = False
            self._mouse_pos = None


class SerialConnectDialog(DraggableDialog):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(style_sheet)
        self.setWindowTitle("Float Engine Receiver")
        self.setWindowIcon(QIcon('icon.png'))
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setFixedSize(500, 1000)
        self.setWindowFlags(self.windowFlags() & ~
                            QtCore.Qt.WindowContextHelpButtonHint)
        self.combo_box = QComboBox()
        self.connect_button = QPushButton("Connect")
        self.text_edit = QTextEdit(readOnly=True)
        self.text_edit.setAlignment(QtCore.Qt.AlignCenter)

        self.status_label = QLabel("Select a serial port to connect")
        self.status_label.setAlignment(QtCore.Qt.AlignCenter)

        self.serial_port = None
        self.thread = None
        closeBar = QHBoxLayout()
        closeBar.addWidget(QPushButton(
            "-", clicked=lambda: self.showMinimized()))
        closeBar.addWidget(QPushButton("X", clicked=self.close))
        closeBar.setAlignment(QtCore.Qt.AlignRight)
        title = QLabel("Float Engine Receiver")
        title.setStyleSheet("font-size: 20px;")
        titleBar = QHBoxLayout()
        titleBar.addWidget(title)
        titleBar.addStretch()
        titleBar.addLayout(closeBar)
        titleBar.setAlignment(QtCore.Qt.AlignRight)
        layout1 = QHBoxLayout()
        layout1.addWidget(self.combo_box)
        layout1.addWidget(self.connect_button)
        layout2 = QVBoxLayout()
        layout2.addWidget(self.text_edit)
        layout2.addWidget(self.status_label)

        main_layout = QVBoxLayout(self)
        main_layout.addLayout(titleBar)
        main_layout.addLayout(layout1)
        main_layout.addLayout(layout2)

        self.refreshPorts()
        self.connect_button.clicked.connect(self.connectSerial)

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        painter.setPen(QtCore.Qt.NoPen)
        painter.setBrush(QtGui.QColor(37, 37, 37))
        painter.drawRoundedRect(self.rect(), 10, 10)

    def refreshPorts(self):
        try:
            self.combo_box.clear()
            ports = serial.tools.list_ports.comports()

            if not ports:
                self.status_label.setText("No serial ports detected.")
                self.status_label.setStyleSheet('color: red;')
                return

            self.combo_box.addItems([port.device for port in ports])

            if self.serial_port and self.serial_port.is_open and self.serial_port.name in [port.device for port in ports] and self.serial_port.name == self.combo_box.currentText() and self.thread and self.thread.isRunning():
                self.status_label.setText(
                    f"Connected to {self.serial_port.name}")
                self.status_label.setStyleSheet('color: green;')

            else:
                self.status_label.setText("Select a serial port to connect")

        except Exception as e:
            self.showError(str(e))

    def connectSerial(self):
        try:
            self.connectSerialFn()
        except Exception as e:
            self.showError(str(e))
            self.status_label.setText("Select a serial port to connect")
            self.status_label.setStyleSheet('color: black;')

    def connectSerialFn(self):
        if not self.combo_box.count():
            raise ValueError("No serial port selected")

        port_name = self.combo_box.currentText()
        self.serial_port = serial.Serial(
            port_name, baudrate=9600, timeout=1)
        self.serial_port.flushInput()

        if self.thread and self.thread.isRunning():
            self.thread.terminate()

        self.thread = SerialReaderThread(self.serial_port)
        self.thread.new_packet.connect(self.text_edit.append)
        self.thread.start()
        self.setStyleSheet(style_sheet)
        self.status_label.setText(f"Connected to {port_name}")
        self.status_label.setStyleSheet('color: green;')

    def showError(self, error):
        msg_box = QMessageBox()
        msg_box.setWindowTitle("Error")
        msg_box.setText(error)
        msg_box.exec_()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    dialog = SerialConnectDialog()
    dialog.show()
    timer = QTimer()
    timer.timeout.connect(dialog.refreshPorts)
    timer.start(1000)
    sys.exit(app.exec_())
