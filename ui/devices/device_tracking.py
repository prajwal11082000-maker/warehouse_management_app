from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
    QLabel, QFrame, QPushButton, QComboBox,
    QGroupBox, QFormLayout, QTableWidget,
    QTableWidgetItem, QHeaderView, QSizePolicy
)
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
        split_layout.setContentsMargins(0, 0, 0, 0)  # Remove margins for better control

        # Task Details Panel
        task_details_group = QGroupBox("Task Details")
        task_details_group.setStyleSheet(running_devices_group.styleSheet())
        task_details_group.setMinimumWidth(300)  # Set minimum width for task details panel
        task_details_layout = QFormLayout(task_details_group)
        task_details_layout.setSpacing(15)

        # Create labels for task details
        self.device_name_label = QLabel("N/A")
        self.device_id_label = QLabel("N/A")
        self.task_id_label = QLabel("N/A")
        self.task_type_label = QLabel("N/A")
        self.task_details_text = QLabel("N/A")
        self.task_details_text.setWordWrap(True)

        # Style all labels
        label_style = """
            QLabel {
                color: #ffffff;
                font-size: 13px;
                padding: 5px;
                background-color: #404040;
                border-radius: 4px;
            }
        """
        for label in [self.device_name_label, self.device_id_label, 
                     self.task_id_label, self.task_type_label, 
                     self.task_details_text]:
            label.setStyleSheet(label_style)
            label.setMinimumWidth(200)

        # Add fields to form layout
        task_details_layout.addRow("Device Name:", self.device_name_label)
        task_details_layout.addRow("Device ID:", self.device_id_label)
        task_details_layout.addRow("Task ID:", self.task_id_label)
        task_details_layout.addRow("Task Type:", self.task_type_label)
        task_details_layout.addRow("Task Details:", self.task_details_text)

        # Add live tracking fields
        self.current_location_label = QLabel("N/A")
        self.distance_label = QLabel("N/A")
        self.direction_label = QLabel("N/A")
        # New: robot facing direction (orientation)
        self.facing_label = QLabel("N/A")
        # New: last/current zone info with directions (generic, from CSV + nav manager)
        self.last_zone_info_label = QLabel("N/A")
        self.current_zone_info_label = QLabel("N/A")
        for label in [
            self.current_location_label,
            self.distance_label,
            self.direction_label,
            self.facing_label,
            self.last_zone_info_label,
            self.current_zone_info_label,
        ]:
            label.setStyleSheet(label_style)
            label.setMinimumWidth(200)

        # Add divider
        divider = QFrame()
        divider.setFrameShape(QFrame.HLine)
        divider.setStyleSheet("background-color: #666666;")
        task_details_layout.addRow(divider)

        # Add live tracking section
        tracking_title = QLabel("📍 Live Tracking")
        tracking_title.setStyleSheet("color: #ff6b35; font-weight: bold; font-size: 14px;")
        task_details_layout.addRow(tracking_title)
        task_details_layout.addRow("Current Location:", self.current_location_label)
        task_details_layout.addRow("Distance:", self.distance_label)
        task_details_layout.addRow("Direction:", self.direction_label)
        # New: Facing orientation
        task_details_layout.addRow("Facing:", self.facing_label)
        # Show full from -> to in these labels
        task_details_layout.addRow("Last Zone:", self.last_zone_info_label)
        task_details_layout.addRow("Current Zone:", self.current_zone_info_label)

        # Multi-device live tracking container (blocks added on selection)
        self.multi_tracking_container = QGroupBox("Devices Live Tracking")
        self.multi_tracking_container.setStyleSheet(running_devices_group.styleSheet())
        self.multi_tracking_layout = QVBoxLayout(self.multi_tracking_container)
        self.multi_tracking_layout.setSpacing(8)
        task_details_layout.addRow(self.multi_tracking_container)

        split_layout.addWidget(task_details_group)

        # Task Map Panel
        task_map_group = QGroupBox("Task Map")
        task_map_group.setStyleSheet(running_devices_group.styleSheet())
        task_map_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)  # Allow map to expand
        task_map_layout = QVBoxLayout(task_map_group)
        task_map_layout.setContentsMargins(10, 10, 10, 10)  # Add some padding

        # Create map viewer widget
        self.map_view = MapViewerWidget(self.api_client, self.csv_handler)
        self.map_view.setMinimumSize(400, 300)
        # Enable task mode for simplified view
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
        # Update per-device blocks if present
        if active_ids:
            for did in active_ids:
                try:
                    data = self.device_data_handler.get_latest_device_data(did)
                    blk = getattr(self, 'live_blocks', {}).get(did)
                    if data and blk:
                        blk['location'].setText(data.get('current_location', 'N/A'))
                        blk['distance'].setText(data.get('distance', 'N/A'))
                        blk['direction'].setText(data.get('direction', 'N/A'))
                    elif blk:
                        blk['location'].setText("No data available")
                        blk['distance'].setText("N/A")
                        blk['direction'].setText("N/A")
                    # Update map sprite position for this device
                    if hasattr(self, 'map_view') and self.map_view:
                        try:
                            self.map_view.map_canvas.update_robot_position_from_csv_multi(did)
                        except Exception as e:
                            self.logger.error(f"Error updating multi robot position: {e}")
                except Exception as e:
                    self.logger.error(f"Live tracking update failed for {did}: {e}")

            # Also reflect the first device in the legacy single-device labels
            first_id = active_ids[0]
            data = self.device_data_handler.get_latest_device_data(first_id) or {}
            self.current_location_label.setText(data.get('current_location', 'N/A'))
            self.distance_label.setText(data.get('distance', 'N/A'))
            direction = data.get('direction', 'N/A')
            self.direction_label.setText(direction)
            direction_color = {
                "Forward": "#10B981",
                "Backward": "#EF4444",
                "Stationary": "#8B5CF6"
            }.get(direction, "#cccccc")
            self.direction_label.setStyleSheet(f"color: {direction_color};")
            facing = data.get('facing_direction')
            self.facing_label.setText(facing.title() if isinstance(facing, str) and facing else "N/A")
            last_route = data.get('last_route')
            current_route = data.get('current_route')
            if not last_route:
                lz = data.get('last_zone')
                cz = data.get('current_zone')
                last_route = f"{lz} -> {cz}" if lz and cz else None
            if not current_route:
                cz = data.get('current_zone')
                tz = data.get('target_zone')
                current_route = f"{cz} -> {tz}" if cz and tz else None
            self.last_zone_info_label.setText(last_route or "N/A")
            self.current_zone_info_label.setText(current_route or "N/A")
            return

        # Fallback: legacy single-device behavior
        device_id = self.device_id_label.text()
        if device_id and device_id != "N/A":
            device_data = self.device_data_handler.get_latest_device_data(device_id)
            if device_data:
                self.current_location_label.setText(device_data['current_location'])
                self.current_location_label.setStyleSheet("color: #10B981;")
                self.distance_label.setText(device_data['distance'])
                self.distance_label.setStyleSheet("color: #3B82F6;")
                direction = device_data['direction']
                self.direction_label.setText(direction)
                direction_color = {
                    "Forward": "#10B981",
                    "Backward": "#EF4444",
                    "Stationary": "#8B5CF6"
                }.get(direction, "#cccccc")
                self.direction_label.setStyleSheet(f"color: {direction_color};")
                facing = device_data.get('facing_direction')
                self.facing_label.setText(facing.title() if isinstance(facing, str) and facing else "N/A")
                last_route = device_data.get('last_route')
                current_route = device_data.get('current_route')
                if not last_route:
                    lz = device_data.get('last_zone')
                    cz = device_data.get('current_zone')
                    last_route = f"{lz} -> {cz}" if lz and cz else None
                if not current_route:
                    cz = device_data.get('current_zone')
                    tz = device_data.get('target_zone')
                    current_route = f"{cz} -> {tz}" if cz and tz else None
                self.last_zone_info_label.setText(last_route or "N/A")
                self.last_zone_info_label.setStyleSheet("color: #cccccc;")
                self.current_zone_info_label.setText(current_route or "N/A")
                self.current_zone_info_label.setStyleSheet("color: #10B981;")
                if hasattr(self, 'map_view') and self.map_view:
                    try:
                        self.map_view.update_robot_position(device_id)
                    except Exception as e:
                        self.logger.error(f"Error updating robot position: {e}")
            else:
                self.current_location_label.setText("No data available")
                self.distance_label.setText("N/A")
                self.direction_label.setText("N/A")
                self.facing_label.setText("N/A")
                self.last_zone_info_label.setText("N/A")
                self.current_zone_info_label.setText("N/A")
        else:
            self.current_location_label.setText("No device selected")
            self.distance_label.setText("N/A")
            self.direction_label.setText("N/A")
            self.facing_label.setText("N/A")
            self.last_zone_info_label.setText("N/A")
            self.current_zone_info_label.setText("N/A")

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
            if not data:
                # Clear the panels
                self.device_name_label.setText("N/A")
                self.device_id_label.setText("N/A")
                self.task_id_label.setText("N/A")
                self.task_type_label.setText("N/A")
                self.task_details_text.setText("N/A")
                # Clear the map
                self.map_view.clear_map()
                # Clear multi blocks
                self._build_multi_live_tracking([])
                self.active_device_ids = []
                return

            task = data.get('task', {})
            device_ids = data.get('device_ids', [])
            devices = data.get('devices', [])

            # Update device details (summary)
            if len(devices) > 1:
                self.device_name_label.setText("Multiple")
                self.device_id_label.setText(", ".join(device_ids))
            elif len(devices) == 1:
                self.device_name_label.setText(devices[0].get('device_name', 'N/A'))
                self.device_id_label.setText(devices[0].get('device_id', 'N/A'))
            else:
                self.device_name_label.setText('N/A')
                self.device_id_label.setText('N/A')
            
            # Update task details
            self.task_id_label.setText(task.get('task_id', 'N/A'))
            self.task_type_label.setText(task.get('task_type', 'N/A').title())
            
            # Parse and display task details
            task_details = task.get('task_details', '{}')
            try:
                import json
                details_dict = json.loads(task_details)
                formatted_details = []
                
                # Format specific fields we want to show
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
            # Build multi-device live tracking blocks and remember active ids
            self._build_multi_live_tracking(device_ids)
            self.active_device_ids = device_ids
        except Exception as e:
            self.logger.error(f"Error handling device selection: {e}")
            # Clear the map and show error in info label
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

    def _build_multi_live_tracking(self, device_ids):
        """Create/refresh per-device live tracking blocks under the Live Tracking section."""
        if not hasattr(self, 'multi_tracking_layout'):
            return
        self._clear_layout(self.multi_tracking_layout)
        self.live_blocks = {}
        if not device_ids:
            lbl = QLabel("No device(s) for this task")
            lbl.setStyleSheet("color: #cccccc;")
            self.multi_tracking_layout.addWidget(lbl)
            return
        for did in device_ids:
            try:
                frame = QFrame()
                frame.setStyleSheet("QFrame { background-color: #2f2f2f; border: 1px solid #555555; border-radius: 4px; }")
                form = QFormLayout(frame)
                form.setSpacing(6)
                # Header label
                header = QLabel(f"Device: {did}")
                header.setStyleSheet("color: #ff6b35; font-weight: bold;")
                form.addRow(header)
                # Fields
                loc = QLabel("Loading...")
                loc.setStyleSheet("color: #10B981;")
                dist = QLabel("Loading...")
                dist.setStyleSheet("color: #3B82F6;")
                direc = QLabel("Loading...")
                direc.setStyleSheet("color: #8B5CF6;")
                form.addRow("Current Location:", loc)
                form.addRow("Distance:", dist)
                form.addRow("Direction:", direc)
                self.multi_tracking_layout.addWidget(frame)
                if not hasattr(self, 'live_blocks'):
                    self.live_blocks = {}
                self.live_blocks[did] = {'location': loc, 'distance': dist, 'direction': direc}
            except Exception:
                continue

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
