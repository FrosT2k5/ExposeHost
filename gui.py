import sys
import os
import psutil
import json
import urllib.request
from threading import Thread

# Ensure current directory is in path for module resolution
sys.path.append(os.getcwd())

from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QLineEdit, QPushButton, QComboBox, QGroupBox, 
                             QMessageBox, QFrame, QSizePolicy, QSpacerItem, 
                             QGraphicsDropShadowEffect, QStyle, QToolTip, QCompleter,
                             QListWidget, QListWidgetItem, QDesktopWidget, QDialog,
                             QScrollArea, QStackedWidget)
from PyQt5.QtCore import QTimer, Qt, pyqtSignal, QObject, QUrl, QSize
from PyQt5.QtGui import QIcon, QPixmap, QFont, QDesktopServices, QColor
from PyQt5.QtSvg import QSvgWidget

from exposehost.client import Client

# --- Theme Definitions ---
# --- Theme Definitions ---
class Theme:
    VERSION = "v0.1.0-alpha"
    GITHUB_REPO = "frost2k5/exposehost"
    
    COMMON = """
    * { outline: none; }
    QWidget { font-family: 'Inter', system-ui, sans-serif; }
    
    QScrollBar:vertical {
        border: none;
        background: transparent;
        width: 8px;
        margin: 0;
    }
    QScrollBar::handle:vertical {
        background: #52525b;
        min-height: 20px;
        border-radius: 4px;
    }
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
        height: 0px;
    }
    """

    DARK = COMMON + """
    QWidget {
        background-color: #0a0a0c;
        color: #f4f4f5;
        font-size: 16px; /* Increased base size */
    }
    
    QFrame#Header {
        background-color: #111114;
        border-bottom: 1px solid #27272a;
    }
    
    QLabel#Title {
        font-size: 24px; /* Bigger Title */
        font-weight: 700;
        color: #f4f4f5;
        letter-spacing: -0.02em;
    }
    
    QLineEdit, QComboBox, QListWidget {
        background-color: #18181b;
        border: 1px solid #27272a;
        border-radius: 8px;
        padding: 16px; /* More padding */
        color: #f4f4f5;
        font-size: 16px; /* Bigger input text */
        selection-background-color: #6366f1;
    }
    
    QLineEdit:focus {
        border: 1px solid #6366f1;
        background-color: #18181b;
    }
    
    QListWidget {
        background-color: #18181b;
        padding: 8px;
        font-size: 15px;
    }
    QListWidget::item {
        padding: 12px;
        border-radius: 6px;
        margin-bottom: 4px;
    }
    QListWidget::item:hover {
        background-color: #27272a;
    }
    QListWidget::item:selected {
        background-color: rgba(99, 102, 241, 0.2);
        color: #818cf8;
        border: 1px solid rgba(99, 102, 241, 0.4);
    }
    
    QPushButton {
        background-color: #6366f1;
        color: white;
        border: none;
        border-radius: 8px;
        padding: 16px 24px;
        font-weight: 700; /* BOLDER */
        font-size: 16px;
    }
    QPushButton:hover { background-color: #4f46e5; }
    QPushButton:pressed { background-color: #4338ca; }
    QPushButton:disabled { background-color: #27272a; color: #52525b; }
    
    QPushButton#IconBtn {
        background-color: transparent;
        border: 1px solid #27272a;
        color: #a1a1aa;
        padding: 10px;
        border-radius: 8px;
    }
    QPushButton#IconBtn:hover {
        border-color: #6366f1;
        color: #f4f4f5;
        background-color: rgba(99, 102, 241, 0.1);
    }

    QDialog { background-color: #0a0a0c; }
    QLabel#SettingsHeader { font-size: 24px; font-weight: 800; margin-bottom: 8px; }
    QGroupBox { border: 1px solid #27272a; border-radius: 8px; margin-top: 16px; padding-top: 32px; font-weight: 700; font-size: 15px; }
    QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top left; padding: 0 5px; left: 12px; color: #a1a1aa; }
    """

    LIGHT = COMMON + """
    QWidget {
        background-color: #ffffff;
        color: #18181b;
        font-size: 16px;
    }
    
    QFrame#Header {
        background-color: #ffffff;
        border-bottom: 1px solid #e4e4e7;
    }
    
    QLabel#Title {
        font-size: 24px; 
        font-weight: 700;
        color: #18181b;
        letter-spacing: -0.02em;
    }
    
    QLineEdit, QComboBox, QListWidget {
        background-color: #fafafa;
        border: 1px solid #e4e4e7;
        border-radius: 8px;
        padding: 16px;
        color: #18181b;
        font-size: 16px;
        selection-background-color: #6366f1;
    }
    
    QLineEdit:focus {
        border: 1px solid #6366f1;
        background-color: #ffffff;
    }
    
    QListWidget {
        background-color: #fafafa;
    }
    QListWidget::item {
        padding: 12px;
        border-radius: 6px;
        margin-bottom: 4px;
    }
    QListWidget::item:hover {
        background-color: #f4f4f5;
    }
    QListWidget::item:selected {
        background-color: rgba(99, 102, 241, 0.1);
        color: #6366f1;
        border: 1px solid rgba(99, 102, 241, 0.3);
    }
    
    QPushButton {
        background-color: #6366f1;
        color: white;
        border: none;
        border-radius: 8px;
        padding: 16px 24px;
        font-weight: 700;
        font-size: 16px;
    }
    QPushButton:hover { background-color: #4f46e5; }
    QPushButton:pressed { background-color: #4338ca; }
    QPushButton:disabled { background-color: #e4e4e7; color: #a1a1aa; }
    
    QPushButton#IconBtn {
        background-color: transparent;
        border: 1px solid #e4e4e7;
        color: #52525b;
        padding: 10px;
        border-radius: 8px;
    }
    QPushButton#IconBtn:hover {
        border-color: #6366f1;
        color: #6366f1;
        background-color: rgba(99, 102, 241, 0.05);
    }

    QDialog { background-color: #ffffff; }
    QLabel#SettingsHeader { font-size: 24px; font-weight: 800; margin-bottom: 8px; }
    QGroupBox { border: 1px solid #e4e4e7; border-radius: 8px; margin-top: 16px; padding-top: 32px; font-weight: 700; font-size: 15px; }
    QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top left; padding: 0 5px; left: 12px; color: #52525b; }
    """

class SettingsWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_gui = parent
        self.initUI()
        
    def initUI(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(24)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Header for Settings
        header_layout = QHBoxLayout()
        
        back_btn = QPushButton("← Back")
        back_btn.setCursor(Qt.PointingHandCursor)
        back_btn.setObjectName("IconBtn")
        back_btn.setFixedSize(80, 40)
        back_btn.clicked.connect(self.go_back)
        header_layout.addWidget(back_btn)
        
        title = QLabel("Settings")
        title.setObjectName("SettingsHeader") # Will style this
        title.setStyleSheet("font-size: 20px; font-weight: 700;")
        header_layout.addWidget(title)
        header_layout.addStretch()
        
        layout.addLayout(header_layout)
        
        # Scroll Area for settings content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("background: transparent;")
        
        content = QWidget()
        content.setStyleSheet("background: transparent;")
        content_layout = QVBoxLayout(content)
        content_layout.setSpacing(24)
        content_layout.setContentsMargins(0, 0, 10, 0) # Right margin for scrollbar
        
        # Appearance
        app_group = QGroupBox("Appearance")
        app_layout = QVBoxLayout()
        
        self.theme_btn = QPushButton(f"Switch to {'Light' if self.parent_gui and self.parent_gui.is_dark_mode else 'Dark'} Mode")
        self.theme_btn.setObjectName("IconBtn")
        self.theme_btn.setStyleSheet("text-align: left; padding: 12px;")
        self.theme_btn.clicked.connect(self.toggle_theme)
        app_layout.addWidget(self.theme_btn)
        
        app_group.setLayout(app_layout)
        content_layout.addWidget(app_group)
        
        # Updates
        update_group = QGroupBox("Updates")
        update_layout = QVBoxLayout()
        
        version_row = QHBoxLayout()
        version_label = QLabel(f"Current Version: {Theme.VERSION}")
        version_label.setStyleSheet("color: #a1a1aa;")
        version_row.addWidget(version_label)
        version_row.addStretch()
        update_layout.addLayout(version_row)
        
        self.check_update_btn = QPushButton("Check for Updates")
        self.check_update_btn.setObjectName("IconBtn")
        self.check_update_btn.setStyleSheet("text-align: left; padding: 12px;")
        self.check_update_btn.clicked.connect(self.check_for_updates)
        update_layout.addWidget(self.check_update_btn)
        
        update_group.setLayout(update_layout)
        content_layout.addWidget(update_group)
        
        # Credits
        credit_group = QGroupBox("Credits")
        credit_layout = QVBoxLayout()
        
        credit_text = QLabel("Built by\nYash Patil, Sairaj Pai & Nandini Nichite")
        credit_text.setStyleSheet("color: #71717a; font-size: 13px; line-height: 1.6; font-weight: 500;")
        credit_layout.addWidget(credit_text)
        
        github_btn = QPushButton("View on GitHub")
        github_btn.setObjectName("IconBtn")
        github_btn.setStyleSheet("text-align: left; padding: 12px; margin-top: 8px;")
        github_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(f"https://github.com/{Theme.GITHUB_REPO}")))
        credit_layout.addWidget(github_btn)
        
        credit_group.setLayout(credit_layout)
        content_layout.addWidget(credit_group)
        
        content_layout.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll)
        
    def go_back(self):
        if self.parent_gui:
            self.parent_gui.show_home()
            
    def toggle_theme(self):
        if self.parent_gui:
            self.parent_gui.toggle_theme()
            is_dark = self.parent_gui.is_dark_mode
            self.theme_btn.setText(f"Switch to {'Light' if is_dark else 'Dark'} Mode")

    def check_for_updates(self):
        self.check_update_btn.setText("Checking...")
        self.check_update_btn.setEnabled(False)
        
        # Run in thread to not block UI
        Thread(target=self._fetch_update, daemon=True).start()
        
    def _fetch_update(self):
        try:
            url = f"https://api.github.com/repos/{Theme.GITHUB_REPO}/releases/latest"
            # Set User-Agent to avoid github rate limits or 403s
            req = urllib.request.Request(url, headers={'User-Agent': 'ExposeHost-Client'})
            
            with urllib.request.urlopen(req) as response:
                data = json.loads(response.read().decode())
                latest_tag = data.get('tag_name', '')
                html_url = data.get('html_url', '')
                
                # Simple version comparison
                if latest_tag and latest_tag != Theme.VERSION:
                    QTimer.singleShot(0, lambda: self._show_update_available(latest_tag, html_url))
                else:
                    QTimer.singleShot(0, lambda: self._show_no_update())
        except urllib.error.HTTPError as e:
            if e.code == 404:
                 QTimer.singleShot(0, lambda: self._show_no_update()) # No releases found
            else:
                 print(f"Update HTTP error: {e}")
                 QTimer.singleShot(0, lambda: self._show_update_error())
        except Exception as e:
            print(f"Update check failed: {e}")
            QTimer.singleShot(0, lambda: self._show_update_error())

    def _show_update_available(self, version, url):
        self.check_update_btn.setText("Update Available!")
        self.check_update_btn.setEnabled(True)
        
        msg = QMessageBox(self)
        msg.setWindowTitle("Update Available")
        msg.setText(f"A new version ({version}) is available.")
        msg.setInformativeText("Would you like to view the release page?")
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg.setDefaultButton(QMessageBox.Yes)
        
        if msg.exec_() == QMessageBox.Yes:
            QDesktopServices.openUrl(QUrl(url))
            
    def _show_no_update(self):
        self.check_update_btn.setText("You are up to date (No updates found)")
        self.check_update_btn.setEnabled(True)
        
    def _show_update_error(self):
        self.check_update_btn.setText("Check Failed (See Console)")
        self.check_update_btn.setEnabled(True)

