import sys
import socket
import psutil
import threading
import time
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QLineEdit, QPushButton, QVBoxLayout,
    QHBoxLayout, QMessageBox, QComboBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QGroupBox, QDesktopWidget
)
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt, QTimer
from exposehost.client import Client

class ExposeHostApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ExposeHost Client")
        self.resize(900, 600)
        self.center()

        self.client = None
        self.timer = QTimer()
        self.timer.timeout.connect(self.populate_ports)
        self.timer.start(4000)

        title = QLabel("ExposeHost : Exposing LocalHost to Internet")
        title.setFont(QFont("Segoe UI", 20, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)

        port_group = QGroupBox("Active Localhost Ports")
        port_group_layout = QVBoxLayout()

        port_label = QLabel("Choose a running service or enter a custom port:")
        port_label.setFont(QFont("Segoe UI", 10))

        self.port_dropdown = QComboBox()
        self.port_dropdown.setEditable(True)
        self.port_dropdown.setPlaceholderText("Enter custom port or select from detected list")

        self.refresh_button = QPushButton("⟳")
        self.refresh_button.setFixedSize(32, 32)
        self.refresh_button.clicked.connect(self.populate_ports)

        port_hbox = QHBoxLayout()
        port_hbox.addWidget(self.port_dropdown)
        port_hbox.addWidget(self.refresh_button)

        port_group_layout.addWidget(port_label)
        port_group_layout.addLayout(port_hbox)
        port_group.setLayout(port_group_layout)

        service_group = QGroupBox("Detected Local Services")
        service_layout = QVBoxLayout()
        self.services_table = QTableWidget(0, 3)
        self.services_table.setHorizontalHeaderLabels(["Port", "Protocol", "Process"])
        self.services_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.services_table.verticalHeader().setVisible(False)
        self.services_table.setSelectionBehavior(self.services_table.SelectRows)
        self.services_table.setEditTriggers(self.services_table.NoEditTriggers)
        self.services_table.doubleClicked.connect(self.use_selected_service)
        service_layout.addWidget(self.services_table)
        service_group.setLayout(service_layout)

        subdomain_label = QLabel("Subdomain:")
        subdomain_label.setFont(QFont("Segoe UI", 10))
        self.subdomain_input = QLineEdit()
        self.subdomain_input.setPlaceholderText("Enter subdomain")
        self.start_button = QPushButton("Start Tunnel")
        self.start_button.clicked.connect(self.start_tunnel)

        subdomain_layout = QHBoxLayout()
        subdomain_layout.addWidget(subdomain_label)
        subdomain_layout.addWidget(self.subdomain_input)
        subdomain_layout.addWidget(self.start_button)

        self.forwarded_label = QLabel("")
        self.forwarded_label.setFont(QFont("Segoe UI", 11))
        self.forwarded_label.setTextInteractionFlags(Qt.TextBrowserInteraction)
        self.forwarded_label.setOpenExternalLinks(True)
        self.forwarded_label.setAlignment(Qt.AlignCenter)

        main_layout = QVBoxLayout()
        main_layout.addWidget(title)
        main_layout.addSpacing(20)
        main_layout.addWidget(port_group)
        main_layout.addSpacing(20)
        main_layout.addWidget(service_group)
        main_layout.addSpacing(30)
        main_layout.addLayout(subdomain_layout)
        main_layout.addWidget(self.forwarded_label)
        main_layout.addStretch()
        self.setLayout(main_layout)

        self.setStyleSheet("""
            QWidget { background-color: #ffffff; color: #111; font-family: 'Segoe UI'; }
            QGroupBox { border: 1px solid #ccc; border-radius: 6px; margin-top: 10px; padding: 10px; }
            QLabel { color: #222; }
            QPushButton { background-color: #111; color: #fff; padding: 8px 14px; border: none; border-radius: 4px; font-weight: bold; }
            QPushButton:hover { background-color: #333; }
            QComboBox, QLineEdit { border: 1px solid #555; padding: 6px; border-radius: 4px; background: #fff; }
            QHeaderView::section { background-color: #111; color: #fff; padding: 6px; border: none; }
            QTableWidget { gridline-color: #888; selection-background-color: #111; selection-color: #fff; font-size: 10.5pt; }
        """)

        self.populate_ports()

    def center(self):
        qr = self.frameGeometry()
        cp = QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

    def populate_ports(self):
        self.port_dropdown.clear()
        self.services_table.setRowCount(0)
        try:
            used_ports = {}
            for conn in psutil.net_connections(kind='inet'):
                if conn.laddr and conn.laddr.ip in ("127.0.0.1", "::1") and conn.status == psutil.CONN_LISTEN:
                    port = conn.laddr.port
                    proto = "TCP" if conn.type == socket.SOCK_STREAM else "UDP"
                    pid = conn.pid
                    if not pid or port == 1435:
                        continue
                    try:
                        p = psutil.Process(pid)
                        name = p.name()
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        name = "Unknown"
                    used_ports[str(port)] = (proto, name)

            for port in sorted(used_ports.keys(), key=lambda x: int(x)):
                self.port_dropdown.addItem(port)
            for i, (port, info) in enumerate(used_ports.items()):
                self.services_table.insertRow(i)
                self.services_table.setItem(i, 0, QTableWidgetItem(str(port)))
                self.services_table.setItem(i, 1, QTableWidgetItem(info[0]))
                self.services_table.setItem(i, 2, QTableWidgetItem(info[1]))

            if not used_ports:
                self.port_dropdown.addItem("No localhost services found")

        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def use_selected_service(self):
        row = self.services_table.currentRow()
        if row >= 0:
            port = self.services_table.item(row, 0).text()
            self.port_dropdown.setEditText(port)

    def start_tunnel(self):
        port = self.port_dropdown.currentText().strip()
        subdomain = self.subdomain_input.text().strip()
        if not port.isdigit():
            QMessageBox.warning(self, "Invalid Input", "Enter a valid port number.")
            return
        if not subdomain:
            QMessageBox.warning(self, "Invalid Input", "Subdomain cannot be empty.")
            return

        self.forwarded_label.setText("Starting tunnel...")

        def run_client():
            try:
                server_host = "exposehost.me"
                server_ip = socket.gethostbyname(server_host)
                client = Client('127.0.0.1', port, server_ip, 1435, 'http', subdomain)

                threading.Thread(target=client.start, daemon=True).start()

                # Wait a bit for the tunnel to initialize
                time.sleep(2)
                url = f"https://{subdomain}.exposehost.me"
                self.forwarded_label.setText(f"<div style='text-align:center; font-weight:bold; color:#007bff;'>Forwarded: <a href='{url}'>{url}</a></div>")

            except Exception as e:
                self.forwarded_label.setText("")
                QMessageBox.critical(self, "Error", str(e))

        threading.Thread(target=run_client, daemon=True).start()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ExposeHostApp()
    window.show()
    sys.exit(app.exec_())

