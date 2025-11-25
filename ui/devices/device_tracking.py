from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
    QLabel, QFrame, QPushButton, QComboBox,
    QGroupBox, QFormLayout, QTableWidget,
    QTableWidgetItem, QHeaderView, QSizePolicy,
    QScrollArea
)

class DeviceDetailCard(QFrame):
    def __init__(self, device_data, parent=None):
        super().__init__(parent)
        self.device_id = device_data.get('device_id')
        self.setup_ui(device_data)

    def setup_ui(self, data):
        self.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
        self.setStyleSheet("""
            QFrame {
                background-color: #2f2f2f;
                border: 1px solid #555555;
                border-radius: 6px;
            }
            QLabel {
                border: none;
                background-color: transparent;
                color: #e0e0e0;
            }
        """)
        layout = QVBoxLayout(self)
        layout.setSpacing(5)
        
        # Header
        header_layout = QHBoxLayout()
        name_label = QLabel(f"{data.get('device_name', 'Unknown')} ({self.device_id})")
        name_label.setStyleSheet("font-weight: bold; color: #ff6b35; font-size: 14px;")
        header_layout.addWidget(name_label)
        header_layout.addStretch()
        layout.addLayout(header_layout)
        
        # Grid for details
        details_layout = QFormLayout()
        details_layout.setSpacing(5)
        
        self.loc_label = QLabel("N/A")
        self.dist_label = QLabel("N/A")
        self.dir_label = QLabel("N/A")
        self.face_label = QLabel("N/A")
        self.last_zone_label = QLabel("N/A")
        self.curr_zone_label = QLabel("N/A")
        
        # Style values
        for lbl in [self.loc_label, self.dist_label, self.dir_label, self.face_label, self.last_zone_label, self.curr_zone_label]:
            lbl.setStyleSheet("color: #10B981;") 
            
        details_layout.addRow("Location:", self.loc_label)
        details_layout.addRow("Distance:", self.dist_label)
        details_layout.addRow("Direction:", self.dir_label)
        details_layout.addRow("Facing:", self.face_label)
        details_layout.addRow("Last Zone:", self.last_zone_label)
        details_layout.addRow("Current Zone:", self.curr_zone_label)
        
        layout.addLayout(details_layout)

    def update_data(self, data):
        if not data:
            return
        self.loc_label.setText(str(data.get('current_location', 'N/A')))
        self.dist_label.setText(str(data.get('distance', 'N/A')))
        
        direction = data.get('direction', 'N/A')
        self.dir_label.setText(direction)
        # Color code direction
        color = "#10B981" if direction == "Forward" else "#EF4444" if direction == "Backward" else "#8B5CF6" if direction == "Stationary" else "#e0e0e0"
        self.dir_label.setStyleSheet(f"color: {color};")
        
        self.face_label.setText(str(data.get('facing_direction', 'N/A')).title())
        
        # Routes
        last_route = data.get('last_route')
        if not last_route:
            lz = data.get('last_zone')
            cz = data.get('current_zone')
            last_route = f"{lz} -> {cz}" if lz and cz else "N/A"
        self.last_zone_label.setText(last_route)
        
        curr_route = data.get('current_route')
        if not curr_route:
            cz = data.get('current_zone')
            tz = data.get('target_zone')
            curr_route = f"{cz} -> {tz}" if cz and tz else "N/A"
        self.curr_zone_label.setText(curr_route)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont
from ui.maps.map_viewer import MapViewerWidget
from data_manager.device_data_handler import DeviceDataHandler
import os

from api.client import APIClient
from api.devices import DevicesAPI
from data_manager.csv_handler import CSVHandler
from utils.logger import setup_logger

# Remove references to map_preview_label that we no longer need
if 'map_preview_label' in globals():
    del map_preview_label


