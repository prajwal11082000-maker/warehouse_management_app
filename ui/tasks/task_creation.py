from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
                             QLineEdit, QComboBox, QTextEdit, QSpinBox, QPushButton,
                             QLabel, QFrame, QMessageBox, QScrollArea, QGroupBox,
                             QCheckBox, QDateTimeEdit, QProgressBar, QTabWidget,
                             QListWidget, QListWidgetItem, QSplitter, QFileDialog)
from PyQt5.QtCore import Qt, pyqtSignal, QDateTime, QTimer
from PyQt5.QtGui import QFont, QPixmap, QIcon
from datetime import datetime, timedelta
import os
import csv

from api.client import APIClient
from api.tasks import TasksAPI
from data_manager.csv_handler import CSVHandler
from config.constants import TASK_TYPES
from utils.logger import setup_logger
from data_manager.device_data_handler import DeviceDataHandler


class TaskCreationWidget(QWidget):
    task_created = pyqtSignal(dict)

    def __init__(self, api_client: APIClient, csv_handler: CSVHandler):
        super().__init__()
        self.api_client = api_client
        self.csv_handler = csv_handler
        self.tasks_api = TasksAPI(api_client)
        self.logger = setup_logger('task_creation')
        self.device_data_handler = DeviceDataHandler()

        self.setup_ui()
        self.load_data()

    def setup_ui(self):
        """Setup task creation UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Task statistics header
        #self.create_stats_header(layout)

        # Main content with tabs
        self.create_main_content(layout)

        # Action buttons
        self.create_action_buttons(layout)

    '''
    def create_stats_header(self, parent_layout):
        """Create task statistics header"""
        stats_frame = QFrame()
        stats_frame.setStyleSheet("""
            QFrame {
                background-color: #353535;
                border: 1px solid #555555;
                border-radius: 6px;
                padding: 15px;
            }
        """)
        stats_layout = QHBoxLayout(stats_frame)
        stats_layout.setSpacing(20)

        # Active tasks label
        self.active_tasks_label = QLabel("Active Tasks: 0")
        self.active_tasks_label.setStyleSheet("""
            QLabel {
                color: #10B981;
                font-size: 14px;
                font-weight: bold;
            }
        """)
        stats_layout.addWidget(self.active_tasks_label)

        # Pending tasks label
        self.pending_tasks_label = QLabel("Pending: 0")
        self.pending_tasks_label.setStyleSheet("""
            QLabel {
                color: #F59E0B;
                font-size: 14px;
                font-weight: bold;
            }
        """)
        stats_layout.addWidget(self.pending_tasks_label)

        stats_layout.addStretch()
        parent_layout.addWidget(stats_frame)
        '''


    def create_main_content(self, parent_layout):
        """Create main content with tabs"""
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #555555;
                background-color: #2b2b2b;
            }
            QTabBar::tab {
                background-color: #404040;
                color: #ffffff;
                padding: 10px 20px;
                margin-right: 2px;
                border: 1px solid #555555;
                border-bottom: none;
                border-radius: 6px 6px 0 0;
            }
            QTabBar::tab:selected {
                background-color: #ff6b35;
                color: #ffffff;
            }
            QTabBar::tab:hover:!selected {
                background-color: #4a4a4a;
            }
        """)

        # Tab 1: Manual Task Creation
        self.manual_tab = self.create_manual_creation_tab()
        self.tab_widget.addTab(self.manual_tab, "✏️ Manual Creation")

        parent_layout.addWidget(self.tab_widget)

    def create_manual_creation_tab(self):
        """Create manual task creation tab"""
        tab_widget = QWidget()
        layout = QHBoxLayout(tab_widget)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(25)

        # Left panel - Task form with scroll
        left_scroll = QScrollArea()
        left_scroll.setWidgetResizable(True)
        left_scroll.setFrameStyle(QFrame.NoFrame)
        left_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        left_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        left_panel = self.create_task_form_panel()
        left_scroll.setWidget(left_panel)
        layout.addWidget(left_scroll, 2)

        # Right panel - Assignment and preview with scroll
        right_scroll = QScrollArea()
        right_scroll.setWidgetResizable(True)
        right_scroll.setFrameStyle(QFrame.NoFrame)
        right_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        right_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        right_panel = self.create_assignment_panel()
        right_scroll.setWidget(right_panel)
        layout.addWidget(right_scroll, 1)

        return tab_widget

    def create_task_form_panel(self):
        """Create task form panel"""
        panel = QFrame()
        panel.setStyleSheet("""
            QFrame {
                background-color: #353535;
                border: 1px solid #555555;
                border-radius: 6px;
                padding: 25px;
            }
        """)
        layout = QVBoxLayout(panel)
        layout.setSpacing(25)

        # Basic Information Section
        basic_section = self.create_basic_info_section()
        layout.addWidget(basic_section)

        # Add some bottom spacing
        layout.addStretch()

        return panel

    def create_basic_info_section(self):
        """Create basic information section"""
        section = QGroupBox("Basic Information")
        section.setStyleSheet(self.get_groupbox_style())
        layout = QFormLayout(section)
        layout.setSpacing(15)
        layout.setVerticalSpacing(15)

        # Task Name
        self.task_name_input = QLineEdit()
        self.task_name_input.setPlaceholderText("Enter descriptive task name")
        self.task_name_input.setMinimumHeight(35)
        self.apply_input_style(self.task_name_input)
        layout.addRow("Task Name *:", self.task_name_input)

        # Task Type
        self.task_type_combo = QComboBox()
        self.task_type_combo.setMinimumHeight(35)
        # Add default option
        self.task_type_combo.addItem("Select Task Type", "")
        # Add required task types
        self.task_type_combo.addItem("Picking", "picking")
        self.task_type_combo.addItem("Auditing", "auditing")
        self.task_type_combo.addItem("Storing", "storing")
        self.task_type_combo.currentTextChanged.connect(self.on_task_type_changed)
        self.apply_combo_style(self.task_type_combo)
        layout.addRow("Task Type *:", self.task_type_combo)

        # Picking-specific section (initially hidden)
        self.picking_section = self.create_picking_section()
        self.picking_section.setVisible(False)
        layout.addRow(self.picking_section)
        
        # Storing-specific section (initially hidden)
        self.storing_section = self.create_storing_section()
        self.storing_section.setVisible(False)
        layout.addRow(self.storing_section)
        
        # Auditing-specific section (initially hidden)
        self.auditing_section = self.create_auditing_section()
        self.auditing_section.setVisible(False)
        layout.addRow(self.auditing_section)

        return section


    def create_picking_section(self):
        """Create picking-specific section with map, zone, file upload, and barcode fields"""
        section = QGroupBox("Picking Details")
        section.setStyleSheet(self.get_groupbox_style())
        layout = QFormLayout(section)
        layout.setSpacing(15)
        layout.setVerticalSpacing(15)

        # Pickup Map dropdown
        self.pickup_map_combo = QComboBox()
        self.pickup_map_combo.setMinimumHeight(35)
        self.pickup_map_combo.addItem("Select Pickup Map", "")
        self.apply_combo_style(self.pickup_map_combo)
        layout.addRow("Pickup Map *:", self.pickup_map_combo)

        # From Zone dropdown
        self.from_zone_combo = QComboBox()
        self.from_zone_combo.setMinimumHeight(35)
        self.from_zone_combo.addItem("Select From Zone", "")
        self.apply_combo_style(self.from_zone_combo)
        layout.addRow("From Zone *:", self.from_zone_combo)

        # To Zone dropdown
        self.to_zone_combo = QComboBox()
        self.to_zone_combo.setMinimumHeight(35)
        self.to_zone_combo.addItem("Select To Zone", "")
        self.apply_combo_style(self.to_zone_combo)
        layout.addRow("To Zone *:", self.to_zone_combo)

        # Drop Stop list
        self.drop_stop_list = QListWidget()
        self.drop_stop_list.setMinimumHeight(100)
        self.drop_stop_list.setSelectionMode(QListWidget.MultiSelection)
        self.drop_stop_list.setStyleSheet("""
            QListWidget {
                background-color: #404040;
                border: 1px solid #555555;
                padding: 5px;
                border-radius: 4px;
                color: #ffffff;
                font-size: 13px;
                min-height: 15px;
            }
            QListWidget::item {
                padding: 4px;
            }
            QListWidget::item:selected {
                background-color: #ff6b35;
                color: white;
            }
        """)
        layout.addRow("Drop Stop:", self.drop_stop_list)

        # Upload CSV file button
        upload_layout = QHBoxLayout()
        self.upload_csv_button = QPushButton("📁 Upload CSV File")
        self.upload_csv_button.clicked.connect(self.upload_csv_file)
        self.upload_csv_button.setStyleSheet("""
            QPushButton {
                background-color: #3B82F6;
                color: white;
                border: none;
                padding: 10px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2563EB;
            }
        """)
        
        self.uploaded_file_label = QLabel("No file uploaded")
        self.uploaded_file_label.setStyleSheet("color: #cccccc; font-size: 11px; padding: 5px;")
        
        upload_layout.addWidget(self.upload_csv_button)
        upload_layout.addWidget(self.uploaded_file_label)
        layout.addRow("Upload File:", upload_layout)

        # Barcode input
        self.barcode_input = QLineEdit()
        self.barcode_input.setPlaceholderText("Enter barcode")
        self.barcode_input.setMinimumHeight(35)
        self.apply_input_style(self.barcode_input)
        layout.addRow("Barcode:", self.barcode_input)

        return section

    def create_auditing_section(self):
        """Create auditing-specific section with map, file upload, and barcode fields"""
        section = QGroupBox("Auditing Details")
        section.setStyleSheet(self.get_groupbox_style())
        layout = QFormLayout(section)
        layout.setSpacing(15)
        layout.setVerticalSpacing(15)

        # Auditing Map dropdown
        self.auditing_map_combo = QComboBox()
        self.auditing_map_combo.setMinimumHeight(35)
        self.auditing_map_combo.addItem("Select Auditing Map", "")
        self.apply_combo_style(self.auditing_map_combo)
        layout.addRow("Auditing Map *:", self.auditing_map_combo)

        # Upload CSV file button
        upload_layout = QHBoxLayout()
        self.auditing_upload_csv_button = QPushButton("📁 Upload CSV File")
        self.auditing_upload_csv_button.clicked.connect(self.upload_csv_file)
        self.auditing_upload_csv_button.setStyleSheet("""
            QPushButton {
                background-color: #3B82F6;
                color: white;
                border: none;
                padding: 10px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2563EB;
            }
        """)
        
        self.auditing_uploaded_file_label = QLabel("No file uploaded")
        self.auditing_uploaded_file_label.setStyleSheet("color: #cccccc; font-size: 11px; padding: 5px;")
        
        upload_layout.addWidget(self.auditing_upload_csv_button)
        upload_layout.addWidget(self.auditing_uploaded_file_label)
        layout.addRow("Upload File:", upload_layout)

        # Barcode input
        self.auditing_barcode_input = QLineEdit()
        self.auditing_barcode_input.setPlaceholderText("Enter barcode")
        self.auditing_barcode_input.setMinimumHeight(35)
        self.apply_input_style(self.auditing_barcode_input)
        layout.addRow("Barcode:", self.auditing_barcode_input)

        return section

    def create_storing_section(self):
        """Create storing-specific section with map, zone, file upload, and barcode fields"""
        section = QGroupBox("Storing Details")
        section.setStyleSheet(self.get_groupbox_style())
        layout = QFormLayout(section)
        layout.setSpacing(15)
        layout.setVerticalSpacing(15)

        # Storing Map dropdown
        self.storing_map_combo = QComboBox()
        self.storing_map_combo.setMinimumHeight(35)
        self.storing_map_combo.addItem("Select Storing Map", "")
        self.apply_combo_style(self.storing_map_combo)
        layout.addRow("Storing Map *:", self.storing_map_combo)

        # From Zone dropdown for storing
        self.storing_from_zone_combo = QComboBox()
        self.storing_from_zone_combo.setMinimumHeight(35)
        self.storing_from_zone_combo.addItem("Select From Zone", "")
        self.apply_combo_style(self.storing_from_zone_combo)
        layout.addRow("From Zone *:", self.storing_from_zone_combo)

        # To Zone dropdown for storing
        self.storing_to_zone_combo = QComboBox()
        self.storing_to_zone_combo.setMinimumHeight(35)
        self.storing_to_zone_combo.addItem("Select To Zone", "")
        self.apply_combo_style(self.storing_to_zone_combo)
        layout.addRow("To Zone *:", self.storing_to_zone_combo)

        # Pickup Stop list
        self.pickup_stop_list = QListWidget()
        self.pickup_stop_list.setMinimumHeight(100)
        self.pickup_stop_list.setSelectionMode(QListWidget.MultiSelection)
        self.pickup_stop_list.setStyleSheet("""
            QListWidget {
                background-color: #404040;
                border: 1px solid #555555;
                padding: 5px;
                border-radius: 4px;
                color: #ffffff;
                font-size: 13px;
                min-height: 15px;
            }
            QListWidget::item {
                padding: 4px;
            }
            QListWidget::item:selected {
                background-color: #ff6b35;
                color: white;
            }
        """)
        layout.addRow("Pickup Stop:", self.pickup_stop_list)

        # Upload CSV file button
        upload_layout = QHBoxLayout()
        self.storing_upload_csv_button = QPushButton("📁 Upload CSV File")
        self.storing_upload_csv_button.clicked.connect(self.upload_csv_file)
        self.storing_upload_csv_button.setStyleSheet("""
            QPushButton {
                background-color: #3B82F6;
                color: white;
                border: none;
                padding: 10px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2563EB;
            }
        """)
        
        self.storing_uploaded_file_label = QLabel("No file uploaded")
        self.storing_uploaded_file_label.setStyleSheet("color: #cccccc; font-size: 11px; padding: 5px;")
        
        upload_layout.addWidget(self.storing_upload_csv_button)
        upload_layout.addWidget(self.storing_uploaded_file_label)
        layout.addRow("Upload File:", upload_layout)

        # Barcode input
        self.storing_barcode_input = QLineEdit()
        self.storing_barcode_input.setPlaceholderText("Enter barcode")
        self.storing_barcode_input.setMinimumHeight(35)
        self.apply_input_style(self.storing_barcode_input)
        layout.addRow("Barcode:", self.storing_barcode_input)

        return section



    def create_assignment_panel(self):
        """Create assignment panel"""
        panel = QFrame()
        panel.setStyleSheet("""
            QFrame {
                background-color: #353535;
                border: 1px solid #555555;
                border-radius: 6px;
                padding: 25px;
            }
        """)
        layout = QVBoxLayout(panel)
        layout.setSpacing(20)

        # Assignment Section
        assignment_section = QGroupBox("Assignment")
        assignment_section.setStyleSheet(self.get_groupbox_style())
        assignment_layout = QFormLayout(assignment_section)
        assignment_layout.setSpacing(15)
        assignment_layout.setVerticalSpacing(15)

        # Device Assignment
        self.device_combo = QComboBox()
        self.device_combo.setMinimumHeight(35)
        self.device_combo.addItem("Select Device", "")  # Changed text to indicate selection is required
        self.device_combo.currentTextChanged.connect(self.on_device_changed)
        self.apply_combo_style(self.device_combo)
        assignment_layout.addRow("Assign Device *:", self.device_combo)  # Added asterisk to indicate required

        # Device Status Label
        self.device_status_label = QLabel("Auto-assignment enabled")
        self.device_status_label.setStyleSheet("""
            QLabel {
                color: #cccccc;
                font-size: 11px;
                padding: 5px;
                background-color: #404040;
                border: 1px solid #555555;
                border-radius: 4px;
            }
        """)
        self.device_status_label.setWordWrap(True)
        self.device_status_label.setMinimumHeight(60)
        assignment_layout.addRow("Device Status:", self.device_status_label)

        # User Assignment
        self.user_combo = QComboBox()
        self.user_combo.setMinimumHeight(35)
        self.user_combo.addItem("Auto-assign Available User", "")
        self.apply_combo_style(self.user_combo)
        assignment_layout.addRow("Assign User:", self.user_combo)

        layout.addWidget(assignment_section)

        layout.addStretch()

        return panel



    def create_action_buttons(self, parent_layout):
        """Create action buttons"""
        action_layout = QHBoxLayout()

        # Clear form button
        clear_btn = QPushButton("🗑️ Clear Form")
        clear_btn.clicked.connect(self.clear_form)
        self.apply_button_style(clear_btn)
        action_layout.addWidget(clear_btn)


        action_layout.addStretch()

        # Create task button
        self.create_btn = QPushButton("➕ Create Task")
        self.create_btn.clicked.connect(self.create_task)
        self.create_btn.setStyleSheet("""
            QPushButton {
                background-color: #ff6b35;
                color: white;
                border: none;
                padding: 12px 24px;
                border-radius: 6px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #e55a2b;
            }
        """)
        action_layout.addWidget(self.create_btn)

        parent_layout.addLayout(action_layout)

    def get_groupbox_style(self):
        """Get groupbox styling"""
        return """
            QGroupBox {
                color: #ffffff;
                border: 1px solid #666666;
                border-radius: 6px;
                padding-top: 20px;
                margin: 15px 0;
                font-weight: bold;
                font-size: 14px;
            }
            QGroupBox::title {
                color: #ff6b35;
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 8px 0 8px;
                font-size: 14px;
            }
        """

    def apply_input_style(self, widget):
        """Apply input styling"""
        widget.setStyleSheet("""
            QLineEdit, QSpinBox, QDateTimeEdit, QDoubleSpinBox {
                background-color: #404040;
                border: 1px solid #555555;
                padding: 10px;
                border-radius: 4px;
                color: #ffffff;
                font-size: 13px;
                min-height: 15px;
            }
            QLineEdit:focus, QSpinBox:focus, QDateTimeEdit:focus, QDoubleSpinBox:focus {
                border: 2px solid #ff6b35;
            }
        """)

    def apply_combo_style(self, combo):
        """Apply combobox styling"""
        combo.setStyleSheet("""
            QComboBox {
                background-color: #404040;
                border: 1px solid #555555;
                padding: 10px;
                padding-right: 35px;
                border-radius: 4px;
                color: #ffffff;
                min-width: 150px;
                font-size: 13px;
                min-height: 15px;
            }
            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 30px;
                border: none;
                border-left: 1px solid #555555;
                border-radius: 0 4px 4px 0;
                background: #ff6b35;
            }
            QComboBox::down-arrow {
                image: none;
                text: "˅";
                color: #ffffff;
                font-size: 20px;
                font-weight: bold;
                right: 8px;
                top: 1px;
            }
            QComboBox QAbstractItemView {
                background-color: #404040;
                color: #ffffff;
                selection-background-color: #ff6b35;
                padding: 5px;
                border: 1px solid #555555;
                border-radius: 4px;
            }
        """)

    def apply_button_style(self, button):
        """Apply button styling"""
        button.setStyleSheet("""
            QPushButton {
                background-color: #555555;
                color: white;
                border: none;
                padding: 10px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #666666;
            }
        """)

    def load_data(self):
        """Load devices and users for assignment"""
        self.load_devices()
        self.load_users()
        self.update_task_stats()

    def load_devices(self):
        """Load available devices"""
        try:
            devices = self.csv_handler.read_csv('devices')

            self.device_combo.clear()
            self.device_combo.addItem("Auto-assign Available Device", "")

            for device in devices:
                status = device.get('status', '').lower()
                battery = device.get('battery_level', '')

                device_text = f"{device.get('device_name', '')} ({device.get('device_id', '')})"

                if status == 'working':
                    if battery:
                        device_text += f" - {battery}% ⚡"
                    self.device_combo.addItem(f"✅ {device_text}", device.get('id'))
                elif status == 'charging':
                    device_text += " - Charging 🔋"
                    self.device_combo.addItem(f"🔋 {device_text}", device.get('id'))
                else:
                    device_text += f" - {status.title()}"
                    self.device_combo.addItem(f"❌ {device_text}", device.get('id'))

        except Exception as e:
            self.logger.error(f"Error loading devices: {e}")

    def load_users(self):
        """Load available users"""
        try:
            users = self.csv_handler.read_csv('users')

            self.user_combo.clear()
            self.user_combo.addItem("Auto-assign Available User", "")

            for user in users:
                is_active = user.get('is_active', 'true').lower() == 'true'

                user_text = user.get('username', '')
                employee_id = user.get('employee_id', '')
                if employee_id:
                    user_text += f" ({employee_id})"

                if is_active:
                    self.user_combo.addItem(f"✅ {user_text.strip()}", user.get('id'))
                else:
                    self.user_combo.addItem(f"❌ {user_text.strip()} - Inactive", user.get('id'))

        except Exception as e:
            self.logger.error(f"Error loading users: {e}")

    def update_task_stats(self):
        """Update task statistics"""
        try:
            tasks = self.csv_handler.read_csv('tasks')

            active_count = len([t for t in tasks if t.get('status', '').lower() == 'running'])
            pending_count = len([t for t in tasks if t.get('status', '').lower() == 'pending'])

            # Safely update labels if they exist
            if hasattr(self, 'active_tasks_label') and self.active_tasks_label:
                self.active_tasks_label.setText(f"Active Tasks: {active_count}")
            if hasattr(self, 'pending_tasks_label') and self.pending_tasks_label:
                self.pending_tasks_label.setText(f"Pending: {pending_count}")

        except Exception as e:
            self.logger.error(f"Error updating stats: {e}")

    def on_task_type_changed(self):
        """Handle task type change"""
        # Update suggested locations based on task type
        task_type = self.task_type_combo.currentData()

        # Show/hide sections based on task type
        if hasattr(self, 'picking_section') and hasattr(self, 'storing_section') and hasattr(self, 'auditing_section'):
            # Hide all sections first
            self.picking_section.setVisible(False)
            self.storing_section.setVisible(False)
            self.auditing_section.setVisible(False)
            
            # Show the appropriate section based on task type
            if task_type == 'picking':
                self.picking_section.setVisible(True)
                self.populate_pickup_maps()
            elif task_type == 'storing':
                self.storing_section.setVisible(True)
                self.populate_pickup_maps_for_storing()
            elif task_type == 'auditing':
                self.auditing_section.setVisible(True)
                self.populate_pickup_maps_for_auditing()

    def on_device_changed(self):
        """Handle device selection change"""
        device_id = self.device_combo.currentData()
        if device_id:
            # Find device info
            devices = self.csv_handler.read_csv('devices')
            device = next((d for d in devices if str(d.get('id')) == str(device_id)), None)

            if device:
                status = device.get('status', 'unknown').title()
                battery = device.get('battery_level', 'N/A')
                location = device.get('current_location', 'Unknown')

                info_text = f"Status: {status}\nBattery: {battery}%\nLocation: {location}"
                self.device_status_label.setText(info_text)
            else:
                self.device_status_label.setText("Device information not available")
        else:
            self.device_status_label.setText("Please select a device")

    def clear_form(self):
        """Clear all form fields"""
        self.task_name_input.clear()
        self.task_type_combo.setCurrentIndex(0)
        self.device_combo.setCurrentIndex(0)
        self.user_combo.setCurrentIndex(0)



    def create_task(self):
        """Create new task"""
        if not self.validate_form():
            return

        try:
            task_data = self.collect_task_data()
            self.save_task(task_data)
        except Exception as e:
            self.logger.error(f"Error creating task: {e}")
            QMessageBox.critical(self, "Error", f"Failed to create task: {e}")


    def check_device_availability(self, device_id):
        """Check if device is available (not running another task)"""
        if not device_id:
            return True
        
        tasks = self.csv_handler.read_csv('tasks')
        device_tasks = [t for t in tasks if (
            t.get('assigned_device_id') == str(device_id) and
            t.get('status', '').lower() == 'running'
        )]
        
        return len(device_tasks) == 0

    def validate_form(self):
        """Validate form inputs"""
        if not self.task_name_input.text().strip():
            QMessageBox.warning(self, "Validation Error", "Task name is required")
            self.task_name_input.setFocus()
            return False

        if not self.task_type_combo.currentData():
            QMessageBox.warning(self, "Validation Error", "Task type is required")
            self.task_type_combo.setFocus()
            return False

        if not self.device_combo.currentData():
            QMessageBox.warning(self, "Validation Error", "Device assignment is required")
            self.device_combo.setFocus()
            return False
            
        # Check if selected device is available
        device_id = self.device_combo.currentData()
        if not self.check_device_availability(device_id):
            QMessageBox.warning(
                self,
                "Device Busy",
                "The selected device is currently running another task. "
                "Please wait for the device to complete its current task or select a different device."
            )
            self.device_combo.setFocus()
            return False

        # Task type specific validations
        task_type = self.task_type_combo.currentData()
        if task_type == 'picking':
            if not self.pickup_map_combo.currentData():
                QMessageBox.warning(self, "Validation Error", "Pickup map is required")
                self.pickup_map_combo.setFocus()
                return False
            if not self.from_zone_combo.currentData():
                QMessageBox.warning(self, "Validation Error", "From zone is required")
                self.from_zone_combo.setFocus()
                return False
            if not self.to_zone_combo.currentData():
                QMessageBox.warning(self, "Validation Error", "To zone is required")
                self.to_zone_combo.setFocus()
                return False

        elif task_type == 'storing':
            if not self.storing_map_combo.currentData():
                QMessageBox.warning(self, "Validation Error", "Storing map is required")
                self.storing_map_combo.setFocus()
                return False
            if not self.storing_from_zone_combo.currentData():
                QMessageBox.warning(self, "Validation Error", "From zone is required")
                self.storing_from_zone_combo.setFocus()
                return False
            if not self.storing_to_zone_combo.currentData():
                QMessageBox.warning(self, "Validation Error", "To zone is required")
                self.storing_to_zone_combo.setFocus()
                return False

        elif task_type == 'auditing':
            if not self.auditing_map_combo.currentData():
                QMessageBox.warning(self, "Validation Error", "Auditing map is required")
                self.auditing_map_combo.setFocus()
                return False

        return True

    def collect_task_data(self):
        """Collect task data from form"""
        current_time = datetime.now().isoformat()

        # Generate task ID automatically
        task_id = f"TASK{self.csv_handler.get_next_id('tasks'):04d}"

        task_data = {
            'id': '',  # Will be auto-generated by the CSV handler
            'task_id': task_id,
            'task_name': self.task_name_input.text().strip(),
            'task_type': self.task_type_combo.currentData(),
            'status': 'pending',
            'assigned_device_id': self.device_combo.currentData() or '',
            'assigned_user_id': self.user_combo.currentData() or '',
            'description': self.description_input.text().strip() if hasattr(self, 'description_input') else '',
            'estimated_duration': '',  # We can calculate this based on zones/path later
            'actual_duration': '',
            'created_at': current_time,
            'started_at': '',
            'completed_at': '',
            'map_id': '',  # Will be set based on task type
            'zone_ids': '',  # Will be set based on task type
            'stop_ids': '',  # Will be set based on task type
            'task_details': {}  # Will be filled based on task type
        }

        # Add task-type specific data and consolidate map/zone/stop information
        task_type = self.task_type_combo.currentData()
        
        # Initialize common fields
        task_data['map_id'] = ''
        task_data['zone_ids'] = ''
        task_data['stop_ids'] = ''
        task_data['task_details'] = {}  # Dictionary to store type-specific details
        
        if task_type == 'auditing':
            # Add auditing-specific data
            if hasattr(self, 'auditing_map_combo'):
                map_id = self.auditing_map_combo.currentData() or ''
                task_data['map_id'] = map_id
                task_data['task_details']['auditing_map_id'] = map_id
                task_data['task_details']['auditing_map_name'] = self.auditing_map_combo.currentText() or ''
            if hasattr(self, 'auditing_barcode_input'):
                task_data['task_details']['barcode'] = self.auditing_barcode_input.text().strip()
            if hasattr(self, 'uploaded_csv_file'):
                task_data['task_details']['csv_file_path'] = self.uploaded_csv_file
                
        elif task_type == 'picking':
            # Add picking-specific data
            if hasattr(self, 'pickup_map_combo'):
                map_id = self.pickup_map_combo.currentData() or ''
                task_data['map_id'] = map_id
                task_data['task_details']['pickup_map_id'] = map_id
                task_data['task_details']['pickup_map_name'] = self.pickup_map_combo.currentText() or ''
            # Handle from and to zones
            if hasattr(self, 'from_zone_combo') and hasattr(self, 'to_zone_combo'):
                from_zone = self.from_zone_combo.currentData() or ''
                to_zone = self.to_zone_combo.currentData() or ''
                
                # Find all zones in the path
                zones = self.csv_handler.read_csv('zones')
                selected_map_id = self.pickup_map_combo.currentData()
                
                # Get the complete path and all zone IDs
                zone_path, zone_ids = self.find_path_between_zones(
                    selected_map_id, from_zone, to_zone, zones
                )
                
                if zone_ids:
                    task_data['zone_ids'] = ','.join(str(id) for id in zone_ids)
                    task_data['task_details']['from_zone'] = from_zone
                    task_data['task_details']['to_zone'] = to_zone
                    task_data['task_details']['zone_path'] = zone_path
                    task_data['task_details']['drop_zone_ids'] = zone_ids
                    task_data['task_details']['drop_zone_name'] = ' → '.join(zone_path)
            # Add selected stops if any
            if hasattr(self, 'drop_stop_list'):
                selected_stops = []
                selected_stop_names = []
                for i in range(self.drop_stop_list.count()):
                    item = self.drop_stop_list.item(i)
                    if item.isSelected():
                        stop_id = item.data(Qt.UserRole)
                        if stop_id:
                            selected_stops.append(stop_id)
                            selected_stop_names.append(item.text())
                task_data['stop_ids'] = ','.join(selected_stops) if selected_stops else ''
                task_data['task_details']['drop_stops'] = selected_stops
                task_data['task_details']['drop_stop_names'] = selected_stop_names
                
        elif task_type == 'storing':
            # Add storing-specific data
            if hasattr(self, 'storing_map_combo'):
                map_id = self.storing_map_combo.currentData() or ''
                task_data['map_id'] = map_id
                task_data['task_details']['storing_map_id'] = map_id
                task_data['task_details']['storing_map_name'] = self.storing_map_combo.currentText() or ''
            # Handle from and to zones for storing
            if hasattr(self, 'storing_from_zone_combo') and hasattr(self, 'storing_to_zone_combo'):
                from_zone = self.storing_from_zone_combo.currentData() or ''
                to_zone = self.storing_to_zone_combo.currentData() or ''
                
                # Find all zones in the path
                zones = self.csv_handler.read_csv('zones')
                selected_map_id = self.storing_map_combo.currentData()
                
                # Get the complete path and all zone IDs
                zone_path, zone_ids = self.find_path_between_zones(
                    selected_map_id, from_zone, to_zone, zones
                )
                
                if zone_ids:
                    task_data['zone_ids'] = ','.join(str(id) for id in zone_ids)
                    task_data['task_details']['from_zone'] = from_zone
                    task_data['task_details']['to_zone'] = to_zone
                    task_data['task_details']['zone_path'] = zone_path
                    task_data['task_details']['pickup_zone_ids'] = zone_ids
                    task_data['task_details']['pickup_zone_name'] = ' → '.join(zone_path)
            # Add selected stops if any
            if hasattr(self, 'pickup_stop_list'):
                selected_stops = []
                selected_stop_names = []
                for i in range(self.pickup_stop_list.count()):
                    item = self.pickup_stop_list.item(i)
                    if item.isSelected():
                        stop_id = item.data(Qt.UserRole)
                        if stop_id:
                            selected_stops.append(stop_id)
                            selected_stop_names.append(item.text())
                task_data['stop_ids'] = ','.join(selected_stops) if selected_stops else ''
                task_data['task_details']['pickup_stops'] = selected_stops
                task_data['task_details']['pickup_stop_names'] = selected_stop_names
        
        # Convert task_details to JSON string for storage
        import json
        task_data['task_details'] = json.dumps(task_data['task_details'])
        return task_data


    def save_task(self, task_data):
        """Save task to CSV or API"""
        if self.save_task_data(task_data):
            QMessageBox.information(
                self, "Success",
                f"Task '{task_data['task_name']}' created successfully!"
            )

            self.task_created.emit(task_data)
            self.clear_form()
            self.update_task_stats()

            # Switch to first tab after successful creation
            self.tab_widget.setCurrentIndex(0)

    def save_task_data(self, task_data):
        """Save task data (helper method)"""
        try:
            # Validate the data first
            validation_result = self.csv_handler.validate_csv_data('tasks', task_data)

            if not validation_result['valid']:
                error_msg = '\n'.join(validation_result['errors'])
                QMessageBox.critical(self, "Validation Error", f"Cannot create task:\n{error_msg}")
                return False

            # Use validated data
            task_data = validation_result['data']

            # Try API first
            if self.api_client.is_authenticated():
                response = self.tasks_api.create_task(task_data)
                if 'error' not in response:
                    # Update per-device task CSV on success
                    try:
                        self.device_data_handler.update_device_task_pending_by_task(
                            task_data.get('assigned_device_id'), task_data.get('task_id')
                        )
                    except Exception as e:
                        self.logger.warning(f"Could not update device task CSV after API create: {e}")
                    return True
                else:
                    self.logger.warning(f"API failed: {response['error']}, falling back to CSV")

            # Fallback to CSV
            if 'id' not in task_data or not task_data['id']:
                task_data['id'] = self.csv_handler.get_next_id('tasks')

            if self.csv_handler.append_to_csv('tasks', task_data):
                # Update per-device task CSV on CSV fallback success
                try:
                    self.device_data_handler.update_device_task_pending_by_task(
                        task_data.get('assigned_device_id'), task_data.get('task_id')
                    )
                except Exception as e:
                    self.logger.warning(f"Could not update device task CSV after local save: {e}")
                self.logger.info(f"Successfully created task: {task_data.get('task_id', task_data.get('id'))}")
                return True
            else:
                raise Exception("Failed to save to CSV")

        except Exception as e:
            self.logger.error(f"Error saving task: {e}")
            QMessageBox.critical(self, "Error", f"Failed to save task: {e}")
            return False

    def refresh_data(self):
        """Refresh data"""
        self.load_data()

    def populate_pickup_maps(self):
        """Populate pickup maps dropdown with existing maps"""
        self.pickup_map_combo.clear()
        self.pickup_map_combo.addItem("Select Pickup Map", "")
        
        # Load maps using the CSV handler
        try:
            maps = self.csv_handler.read_csv('maps')
            for map_data in maps:
                map_id = map_data.get('id', '')
                map_name = map_data.get('name', map_id)
                if map_id:
                    self.pickup_map_combo.addItem(map_name, map_id)
            
            # Connect map selection to zone population if not already connected
            try:
                self.pickup_map_combo.currentIndexChanged.disconnect(self.on_map_selection_changed)
            except TypeError:
                # Signal was not connected, that's fine
                pass
            self.pickup_map_combo.currentIndexChanged.connect(self.on_map_selection_changed)
        except Exception as e:
            self.logger.error(f"Error loading maps: {e}")

    def on_map_selection_changed(self, index):
        """Handle map selection change and populate zones"""
        # Clear both zone dropdowns
        self.from_zone_combo.clear()
        self.to_zone_combo.clear()
        self.from_zone_combo.addItem("Select From Zone", "")
        self.to_zone_combo.addItem("Select To Zone", "")
        
        if index > 0:  # If a map is selected (not the default "Select" option)
            selected_map_id = self.pickup_map_combo.currentData()
            
            # Load zones for the selected map using the CSV handler
            try:
                zones = self.csv_handler.read_csv('zones')
                # Get unique zone names
                unique_zones = set()
                for zone_data in zones:
                    map_id = zone_data.get('map_id', '')
                    if str(map_id) == str(selected_map_id):
                        from_zone = zone_data.get('from_zone', '')
                        to_zone = zone_data.get('to_zone', '')
                        if from_zone:
                            unique_zones.add(from_zone)
                        if to_zone:
                            unique_zones.add(to_zone)
                
                # Add unique zones to both dropdowns
                for zone in sorted(unique_zones):
                    self.from_zone_combo.addItem(zone, zone)
                    self.to_zone_combo.addItem(zone, zone)
            except Exception as e:
                self.logger.error(f"Error loading zones: {e}")
            
            # Connect zone selection to stop population if not already connected
            try:
                self.from_zone_combo.currentIndexChanged.disconnect(self.on_zone_selection_changed)
                self.to_zone_combo.currentIndexChanged.disconnect(self.on_zone_selection_changed)
            except TypeError:
                # Signal was not connected, that's fine
                pass
            self.from_zone_combo.currentIndexChanged.connect(self.on_zone_selection_changed)
            self.to_zone_combo.currentIndexChanged.connect(self.on_zone_selection_changed)
            
            # Clear the stops list when zones change
            self.drop_stop_list.clear()

    def on_zone_selection_changed(self, index):
        """Handle zone selection change and populate stops"""
        self.drop_stop_list.clear()
        
        if index > 0:  # If a zone is selected (not the default "Select" option)
            from_zone = self.from_zone_combo.currentData()
            to_zone = self.to_zone_combo.currentData()
            
            if not from_zone or not to_zone:
                return
                
            try:
                # Load zones and find the path between selected zones
                zones = self.csv_handler.read_csv('zones')
                selected_map_id = self.pickup_map_combo.currentData()
                
                # Use the same path-finding logic we have for storing
                zone_path, zone_ids = self.find_path_between_zones(
                    selected_map_id, from_zone, to_zone, zones
                )
                
                if zone_ids:
                    # Load stops for all zones in the path
                    stops = self.csv_handler.read_csv('stops')
                    added_stops = set()  # To prevent duplicate stops
                    
                    for zone_id in zone_ids:
                        for stop_data in stops:
                            zone_connection_id = stop_data.get('zone_connection_id', '')
                            stop_id = stop_data.get('stop_id', '')
                            
                            if (str(zone_connection_id) == str(zone_id) and 
                                stop_id and 
                                stop_id not in added_stops):
                                    
                                stop_name = stop_data.get('name', stop_id)
                                item = QListWidgetItem(f"{stop_name} ({stop_id})")
                                item.setData(Qt.UserRole, stop_id)
                                self.drop_stop_list.addItem(item)
                                added_stops.add(stop_id)
                                
                    # Log the path found
                    self.logger.info(f"Found path between zones: {' → '.join(zone_path)}")
                else:
                    self.logger.warning(f"No path found between zones {from_zone} and {to_zone}")
                    
            except Exception as e:
                self.logger.error(f"Error loading stops: {e}")

    def populate_pickup_maps_for_storing(self):
        """Populate pickup maps dropdown with existing maps for storing section"""
        self.storing_map_combo.clear()
        self.storing_map_combo.addItem("Select Storing Map", "")
        
        # Load maps using the CSV handler
        try:
            maps = self.csv_handler.read_csv('maps')
            for map_data in maps:
                map_id = map_data.get('id', '')
                map_name = map_data.get('name', map_id)
                if map_id:
                    self.storing_map_combo.addItem(map_name, map_id)
            
            # Connect map selection to zone population if not already connected
            try:
                self.storing_map_combo.currentIndexChanged.disconnect(self.on_storing_map_selected)
            except TypeError:
                # Signal was not connected, that's fine
                pass
            self.storing_map_combo.currentIndexChanged.connect(self.on_storing_map_selected)
        except Exception as e:
            self.logger.error(f"Error loading maps for storing section: {e}")

    def on_storing_map_selected(self, index):
        """Handle map selection change and populate zones for storing section"""
        # Clear both zone dropdowns
        self.storing_from_zone_combo.clear()
        self.storing_to_zone_combo.clear()
        self.storing_from_zone_combo.addItem("Select From Zone", "")
        self.storing_to_zone_combo.addItem("Select To Zone", "")

        if index > 0:  # If a map is selected (not the default "Select" option)
            selected_map_id = self.storing_map_combo.currentData()

            # Load zones for the selected map using the CSV handler
            try:
                zones = self.csv_handler.read_csv('zones')
                # Get unique zone names
                unique_zones = set()
                for zone_data in zones:
                    map_id = zone_data.get('map_id', '')
                    if str(map_id) == str(selected_map_id):
                        from_zone = zone_data.get('from_zone', '')
                        to_zone = zone_data.get('to_zone', '')
                        if from_zone:
                            unique_zones.add(from_zone)
                        if to_zone:
                            unique_zones.add(to_zone)

                # Add unique zones to both dropdowns
                for zone in sorted(unique_zones):
                    self.storing_from_zone_combo.addItem(zone, zone)
                    self.storing_to_zone_combo.addItem(zone, zone)
            except Exception as e:
                self.logger.error(f"Error loading zones: {e}")

            # Connect zone selections to stop population if not already connected
            try:
                self.storing_from_zone_combo.currentIndexChanged.disconnect(self.on_storing_zone_selected)
                self.storing_to_zone_combo.currentIndexChanged.disconnect(self.on_storing_zone_selected)
            except TypeError:
                # Signal was not connected, that's fine
                pass
            except Exception as e:
                self.logger.error(f"Error disconnecting signal: {e}")

            try:
                self.storing_from_zone_combo.currentIndexChanged.connect(self.on_storing_zone_selected)
                self.storing_to_zone_combo.currentIndexChanged.connect(self.on_storing_zone_selected)
            except Exception as e:
                self.logger.error(f"Error connecting signal: {e}")
                
            # Clear the stops list when zones change
            self.pickup_stop_list.clear()

    def find_path_between_zones(self, map_id, start_zone, end_zone, zones_data):
        """Find all zones in the path between start_zone and end_zone"""
        # Build a graph of zone connections
        graph = {}
        for zone in zones_data:
            if str(zone.get('map_id', '')) == str(map_id):
                from_zone = zone.get('from_zone', '')
                to_zone = zone.get('to_zone', '')
                if from_zone:
                    if from_zone not in graph:
                        graph[from_zone] = {}
                    graph[from_zone][to_zone] = zone.get('id', '')

        # Use BFS to find the path
        queue = [(start_zone, [start_zone], [])]
        visited = {start_zone}
        
        while queue:
            (current, path, zone_ids) = queue.pop(0)
            
            if current == end_zone:
                return path, zone_ids
                
            if current in graph:
                for next_zone, zone_id in graph[current].items():
                    if next_zone not in visited:
                        visited.add(next_zone)
                        queue.append((next_zone, path + [next_zone], zone_ids + [zone_id]))
        
        return [], []  # No path found

    def on_storing_zone_selected(self, index):
        """Handle zone selection change and populate stops for storing section"""
        self.pickup_stop_list.clear()
        
        if index > 0:  # If a zone is selected (not the default "Select" option)
            from_zone = self.storing_from_zone_combo.currentData()
            to_zone = self.storing_to_zone_combo.currentData()
            
            if not from_zone or not to_zone:
                return
                
            try:
                # Load zones and find the path between selected zones
                zones = self.csv_handler.read_csv('zones')
                selected_map_id = self.storing_map_combo.currentData()
                
                zone_path, zone_ids = self.find_path_between_zones(
                    selected_map_id, from_zone, to_zone, zones
                )
                
                if zone_ids:
                    # Load stops for all zones in the path
                    stops = self.csv_handler.read_csv('stops')
                    added_stops = set()  # To prevent duplicate stops
                    
                    for zone_id in zone_ids:
                        for stop_data in stops:
                            zone_connection_id = stop_data.get('zone_connection_id', '')
                            stop_id = stop_data.get('stop_id', '')
                            
                            if (str(zone_connection_id) == str(zone_id) and 
                                stop_id and 
                                stop_id not in added_stops):
                                    
                                stop_name = stop_data.get('name', stop_id)
                                item = QListWidgetItem(f"{stop_name} ({stop_id})")
                                item.setData(Qt.UserRole, stop_id)
                                self.pickup_stop_list.addItem(item)
                                added_stops.add(stop_id)
                                
                    # Log the path found
                    self.logger.info(f"Found path between zones: {' → '.join(zone_path)}")
                else:
                    self.logger.warning(f"No path found between zones {from_zone} and {to_zone}")
                    
            except Exception as e:
                self.logger.error(f"Error loading stops for storing section: {e}")

    def populate_pickup_maps_for_auditing(self):
        """Populate pickup maps dropdown with existing maps for auditing section"""
        self.auditing_map_combo.clear()
        self.auditing_map_combo.addItem("Select Auditing Map", "")
        
        # Load maps using the CSV handler
        try:
            maps = self.csv_handler.read_csv('maps')
            for map_data in maps:
                map_id = map_data.get('id', '')
                map_name = map_data.get('name', map_id)
                if map_id:
                    self.auditing_map_combo.addItem(map_name, map_id)
        except Exception as e:
            self.logger.error(f"Error loading maps for auditing section: {e}")

    def upload_csv_file(self):
        """Handle CSV file upload"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Upload CSV File",
            "",
            "CSV Files (*.csv);;All Files (*)"
        )
        
        if file_path:
            # Store the file path for later use
            self.uploaded_csv_file = file_path
            # Update the appropriate label to show the selected file name
            file_name = os.path.basename(file_path)
            
            # Determine which section is currently visible to update the correct label
            if (hasattr(self, 'picking_section') and self.picking_section.isVisible() and
                hasattr(self, 'uploaded_file_label')):
                self.uploaded_file_label.setText(f"File: {file_name}")
                self.uploaded_file_label.setStyleSheet("color: #3B82F6; font-size: 11px; padding: 5px;")
            elif (hasattr(self, 'storing_section') and self.storing_section.isVisible() and
                  hasattr(self, 'storing_uploaded_file_label')):
                self.storing_uploaded_file_label.setText(f"File: {file_name}")
                self.storing_uploaded_file_label.setStyleSheet("color: #3B82F6; font-size: 11px; padding: 5px;")
            elif (hasattr(self, 'auditing_section') and self.auditing_section.isVisible() and
                  hasattr(self, 'auditing_uploaded_file_label')):
                self.auditing_uploaded_file_label.setText(f"File: {file_name}")
                self.auditing_uploaded_file_label.setStyleSheet("color: #3B82F6; font-size: 11px; padding: 5px;")