class ServiceScanner(QObject):
    scan_finished = pyqtSignal(list)
    
    # Extended list of system processes to ignore
    IGNORED_PROCESSES = [
        'systemd', 'avahi-daemon', 'cupsd', 'rpcbind', 'dhclient',
        'networkmanager', 'kded5', 'dbus-daemon', 'rtkit-daemon',
        'polkitd', 'wpa_supplicant', 'unattended-upgr', 'containerd',
        'dockerd', 'colord', 'gnome-shell', 'Xorg', 'Xwayland',
        'audispd', 'auditd', 'chronyd', 'crond', 'master', 'qmgr',
        'sshd', 'systemd-resolve', 'systemd-logind', 'systemd-network',
        'systemd-timesyn', 'thermald', 'whoopsie', 'wpa_supplicant',
        'zfs-arc', 'zfs-zevent', 'zfs-zpool'
    ]

    def scan(self):
        services = []
        try:
            for conn in psutil.net_connections(kind='inet'):
                if conn.status == 'LISTEN':
                    try:
                        # Listen on local interfaces
                        if conn.laddr.ip in ['127.0.0.1', '0.0.0.0', '::', '::1', '127.0.0.53']:
                            port = conn.laddr.port
                            
                            # Filter out system ports except common web/dev ports
                            is_system_port = port < 1024 and port not in [80, 443, 8080]
                            if not is_system_port:
                                proc = psutil.Process(conn.pid)
                                name = proc.name()
                                
                                if name in self.IGNORED_PROCESSES:
                                    continue
                                
                                # Skip if name looks like a system kernel thread or similar
                                if name.startswith('kworker'): 
                                    continue

                                services.append({
                                    'port': port,
                                    'name': name,
                                    'display': f"{port} — {name}"
                                })
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue
        except Exception as e:
            print(f"Scan error: {e}")
        
        services.sort(key=lambda x: x['port'])
        
        unique_services = []
        seen_ports = set()
        for s in services:
            if s['port'] not in seen_ports:
                unique_services.append(s)
                seen_ports.add(s['port'])
                
        self.scan_finished.emit(unique_services)

class ExposeHostGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.client = None
        self.is_dark_mode = True
        self.scanner = ServiceScanner()
        self.scanner.scan_finished.connect(self.on_scan_finished)
        self.initUI()
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_status)
        
        # Initial scan
        QTimer.singleShot(200, self.refresh_services)

    def initUI(self):
        self.setWindowTitle('ExposeHost Client')
        self.resize(600, 750) # Taller, slightly narrower for better density
        self.center_window()
        
        # Stack wrapper for main content
        self.stack = QStackedWidget()
        
        # --- Page 1: Home ---
        self.home_widget = QWidget()
        home_layout = QVBoxLayout(self.home_widget)
        home_layout.setContentsMargins(0, 0, 0, 0)
        home_layout.setSpacing(0)
        
        # Header (Only on Home)
        self.header = QFrame()
        self.header.setObjectName("Header")
        header_layout = QHBoxLayout(self.header)
        header_layout.setContentsMargins(24, 16, 24, 16) # Reduced margins slightly
        
        # Logo
        logo_path = os.path.join(os.path.dirname(__file__), 'landing-page', 'logo.svg')
        if os.path.exists(logo_path):
            logo_widget = QSvgWidget(logo_path)
            logo_widget.setFixedSize(48, 48) # WAY BIGGER
            header_layout.addWidget(logo_widget)
        
        title = QLabel("ExposeHost")
        title.setObjectName("Title")
        header_layout.addWidget(title)
        header_layout.addStretch()
        
        # Settings Toggle
        self.settings_btn = QPushButton("⚙")
        self.settings_btn.setObjectName("IconBtn")
        self.settings_btn.setFixedSize(52, 52) # Bigger touch target
        self.settings_btn.setCursor(Qt.PointingHandCursor)
        self.settings_btn.clicked.connect(self.open_settings)
        header_layout.addWidget(self.settings_btn)
        
        home_layout.addWidget(self.header)
        
        # Content Container
        content_container = QWidget()
        content_layout = QVBoxLayout(content_container)
        content_layout.setContentsMargins(24, 24, 24, 24) # Tighter margins
        content_layout.setSpacing(16) # Reduced spacing between elements
        
        # 1. Main Form
        
        # Port Input
        port_label = QLabel("Local Port")
        port_label.setStyleSheet("font-weight: 700; font-size: 15px; color: #a1a1aa;")
        content_layout.addWidget(port_label)
        
        port_row = QHBoxLayout()
        port_row.setSpacing(12)
        
        self.port_input = QLineEdit()
        self.port_input.setPlaceholderText("e.g. 3000")
        self.port_input.setFixedHeight(60) # BIGGER input
        port_row.addWidget(self.port_input)
        
        self.refresh_btn = QPushButton("↺") 
        self.refresh_btn.setObjectName("RefreshBtn")
        self.refresh_btn.setFixedSize(60, 60) # MATCH input height
        self.refresh_btn.setCursor(Qt.PointingHandCursor)
        self.refresh_btn.clicked.connect(self.refresh_services)
        self.refresh_btn.setToolTip("Scan for active services")
        port_row.addWidget(self.refresh_btn)
        
        content_layout.addLayout(port_row)
        
        # Service List Checkbox/Area
        services_label = QLabel("Active Services")
        services_label.setStyleSheet("font-size: 15px; font-weight: 700; margin-top: 8px; color: #a1a1aa;")
        content_layout.addWidget(services_label)

        self.service_list = QListWidget()
        self.service_list.setStyleSheet("font-family: 'JetBrains Mono'; font-size: 15px;") 
        self.service_list.itemClicked.connect(self.on_service_selected)
        content_layout.addWidget(self.service_list)

        # Subdomain (Mandatory)
        sub_label = QLabel("Subdomain (Required)")
        sub_label.setStyleSheet("font-weight: 700; font-size: 15px; color: #a1a1aa;")
        self.subdomain_input = QLineEdit()
        self.subdomain_input.setFixedHeight(60) # BIGGER input
        self.subdomain_input.setPlaceholderText("your-app-name")
        content_layout.addWidget(sub_label)
        content_layout.addWidget(self.subdomain_input)
        
        content_layout.addSpacing(16)
        
        # Start Button
        self.start_btn = QPushButton("Start Exposing")
        self.start_btn.setObjectName("StartButton")
        self.start_btn.setFixedHeight(64) # BIGGER, TALLER button
        self.start_btn.setCursor(Qt.PointingHandCursor)
        self.start_btn.clicked.connect(self.start_client)
        # Shadow effect
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 80))
        shadow.setOffset(0, 4)
        self.start_btn.setGraphicsEffect(shadow)
        content_layout.addWidget(self.start_btn)
        
        content_layout.addStretch()
        
        # Status Footer
        self.status_group = QGroupBox()
        self.status_group.setStyleSheet("border: none; background: transparent; margin: 0;")
        status_layout = QVBoxLayout(self.status_group)
        status_layout.setContentsMargins(0, 10, 0, 0)
        status_layout.setSpacing(8)
        
        self.status_label = QLabel("Ready to connect")
        self.status_label.setObjectName("StatusText")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("font-size: 18px; font-weight: 700; color: #71717a;")
        
        self.url_label = QLabel("")
        self.url_label.setObjectName("UrlBox")
        self.url_label.setAlignment(Qt.AlignCenter)
        self.url_label.setOpenExternalLinks(True)
        self.url_label.hide()
        
        status_layout.addWidget(self.status_label)
        status_layout.addWidget(self.url_label)
        
        content_layout.addWidget(self.status_group)
        
        home_layout.addWidget(content_container)
        
        # --- Page 2: Settings ---
        self.settings_widget = SettingsWidget(self)
        self.settings_wrapper = QWidget()
        settings_layout = QVBoxLayout(self.settings_wrapper)
        settings_layout.setContentsMargins(24, 24, 24, 24) # Tighter margins here too
        settings_layout.addWidget(self.settings_widget)
        
        # Add Pages
        self.stack.addWidget(self.home_widget)
        self.stack.addWidget(self.settings_wrapper)
        
        # Set Main Layout
        self.main_layout = QVBoxLayout()
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.addWidget(self.stack)
        
        self.setLayout(self.main_layout)
        
        # Apply Theme
        self.update_theme(initial=True)

    def center_window(self):
        qr = self.frameGeometry()
        cp = QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

    def update_theme(self, initial=False):
        style = Theme.DARK if self.is_dark_mode else Theme.LIGHT
        self.setStyleSheet(style)
        
    def toggle_theme(self):
        self.is_dark_mode = not self.is_dark_mode
        self.update_theme()

    def open_settings(self):
        self.stack.setCurrentIndex(1)
        
    def show_home(self):
        self.stack.setCurrentIndex(0)

    def refresh_services(self):
        self.refresh_btn.setEnabled(False)
        self.scan_thread = Thread(target=self.scanner.scan)
        self.scan_thread.start()

    def on_scan_finished(self, services):
        self.refresh_btn.setEnabled(True)
        self.service_list.clear()
        
        if not services:
            item = QListWidgetItem("No active services found")
            item.setFlags(Qt.NoItemFlags) # Disable selection
            self.service_list.addItem(item)
            return

        for s in services:
            # Store port as data in the item
            item = QListWidgetItem(s['display'])
            item.setData(Qt.UserRole, s['port'])
            self.service_list.addItem(item)

    def on_service_selected(self, item):
        port = item.data(Qt.UserRole)
        if port:
            self.port_input.setText(str(port))
            # Auto-focus the subdomain input if empty
            if not self.subdomain_input.text():
                self.subdomain_input.setFocus()

    def start_client(self):
        port = self.port_input.text().strip()
        subdomain = self.subdomain_input.text().strip()
        protocol = 'http'
        host = '127.0.0.1' 
        
        if not port or not port.isdigit():
            QMessageBox.warning(self, "Validation Error", "Please enter a valid numeric port.")
            self.port_input.setFocus()
            return
            
        if not subdomain:
            QMessageBox.warning(self, "Validation Error", "Subdomain is required.")
            self.subdomain_input.setFocus()
            return

        self.set_ui_state(running=True)
        
        try:
            self.client = Client(host, port, "exposehost.me", 1435, protocol, subdomain)
            self.client.start_non_blocking()
            self.timer.start(500)
        except Exception as e:
            error_msg = str(e)
            
            # Sanitized error messages
            if "Connection refused" in error_msg:
                error_msg = "Could not connect to ExposeHost server. Please check your internet connection."
            elif "Permission denied" in error_msg:
                error_msg = "Permission denied. You might need to run as administrator."
            elif "timed out" in error_msg.lower():
                error_msg = "Connection timed out. Server might be busy."
                
            QMessageBox.critical(self, "Connection Failed", error_msg)
            self.set_ui_state(running=False)

    def set_ui_state(self, running):
        enabled = not running
        self.port_input.setEnabled(enabled)
        self.service_list.setEnabled(enabled)
        self.subdomain_input.setEnabled(enabled)
        self.refresh_btn.setEnabled(enabled)
        self.start_btn.setEnabled(enabled)
        
        if running:
            self.start_btn.setText("Starting Tunnel...")
            self.status_label.setText("Initializing...")
            self.status_label.setStyleSheet("font-size: 16px; font-weight: 600; color: #facc15;")
        else:
            self.start_btn.setText("Start Exposing")
            self.status_label.setText("Ready to connect")
            self.status_label.setStyleSheet("font-size: 16px; font-weight: 600; color: #71717a;")
            self.url_label.hide()

    def update_status(self):
        if not self.client: return
        
        status = self.client.get_status()
        
        if status == "connected":
            self.status_label.setText("ONLINE")
            self.status_label.setStyleSheet("font-size: 16px; font-weight: 600; color: #22c55e;")
            url = self.client.get_url()
            if url:
                self.url_label.setText(f'<a href="{url}" style="color: #22d3ee; text-decoration: none;">{url}</a>')
                self.url_label.show()
                self.start_btn.setText("Tunnel Active")
                
        elif status == "failed":
            self.status_label.setText("CONNECTION FAILED")
            self.status_label.setStyleSheet("font-size: 16px; font-weight: 600; color: #ef4444;")
            self.set_ui_state(running=False)
            self.timer.stop()

if __name__ == '__main__':
    try:
        app = QApplication(sys.argv)
        ex = ExposeHostGUI()
        ex.show()
        sys.exit(app.exec_())
    except Exception as e:
        print(f"Error: {e}")
