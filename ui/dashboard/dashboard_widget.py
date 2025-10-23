from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
                             QLabel, QFrame, QPushButton, QScrollArea, QSizePolicy)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QFont

from .status_cards import StatusCardWidget
from ui.common.table_widget import DataTableWidget
from api.client import APIClient
from api.devices import DevicesAPI
from api.tasks import TasksAPI
from data_manager.csv_handler import CSVHandler
from utils.logger import setup_logger


class DashboardWidget(QWidget):
    refresh_requested = pyqtSignal()

    def __init__(self, api_client: APIClient, csv_handler: CSVHandler):
        super().__init__()
        self.api_client = api_client
        self.csv_handler = csv_handler
        self.devices_api = DevicesAPI(api_client)
        self.tasks_api = TasksAPI(api_client)
        self.logger = setup_logger('dashboard')

        self.setup_ui()
        self.setup_timer()
        self.refresh_data()

    def setup_ui(self):
        """Setup dashboard UI with proper responsive design"""
        # Main layout - no margins since we don't want the duplicate title
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 0, 20, 20)  # No top margin to remove extra space
        layout.setSpacing(20)

        # Status cards section
        self.create_status_cards_section(layout)

        # Content area with scroll
        self.create_content_area(layout)

        # Refresh button at bottom
        self.create_refresh_button(layout)

    def create_status_cards_section(self, parent_layout):
        """Create responsive status cards grid"""
        cards_frame = QFrame()
        cards_frame.setStyleSheet("""
            QFrame {
                background-color: transparent;
                border: none;
            }
        """)
        cards_layout = QGridLayout(cards_frame)
        cards_layout.setSpacing(15)
        cards_layout.setContentsMargins(0, 0, 0, 0)

        # Create status cards with proper sizing
        self.device_working_card = StatusCardWidget("Working Devices", "0", "#10B981", "🤖")
        self.device_charging_card = StatusCardWidget("Charging", "0", "#F59E0B", "🔋")
        self.device_issues_card = StatusCardWidget("Issues", "0", "#EF4444", "⚠️")
        self.device_total_card = StatusCardWidget("Total Devices", "0", "#6B7280", "📟")

        self.task_pending_card = StatusCardWidget("Pending Tasks", "0", "#3B82F6", "📋")
        self.task_running_card = StatusCardWidget("Running Tasks", "0", "#10B981", "🏃")
        self.task_completed_card = StatusCardWidget("Completed Today", "0", "#8B5CF6", "✅")
        self.task_failed_card = StatusCardWidget("Failed Tasks", "0", "#EF4444", "❌")

        # Add cards to responsive grid (4 columns, 2 rows)
        cards = [
            self.device_working_card, self.device_charging_card, self.device_issues_card, self.device_total_card,
            self.task_pending_card, self.task_running_card, self.task_completed_card, self.task_failed_card
        ]

        for i, card in enumerate(cards):
            row = i // 4
            col = i % 4
            cards_layout.addWidget(card, row, col)
            # Make columns expand equally
            cards_layout.setColumnStretch(col, 1)

        parent_layout.addWidget(cards_frame)

    def create_content_area(self, parent_layout):
        """Create scrollable content area"""
        # Main scroll area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameStyle(QFrame.NoFrame)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # Scroll content widget
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setSpacing(20)
        scroll_layout.setContentsMargins(0, 0, 0, 0)

        # Recent Tasks Section
        self.create_recent_tasks_section(scroll_layout)

        # Active Devices Section
        self.create_active_devices_section(scroll_layout)

        scroll_area.setWidget(scroll_widget)
        parent_layout.addWidget(scroll_area)

    def create_recent_tasks_section(self, parent_layout):
        """Create recent tasks section with proper visibility"""
        # Section frame
        tasks_frame = QFrame()
        tasks_frame.setStyleSheet("""
            QFrame {
                background-color: #353535;
                border: 1px solid #555555;
                border-radius: 6px;
                padding: 15px;
            }
        """)
        tasks_layout = QVBoxLayout(tasks_frame)
        tasks_layout.setSpacing(15)

        # Section header
        header_layout = QHBoxLayout()

        tasks_title = QLabel("Recent Tasks")
        tasks_title.setFont(QFont("Arial", 16, QFont.Bold))
        tasks_title.setStyleSheet("color: #ffffff; margin: 0;")
        header_layout.addWidget(tasks_title)

        header_layout.addStretch()

        # View all button
        view_all_btn = QPushButton("View All Tasks")
        view_all_btn.setStyleSheet("""
            QPushButton {
                background-color: #ff6b35;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #e55a2b;
            }
        """)
        header_layout.addWidget(view_all_btn)

        tasks_layout.addLayout(header_layout)

        # Tasks table with proper styling
        self.recent_tasks_table = DataTableWidget([
            "Task ID", "Task Name", "Type", "Status", "Assigned Device", "Created"
        ], searchable=True, selectable=True)

        # Set fixed height for table
        self.recent_tasks_table.setMinimumHeight(250)
        self.recent_tasks_table.setMaximumHeight(300)

        # Improve table styling
        self.recent_tasks_table.setStyleSheet("""
            QWidget {
                background-color: #404040;
                color: #ffffff;
            }
            QTableWidget {
                background-color: #404040;
                alternate-background-color: #454545;
                gridline-color: #555555;
                color: #ffffff;
                border: 1px solid #555555;
                border-radius: 4px;
            }
            QTableWidget::item {
                padding: 8px;
                border: none;
                color: #ffffff;
            }
            QTableWidget::item:selected {
                background-color: #ff6b35;
                color: #ffffff;
            }
            QHeaderView::section {
                background-color: #353535;
                padding: 10px;
                border: 1px solid #555555;
                font-weight: bold;
                color: #ffffff;
            }
            QLineEdit {
                background-color: #404040;
                border: 1px solid #555555;
                padding: 6px;
                border-radius: 4px;
                color: #ffffff;
            }
            QPushButton {
                background-color: #555555;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #666666;
            }
        """)

        tasks_layout.addWidget(self.recent_tasks_table)
        parent_layout.addWidget(tasks_frame)

    def create_active_devices_section(self, parent_layout):
        """Create active devices section with proper visibility"""
        # Section frame
        devices_frame = QFrame()
        devices_frame.setStyleSheet("""
            QFrame {
                background-color: #353535;
                border: 1px solid #555555;
                border-radius: 6px;
                padding: 15px;
            }
        """)
        devices_layout = QVBoxLayout(devices_frame)
        devices_layout.setSpacing(15)

        # Section header
        header_layout = QHBoxLayout()

        devices_title = QLabel("Active Devices")
        devices_title.setFont(QFont("Arial", 16, QFont.Bold))
        devices_title.setStyleSheet("color: #ffffff; margin: 0;")
        header_layout.addWidget(devices_title)

        header_layout.addStretch()

        # View all button
        view_all_btn = QPushButton("Manage Devices")
        view_all_btn.setStyleSheet("""
            QPushButton {
                background-color: #10B981;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #059669;
            }
        """)
        header_layout.addWidget(view_all_btn)

        devices_layout.addLayout(header_layout)

        # Devices table with proper styling
        self.active_devices_table = DataTableWidget([
            "Device ID", "Device Name", "Type", "Status", "Battery", "Location"
        ], searchable=True, selectable=True)

        # Set fixed height for table
        self.active_devices_table.setMinimumHeight(250)
        self.active_devices_table.setMaximumHeight(300)

        # Apply same styling as tasks table
        self.active_devices_table.setStyleSheet("""
            QWidget {
                background-color: #404040;
                color: #ffffff;
            }
            QTableWidget {
                background-color: #404040;
                alternate-background-color: #454545;
                gridline-color: #555555;
                color: #ffffff;
                border: 1px solid #555555;
                border-radius: 4px;
            }
            QTableWidget::item {
                padding: 8px;
                border: none;
                color: #ffffff;
            }
            QTableWidget::item:selected {
                background-color: #10B981;
                color: #ffffff;
            }
            QHeaderView::section {
                background-color: #353535;
                padding: 10px;
                border: 1px solid #555555;
                font-weight: bold;
                color: #ffffff;
            }
            QLineEdit {
                background-color: #404040;
                border: 1px solid #555555;
                padding: 6px;
                border-radius: 4px;
                color: #ffffff;
            }
            QPushButton {
                background-color: #555555;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #666666;
            }
        """)

        devices_layout.addWidget(self.active_devices_table)
        parent_layout.addWidget(devices_frame)

    def create_refresh_button(self, parent_layout):
        """Create refresh button"""
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        refresh_btn = QPushButton("🔄 Refresh Dashboard")
        refresh_btn.setFixedHeight(40)
        refresh_btn.clicked.connect(self.refresh_data)
        refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #ff6b35;
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 14px;
                font-weight: bold;
                padding: 0 30px;
            }
            QPushButton:hover {
                background-color: #e55a2b;
            }
        """)
        button_layout.addWidget(refresh_btn)
        button_layout.addStretch()

        parent_layout.addLayout(button_layout)

    def setup_timer(self):
        """Setup refresh timer"""
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_data)
        self.refresh_timer.start(30000)  # Refresh every 30 seconds

    def refresh_data(self):
        """Refresh all dashboard data"""
        self.load_device_status()
        self.load_task_status()
        self.load_recent_tasks()
        self.load_active_devices()

    def load_device_status(self):
        """Load device status from CSV and API"""
        try:
            # Try API first
            if self.api_client.is_authenticated():
                response = self.devices_api.get_status_summary()
                if 'error' not in response:
                    self.update_device_cards(response)
                    return

            # Fallback to CSV
            devices = self.csv_handler.read_csv('devices')
            status_counts = {
                'working': 0,
                'charging': 0,
                'issues': 0,
                'total': len(devices)
            }

            for device in devices:
                status = device.get('status', '').lower()
                if status in status_counts:
                    status_counts[status] += 1

            self.update_device_cards(status_counts)

        except Exception as e:
            self.logger.error(f"Error loading device status: {e}")
            # Set default values on error
            self.update_device_cards({'working': 0, 'charging': 0, 'issues': 0, 'total': 0})

    def update_device_cards(self, data):
        """Update device status cards"""
        self.device_working_card.update_value(str(data.get('working', 0)))
        self.device_charging_card.update_value(str(data.get('charging', 0)))
        self.device_issues_card.update_value(str(data.get('issues', 0)))
        self.device_total_card.update_value(str(data.get('total', 0)))

    def load_task_status(self):
        """Load task status from CSV and API"""
        try:
            # Try API first
            if self.api_client.is_authenticated():
                response = self.tasks_api.get_task_summary()
                if 'error' not in response:
                    self.update_task_cards(response)
                    return

            # Fallback to CSV
            tasks = self.csv_handler.read_csv('tasks')
            status_counts = {
                'pending': 0,
                'running': 0,
                'completed': 0,
                'failed': 0
            }

            for task in tasks:
                status = task.get('status', '').lower()
                if status in status_counts:
                    status_counts[status] += 1

            self.update_task_cards(status_counts)

        except Exception as e:
            self.logger.error(f"Error loading task status: {e}")
            # Set default values on error
            self.update_task_cards({'pending': 0, 'running': 0, 'completed': 0, 'failed': 0})

    def update_task_cards(self, data):
        """Update task status cards"""
        self.task_pending_card.update_value(str(data.get('pending', 0)))
        self.task_running_card.update_value(str(data.get('running', 0)))
        self.task_completed_card.update_value(str(data.get('completed', 0)))
        self.task_failed_card.update_value(str(data.get('failed', 0)))

    def load_recent_tasks(self):
        """Load recent tasks data"""
        try:
            # Try API first
            if self.api_client.is_authenticated():
                response = self.tasks_api.list_tasks({'limit': 10})
                if 'error' not in response:
                    tasks_data = response.get('results', response) if isinstance(response, dict) else response
                    self.populate_recent_tasks_table(tasks_data)
                    return

            # Fallback to CSV
            tasks = self.csv_handler.read_csv('tasks')
            # Sort by created_at descending and take first 10
            tasks = sorted(tasks, key=lambda x: x.get('created_at', ''), reverse=True)[:10]
            self.populate_recent_tasks_table(tasks)

        except Exception as e:
            self.logger.error(f"Error loading recent tasks: {e}")
            self.populate_recent_tasks_table([])

    def populate_recent_tasks_table(self, tasks):
        """Populate recent tasks table"""
        self.recent_tasks_table.clear_data()

        for task in tasks:
            assigned_device = task.get('assigned_device', {})
            if isinstance(assigned_device, dict):
                device_name = assigned_device.get('device_name', 'Unassigned')
            else:
                device_name = str(task.get('assigned_device_id', 'Unassigned'))

            row_data = [
                task.get('task_id', ''),
                task.get('task_name', ''),
                task.get('task_type', '').title(),
                task.get('status', '').title(),
                device_name,
                task.get('created_at', '')[:16] if task.get('created_at') else ''  # Date and time
            ]
            self.recent_tasks_table.add_row(row_data)

    def load_active_devices(self):
        """Load active devices data"""
        try:
            # Try API first
            if self.api_client.is_authenticated():
                response = self.devices_api.list_devices({'status': 'working'})
                if 'error' not in response:
                    devices_data = response.get('results', response) if isinstance(response, dict) else response
                    self.populate_active_devices_table(devices_data)
                    return

            # Fallback to CSV
            devices = self.csv_handler.read_csv('devices')
            active_devices = [d for d in devices if d.get('status', '').lower() == 'working']
            self.populate_active_devices_table(active_devices)

        except Exception as e:
            self.logger.error(f"Error loading active devices: {e}")
            self.populate_active_devices_table([])

    def populate_active_devices_table(self, devices):
        """Populate active devices table"""
        self.active_devices_table.clear_data()

        for device in devices:
            battery_level = device.get('battery_level', 0)
            battery_text = f"{battery_level}%" if battery_level is not None else "N/A"

            row_data = [
                device.get('device_id', ''),
                device.get('device_name', ''),
                device.get('device_type', ''),
                device.get('status', '').title(),
                battery_text,
                device.get('location', '')
            ]
            self.active_devices_table.add_row(row_data)