class DeviceTrackingWidget(QWidget):
    def __init__(self, api_client: APIClient, csv_handler: CSVHandler):
        super().__init__()
        self.api_client = api_client
        self.csv_handler = csv_handler
        self.devices_api = DevicesAPI(api_client)
        self.logger = setup_logger('device_tracking')

        # Initialize device data handler
        self.device_data_handler = DeviceDataHandler(
            os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data', 'device_logs')
        )
        
        self.setup_ui()
        self.setup_timer()
        self.load_data()

    def setup_ui(self):
        """Setup device tracking UI"""
        # Create main layout
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(20, 20, 20, 20)
        self.layout.setSpacing(20)

        # Create main container
        main_container = QWidget()
        main_layout = QVBoxLayout(main_container)
        main_layout.setSpacing(20)

        # Create tabs
        self.create_tabs(main_layout)

        # Create refresh button
        self.create_refresh_button(main_layout)

        # Add main container to the layout
        self.layout.addWidget(main_container)

    def create_tabs(self, parent_layout):
        """Create tab widget with different tracking views"""
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

        # Real-time tracking tab
        self.realtime_tab = self.create_realtime_tab()
        self.tab_widget.addTab(self.realtime_tab, "🔴 Live Tracking")

        # Historical data tab
        self.history_tab = self.create_history_tab()
        self.tab_widget.addTab(self.history_tab, "📊 Performance History")

        # Analytics tab
        self.analytics_tab = self.create_analytics_tab()
        self.tab_widget.addTab(self.analytics_tab, "📈 Analytics")

        parent_layout.addWidget(self.tab_widget)

    def create_realtime_tab(self):
        """Create real-time tracking tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(20)

        # Running Devices Dropdown
        running_devices_group = QGroupBox("Running Devices")
        running_devices_group.setStyleSheet("""
            QGroupBox {
                border: 1px solid #555555;
                border-radius: 6px;
                margin-top: 1em;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 3px;
                color: #ff6b35;
            }
        """)
        running_devices_layout = QHBoxLayout(running_devices_group)

        self.running_devices_combo = QComboBox()
        self.running_devices_combo.setMinimumWidth(300)
        self.running_devices_combo.setStyleSheet("""
            QComboBox {
                background-color: #404040;
                border: 1px solid #555555;
                border-radius: 4px;
                color: #ffffff;
                padding: 8px;
                font-size: 13px;
            }
            QComboBox::drop-down {
                border: none;
                padding-right: 15px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid #ffffff;
                width: 0;
                height: 0;
                margin-right: 8px;
            }
        """)
        self.running_devices_combo.currentIndexChanged.connect(self.on_running_device_selected)
        running_devices_layout.addWidget(self.running_devices_combo)

        layout.addWidget(running_devices_group)

        # Split view for task details and map
        split_container = QWidget()
        split_layout = QHBoxLayout(split_container)
        split_layout.setSpacing(20)
        split_layout.setContentsMargins(0, 0, 0, 0)

        # Left Panel: Task Details + Scrollable Device List
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(10)
        left_panel.setMinimumWidth(350)
        left_panel.setMaximumWidth(400)

        # 1. Task Info Group (Fixed)
        task_info_group = QGroupBox("Task Info")
        task_info_group.setStyleSheet(running_devices_group.styleSheet())
        task_info_layout = QFormLayout(task_info_group)
        task_info_layout.setSpacing(10)

        self.task_id_label = QLabel("N/A")
        self.task_type_label = QLabel("N/A")
        self.task_details_text = QLabel("N/A")
        self.task_details_text.setWordWrap(True)
        
        label_style = """
            QLabel {
                color: #ffffff;
                font-size: 13px;
                padding: 5px;
                background-color: #404040;
                border-radius: 4px;
            }
        """
        for label in [self.task_id_label, self.task_type_label, self.task_details_text]:
            label.setStyleSheet(label_style)

        task_info_layout.addRow("Task ID:", self.task_id_label)
        task_info_layout.addRow("Task Type:", self.task_type_label)
        task_info_layout.addRow("Details:", self.task_details_text)

        left_layout.addWidget(task_info_group)

        # 2. Devices List (Scrollable)
        devices_group = QGroupBox("Devices Live Tracking")
        devices_group.setStyleSheet(running_devices_group.styleSheet())
        devices_layout_wrapper = QVBoxLayout(devices_group)
        
        self.devices_scroll = QScrollArea()
        self.devices_scroll.setWidgetResizable(True)
        self.devices_scroll.setStyleSheet("""
            QScrollArea { border: none; background-color: transparent; }
            QWidget { background-color: transparent; }
            QScrollBar:vertical {
                border: none;
                background: #2b2b2b;
                width: 10px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: #555555;
                min-height: 20px;
                border-radius: 5px;
            }
        """)
        
        self.devices_container = QWidget()
        self.devices_layout = QVBoxLayout(self.devices_container)
        self.devices_layout.setSpacing(10)
        self.devices_layout.addStretch() # Push items up
        
        self.devices_scroll.setWidget(self.devices_container)
        devices_layout_wrapper.addWidget(self.devices_scroll)
        
        left_layout.addWidget(devices_group)
        
        split_layout.addWidget(left_panel)

        # Right Panel: Task Map
        task_map_group = QGroupBox("Task Map")
        task_map_group.setStyleSheet(running_devices_group.styleSheet())
        task_map_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        task_map_layout = QVBoxLayout(task_map_group)
        task_map_layout.setContentsMargins(10, 10, 10, 10)

        self.map_view = MapViewerWidget(self.api_client, self.csv_handler)
        self.map_view.setMinimumSize(400, 300)
        self.map_view.set_task_mode(True)
        task_map_layout.addWidget(self.map_view)

        split_layout.addWidget(task_map_group)

        layout.addWidget(split_container)
        layout.addStretch()
        return tab

    def create_history_tab(self):
        """Create historical data tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(20)

        # Device selection and time range
        filters_group = QGroupBox("Filters")
        filters_group.setStyleSheet("""
            QGroupBox {
                border: 1px solid #555555;
                border-radius: 6px;
                margin-top: 1em;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 3px;
                color: #ff6b35;
            }
        """)
        filters_layout = QHBoxLayout(filters_group)

        # Add filter controls here
        self.history_device_combo = QComboBox()
        self.history_device_combo.setMinimumWidth(200)
        self.history_device_combo.setStyleSheet("""
            QComboBox {
                background-color: #404040;
                border: 1px solid #555555;
                border-radius: 4px;
                color: #ffffff;
                padding: 5px;
            }
        """)
        filters_layout.addWidget(self.history_device_combo)
        filters_layout.addStretch()

        layout.addWidget(filters_group)

        # Historical data table
        self.history_table = QTableWidget()
        self.history_table.setStyleSheet("""
            QTableWidget {
                background-color: #2b2b2b;
                border: 1px solid #555555;
            }
            QTableWidget::item {
                color: #ffffff;
                padding: 5px;
            }
            QHeaderView::section {
                background-color: #404040;
                color: #ffffff;
                padding: 5px;
                border: 1px solid #555555;
            }
        """)
        layout.addWidget(self.history_table)

        return tab

    def create_analytics_tab(self):
        """Create analytics tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(20)

        # Performance metrics section
        metrics_group = QGroupBox("Performance Metrics")
        metrics_group.setStyleSheet("""
            QGroupBox {
                border: 1px solid #555555;
                border-radius: 6px;
                margin-top: 1em;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 3px;
                color: #ff6b35;
            }
        """)
        metrics_layout = QFormLayout(metrics_group)

        # Add metrics labels
        self.uptime_label = QLabel("N/A")
        self.tasks_completed_label = QLabel("0")
        self.avg_task_time_label = QLabel("N/A")
        self.efficiency_label = QLabel("N/A")

        metrics_layout.addRow("Uptime:", self.uptime_label)
        metrics_layout.addRow("Tasks Completed:", self.tasks_completed_label)
        metrics_layout.addRow("Average Task Time:", self.avg_task_time_label)
        metrics_layout.addRow("Efficiency Score:", self.efficiency_label)

        layout.addWidget(metrics_group)

        layout.addStretch()
        return tab

    def create_refresh_button(self, parent_layout):
        """Create refresh button"""
        refresh_btn = QPushButton("🔄 Refresh Data")
        refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #10B981;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #059669;
            }
        """)
        refresh_btn.clicked.connect(self.load_data)
        parent_layout.addWidget(refresh_btn)

    def setup_timer(self):
        """Setup auto-refresh timer"""
        # Main data refresh timer
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.load_data)
        self.refresh_timer.start(5000)  # Refresh every 5 seconds
        
        # Live tracking update timer
        self.tracking_timer = QTimer()
        self.tracking_timer.timeout.connect(self.update_live_tracking)
        self.tracking_timer.start(1000)  # Update tracking every second

    def load_data(self):
        """Load device data"""
        try:
            devices = self.csv_handler.read_csv('devices')
            tasks = self.csv_handler.read_csv('tasks')
            self.update_running_devices_combo(devices, tasks)
            self.update_history_data()
            self.update_analytics()
            self.update_live_tracking()  # Update live tracking on data load
        except Exception as e:
            self.logger.error(f"Error loading device data: {e}")

    def update_live_tracking(self):
        """Update live tracking for active devices and map sprites."""
        active_ids = getattr(self, 'active_device_ids', []) or []
        
        # Update map sprites
        if hasattr(self, 'map_view') and self.map_view and active_ids:
            try:
                for did in active_ids:
                    self.map_view.map_canvas.update_robot_position_from_csv_multi(did)
            except Exception as e:
                self.logger.error(f"Error updating map positions: {e}")

        # Update device cards
        if hasattr(self, 'device_cards'):
            for did, card in self.device_cards.items():
                try:
                    data = self.device_data_handler.get_latest_device_data(did)
                    card.update_data(data)
                except Exception as e:
                    self.logger.error(f"Error updating card for {did}: {e}")


    def update_running_devices_combo(self, devices, tasks):
        """Update selector to show running tasks with their assigned devices (multi-supported)."""
        try:
            current_data = self.running_devices_combo.currentData()
            
            self.running_devices_combo.clear()
            self.running_devices_combo.addItem("Select Running Task", None)

            # Helper to resolve device_id string list from task
            def resolve_device_ids_for_task(task):
                multi_ids = [s.strip() for s in str(task.get('assigned_device_ids') or '').split(',') if s.strip()]
                if not multi_ids and task.get('assigned_device_id'):
                    multi_ids = [str(task.get('assigned_device_id'))]
                result = []
                for ref in multi_ids:
                    drow = next((d for d in devices if str(d.get('id')) == str(ref) or str(d.get('device_id')) == str(ref)), None)
                    if drow and drow.get('device_id'):
                        result.append(str(drow.get('device_id')))
                    else:
                        result.append(str(ref))
                return result

            running_tasks = [t for t in tasks if str(t.get('status','')).lower() == 'running']
            for task in running_tasks:
                dids = resolve_device_ids_for_task(task)
                if not dids:
                    continue
                # Collect device objects for extra info
                dev_objs = []
                for did in dids:
                    dev = next((d for d in devices if str(d.get('device_id')) == str(did)), None)
                    if dev:
                        dev_objs.append(dev)
                names = [f"{d.get('device_name','')} ({d.get('device_id','')})" for d in dev_objs] or dids
                display_text = f"Task: {task.get('task_name','')}  |  Devices: {', '.join(names)}"
                item_data = {'task': task, 'devices': dev_objs, 'device_ids': dids}
                self.running_devices_combo.addItem(display_text, item_data)

            # Restore previous selection if still valid (by task id)
            if current_data and isinstance(current_data, dict) and 'task' in current_data:
                prev_task_id = current_data['task'].get('id')
                for i in range(self.running_devices_combo.count()):
                    data = self.running_devices_combo.itemData(i)
                    if data and data.get('task', {}).get('id') == prev_task_id:
                        self.running_devices_combo.setCurrentIndex(i)
                        break
            
        except Exception as e:
            self.logger.error(f"Error updating running devices: {e}")

    def on_running_device_selected(self, index):
        """Handle running selection: load task map and enable multi-device tracking for its devices."""
        try:
            data = self.running_devices_combo.currentData()
            
            # Clear previous cards
            while self.devices_layout.count():
                item = self.devices_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
            self.devices_layout.addStretch() # Ensure stretch is always at bottom
            
            self.device_cards = {}
            self.active_device_ids = []

            if not data:
                self.task_id_label.setText("N/A")
                self.task_type_label.setText("N/A")
                self.task_details_text.setText("N/A")
                self.map_view.clear_map()
                return

            task = data.get('task', {})
            device_ids = data.get('device_ids', [])
            devices = data.get('devices', [])

            # Update task details
            self.task_id_label.setText(task.get('task_id', 'N/A'))
            self.task_type_label.setText(task.get('task_type', 'N/A').title())
            
            # Parse and display task details
            task_details = task.get('task_details', '{}')
            try:
                import json
                details_dict = json.loads(task_details)
                formatted_details = []
                
                if details_dict.get('pickup_map_name'):
                    formatted_details.append(f"Pickup Map: {details_dict['pickup_map_name']}")
                if details_dict.get('drop_zone_name'):
                    formatted_details.append(f"Drop Zone: {details_dict['drop_zone_name']}")
                if details_dict.get('drop_stop_names'):
                    stops = ', '.join(details_dict['drop_stop_names'])
                    formatted_details.append(f"Stops: {stops}")
                
                self.task_details_text.setText('\n'.join(formatted_details) if formatted_details else 'No details available')
            except Exception as e:
                self.logger.error(f"Error parsing task details: {e}")
                self.task_details_text.setText("Error loading task details")

            # Create cards for each device
            # Remove the stretch first
            self.devices_layout.takeAt(self.devices_layout.count() - 1)
            
            for i, did in enumerate(device_ids):
                # Find device data object
                dev_obj = next((d for d in devices if str(d.get('device_id')) == str(did)), {'device_id': did, 'device_name': f'Device {i+1}'})
                
                card = DeviceDetailCard(dev_obj)
                self.devices_layout.addWidget(card)
                self.device_cards[did] = card
                
            self.devices_layout.addStretch()
            self.active_device_ids = device_ids

            # Update map view based on task data
            map_id = task.get('map_id')
            if map_id:
                maps = self.csv_handler.read_csv('maps')
                map_data = next((m for m in maps if str(m.get('id')) == str(map_id)), None)
                if map_data:
                    # Get task status
                    task_status = task.get('status', '').lower()

                    # Get all required data for the map
                    zones = self.csv_handler.read_csv('zones')
                    stops = self.csv_handler.read_csv('stops')
                    stop_groups = self.csv_handler.read_csv('stop_groups')

                    # Filter data for current map
                    map_zones = [z for z in zones if str(z.get('map_id')) == str(map_id)]
                    map_stops = [s for s in stops if str(s.get('map_id')) == str(map_id)]
                    map_stop_groups = [sg for sg in stop_groups if str(sg.get('map_id')) == str(map_id)]

                    # Get map dimensions
                    map_width = int(map_data.get('width', 1000))
                    map_height = int(map_data.get('height', 800))

                    # Format task details for map viewer
                    task_details = task.get("task_details", "{}")
                    if isinstance(task_details, str):
                        try:
                            import json
                            details_dict = json.loads(task_details)
                        except json.JSONDecodeError:
                            details_dict = {}
                    else:
                        details_dict = task_details

                    # Build formatted task details string
                    formatted_details = []
                    if details_dict.get('pickup_map_name'):
                        formatted_details.append(f"Pickup Map: {details_dict['pickup_map_name']}")
                    if details_dict.get('drop_zone_name'):
                        formatted_details.append(f"Drop Zone: {details_dict['drop_zone_name']}")
                    if details_dict.get('zone_name'):
                        formatted_details.append(f"Zone: {details_dict['zone_name']}")
                    details_str = ' | '.join(formatted_details)

                    # Create task info dictionary with proper format
                    task_info_dict = {
                        "details": details_str,
                        "type": task.get("task_type", "").lower(),  # ensure lowercase
                        "status": task.get("status", "").lower()    # ensure lowercase
                    }
                    
                    self.map_view.set_map_data(
                        zones=map_zones,
                        stops=map_stops,
                        stop_groups=map_stop_groups,
                        map_width=map_width,
                        map_height=map_height,
                        map_data=map_data,
                        task_status=task_status,
                        task_details=task_info_dict
                    )
                    
                    # Fit the map to view
                    self.map_view.fit_to_view()
                    # Enable multi-robot sprites and initialize their positions
                    if device_ids:
                        try:
                            self.map_view.map_canvas.set_active_devices(device_ids)
                            for did in device_ids:
                                self.map_view.map_canvas.update_robot_position_from_csv_multi(did)
                        except Exception as e:
                            self.logger.error(f"Error initializing multi robots: {e}")
            else:
                # Clear the map if no map_id
                self.map_view.clear_map()
        except Exception as e:
            self.logger.error(f"Error handling device selection: {e}")
            self.map_view.clear_map()


    # -------- Helpers for multi-device live tracking --------
    def _clear_layout(self, layout):
        try:
            if layout is None:
                return
            while layout.count():
                item = layout.takeAt(0)
                widget = item.widget()
                if widget:
                    widget.setParent(None)
        except Exception:
            pass



    def update_device_combo(self, devices):
        """Update device selection combo boxes"""
        current_device = self.history_device_combo.currentText()
        
        self.history_device_combo.clear()
        
        for device in devices:
            device_text = f"{device.get('device_name', '')} ({device.get('device_id', '')})"
            self.history_device_combo.addItem(device_text)
        
        # Restore previous selection if it still exists
        index = self.history_device_combo.findText(current_device)
        if index >= 0:
            self.history_device_combo.setCurrentIndex(index)

    def update_history_data(self):
        """Update historical data table"""
        try:
            device_id = self.get_selected_device_id()
            if not device_id:
                return

            # Read device log data
            log_data = self.read_device_log(device_id)
            
            # Setup table
            self.history_table.clear()
            self.history_table.setColumnCount(5)
            self.history_table.setHorizontalHeaderLabels([
                "Timestamp", "Right Drive", "Left Drive", 
                "Right Motor", "Left Motor"
            ])

            # Populate table
            self.history_table.setRowCount(len(log_data))
            for i, entry in enumerate(log_data):
                self.history_table.setItem(i, 0, QTableWidgetItem(entry.get('timestamp', '')))
                self.history_table.setItem(i, 1, QTableWidgetItem(str(entry.get('right_drive', '0'))))
                self.history_table.setItem(i, 2, QTableWidgetItem(str(entry.get('left_drive', '0'))))
                self.history_table.setItem(i, 3, QTableWidgetItem(str(entry.get('right_motor', '0'))))
                self.history_table.setItem(i, 4, QTableWidgetItem(str(entry.get('left_motor', '0'))))

            # Adjust column widths
            self.history_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        except Exception as e:
            self.logger.error(f"Error updating history data: {e}")

    def update_analytics(self):
        """Update analytics data"""
        try:
            device_id = self.get_selected_device_id()
            if not device_id:
                return

            # Calculate metrics from tasks
            tasks = self.csv_handler.read_csv('tasks')
            device_tasks = [t for t in tasks if str(t.get('assigned_device_id')) == str(device_id)]
            
            completed_tasks = [t for t in device_tasks if t.get('status') == 'completed']
            
            # Update labels
            self.tasks_completed_label.setText(str(len(completed_tasks)))
            
            if completed_tasks:
                # Calculate average task time
                total_time = 0
                count = 0
                for task in completed_tasks:
                    start = task.get('started_at')
                    end = task.get('completed_at')
                    if start and end:
                        try:
                            from datetime import datetime
                            start_time = datetime.fromisoformat(start)
                            end_time = datetime.fromisoformat(end)
                            duration = (end_time - start_time).total_seconds() / 60  # in minutes
                            total_time += duration
                            count += 1
                        except Exception as e:
                            self.logger.error(f"Error calculating task duration: {e}")
                
                if count > 0:
                    avg_time = total_time / count
                    self.avg_task_time_label.setText(f"{avg_time:.1f} minutes")
                
                # Calculate efficiency (completed tasks / total tasks)
                efficiency = (len(completed_tasks) / len(device_tasks)) * 100
                self.efficiency_label.setText(f"{efficiency:.1f}%")
            
        except Exception as e:
            self.logger.error(f"Error updating analytics: {e}")

    def get_selected_device_id(self):
        """Get the ID of the currently selected device"""
        text = self.history_device_combo.currentText()
        if not text:
            return None
        
        # Extract device ID from the format "Device Name (Device ID)"
        import re
        match = re.search(r'\(([^)]+)\)$', text)
        return match.group(1) if match else None

    def read_device_log(self, device_id):
        """Read device log data from CSV file"""
        import csv
        from pathlib import Path
        
        try:
            log_path = Path(f'data/device_logs/{device_id}.csv')
            if not log_path.exists():
                return []
            
            with open(log_path, 'r', newline='') as f:
                reader = csv.DictReader(f)
                return list(reader)
        except Exception as e:
            self.logger.error(f"Error reading device log: {e}")
            return []
