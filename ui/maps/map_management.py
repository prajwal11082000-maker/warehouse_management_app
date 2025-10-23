from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                             QLabel, QComboBox, QMessageBox, QFrame, QSplitter,
                             QTabWidget, QTabBar, QScrollArea, QSpinBox, QDoubleSpinBox,
                             QLineEdit, QListWidget, QListWidgetItem, QCheckBox,
                             QFormLayout, QGroupBox, QGridLayout, QTextEdit,
                             QTableWidget, QAbstractItemView, QFileDialog,
                             QTableWidgetItem, QHeaderView, QSizePolicy)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QPointF, QRectF, QDateTime
from PyQt5.QtGui import QFont, QPainter, QPen, QBrush, QColor
from datetime import datetime
import csv

from .map_viewer import MapViewerWidget
from ui.common.table_widget import DataTableWidget
from api.client import APIClient
from api.maps import MapsAPI
from data_manager.csv_handler import CSVHandler
from data_manager.sync_manager import SyncManager
from utils.logger import setup_logger


class MapManagementWidget(QWidget):
    map_updated = pyqtSignal()

    def __init__(self, api_client: APIClient, csv_handler: CSVHandler):
        super().__init__()
        self.api_client = api_client
        self.csv_handler = csv_handler
        self.maps_api = MapsAPI(api_client)
        self.sync_manager = SyncManager(api_client, csv_handler)
        self.logger = setup_logger('map_management')

        # Data storage
        self.current_maps = []
        self.current_zones = []
        self.current_stops = []
        self.current_stop_groups = []
        self.selected_map_id = None
        
        # Ensure widget is visible
        self.setVisible(True)

        self.setup_ui()
        self.refresh_data()
        
        # Initialize tab accessibility without switching tabs
        self.update_tab_accessibility()
        
        # Ensure we start on the overview tab (index 0) during initialization
        self.tab_widget.setCurrentIndex(0)
        
        # Log initialization
        self.logger.info("Map Management widget initialized")

    def setup_ui(self):
        """Setup map management UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Main content
        self.create_main_content(layout)

        # Action buttons
        self.create_action_buttons(layout)

    def create_header(self, parent_layout):
        """Create header with map selection"""
        header_frame = QFrame()
        header_frame.setStyleSheet("""
            QFrame {
                background-color: #353535;
                border: 1px solid #555555;
                border-radius: 6px;
                padding: 15px;
            }
        """)
        header_layout = QHBoxLayout(header_frame)

        # Title
        title = QLabel("Map Management")
        title.setFont(QFont("Arial", 18, QFont.Bold))
        title.setStyleSheet("color: #ffffff;")
        header_layout.addWidget(title)

        header_layout.addStretch()

        # Map selection
        map_label = QLabel("Current Map:")
        map_label.setStyleSheet("color: #cccccc; font-weight: bold;")
        header_layout.addWidget(map_label)

        self.map_selector = QComboBox()
        self.map_selector.addItem("No Map Selected", "")
        self.map_selector.currentTextChanged.connect(self.on_map_selected)
        self.apply_combo_style(self.map_selector)
        header_layout.addWidget(self.map_selector)

        # New map button
        new_map_btn = QPushButton("➕ Create New Map")
        new_map_btn.clicked.connect(self.create_new_map)
        new_map_btn.setStyleSheet("""
            QPushButton {
                background-color: #10B981;
                color: white;
                border: none;
                padding: 10px 16px;
                border-radius: 6px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #059669;
            }
        """)
        header_layout.addWidget(new_map_btn)

        parent_layout.addWidget(header_frame)

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
        
        # Ensure tab widget is visible and tabs are at the top
        self.tab_widget.setVisible(True)
        self.tab_widget.setTabPosition(QTabWidget.North)

        # We'll add a custom top row with tabs (left) and controls (right)

        # Tab 1: Map Overview
        self.overview_tab = self.create_overview_tab()
        self.tab_widget.addTab(self.overview_tab, "🗺️ Map Overview")

        # Tab 2: Zone Management
        self.zones_tab = self.create_zones_tab()
        self.tab_widget.addTab(self.zones_tab, "🏗️ Zone Management")

        # Tab 3: Stop Management
        self.stops_tab = self.create_stops_tab()
        self.tab_widget.addTab(self.stops_tab, "📍 Stop Management")

        # Tab 4: Rack Configuration (new)
        self.rack_config_tab = self.create_rack_config_tab()
        self.tab_widget.addTab(self.rack_config_tab, "🗄️ Rack Configuration")

        # Tab 5: Map Settings
        self.settings_tab = self.create_settings_tab()
        self.tab_widget.addTab(self.settings_tab, "⚙️ Map Settings")

        # Build a custom top row with our own QTabBar and right-aligned controls
        top_row_container = QWidget()
        top_row_layout = QHBoxLayout(top_row_container)
        top_row_layout.setContentsMargins(0, 0, 0, 0)
        top_row_layout.setSpacing(8)

        # Create custom tab bar mirroring the QTabWidget tabs
        self.custom_tab_bar = QTabBar()
        self.custom_tab_bar.setExpanding(False)
        self.custom_tab_bar.setDrawBase(False)
        self.custom_tab_bar.setElideMode(Qt.ElideRight)
        # Copy tabs
        for i in range(self.tab_widget.count()):
            self.custom_tab_bar.addTab(self.tab_widget.tabText(i))
        self.custom_tab_bar.setCurrentIndex(self.tab_widget.currentIndex())
        # Sync selection both ways
        self.custom_tab_bar.currentChanged.connect(self.tab_widget.setCurrentIndex)
        self.tab_widget.currentChanged.connect(self.custom_tab_bar.setCurrentIndex)

        # Style custom tab bar similar to original
        self.custom_tab_bar.setStyleSheet("""
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

        top_row_layout.addWidget(self.custom_tab_bar)
        top_row_layout.addStretch(1)

        # Right controls
        self.map_label = QLabel("Current Map:")
        self.map_label.setStyleSheet("color: #cccccc; font-weight: bold;")
        top_row_layout.addWidget(self.map_label)

        self.map_selector = QComboBox()
        self.map_selector.addItem("No Map Selected", "")
        self.map_selector.currentTextChanged.connect(self.on_map_selected)
        self.apply_combo_style(self.map_selector)
        self.map_selector.setMinimumWidth(160)
        self.map_selector.setMaximumWidth(260)
        top_row_layout.addWidget(self.map_selector)

        self.new_map_btn = QPushButton("➕ Create New Map")
        self.new_map_btn.clicked.connect(self.create_new_map)
        self.new_map_btn.setStyleSheet("""
            QPushButton {
                background-color: #10B981;
                color: white;
                border: none;
                padding: 10px 16px;
                border-radius: 6px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #059669;
            }
        """)
        top_row_layout.addWidget(self.new_map_btn)

        # Hide the original tab bar and insert the custom top row above the QTabWidget
        self.tab_widget.tabBar().hide()
        parent_layout.addWidget(top_row_container)
        parent_layout.addWidget(self.tab_widget)

    def create_overview_tab(self):
        """Create map overview tab with scrollable content"""
        # Create main tab widget with explicit visibility
        tab_widget = QWidget()
        tab_widget.setVisible(True)  # Explicitly set tab visibility
        tab_widget.setSizePolicy(tab_widget.sizePolicy().Expanding, tab_widget.sizePolicy().Expanding)
        tab_widget.setAttribute(Qt.WA_StyledBackground, True)  # Enable background styling
        
        # Create scroll area to contain all content
        scroll_area = QScrollArea(tab_widget)
        scroll_area.setVisible(True)  # Explicitly set scroll area visibility
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setFrameStyle(QFrame.NoFrame)
        scroll_area.setAttribute(Qt.WA_StyledBackground, True)  # Enable background styling for scroll area
        scroll_area.setStyleSheet("""
            QScrollArea {
                background-color: transparent;
                border: none;
            }
            QScrollBar:vertical {
                background-color: #404040;
                width: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background-color: #ff6b35;
                border-radius: 6px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #e55a2b;
            }
        """)
        
        # Create scrollable content widget
        scroll_content = QWidget()
        scroll_content.setSizePolicy(scroll_content.sizePolicy().Expanding, scroll_content.sizePolicy().Preferred)
        
        # Use horizontal layout for side-by-side arrangement
        layout = QHBoxLayout(scroll_content)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        # Left panel - Map information and statistics
        left_panel = self.create_map_info_section()
        layout.addWidget(left_panel, 1)  # Fixed width ratio
        
        # Map info section
        #info_section = self.create_map_info_section()
        #layout.addWidget(info_section)

        # Right panel - Map viewer
        # Map viewer with explicit visibility
        self.map_viewer = MapViewerWidget(self.api_client, self.csv_handler)
        self.map_viewer.setVisible(True)  # Explicitly set visibility
        self.map_viewer.stop_selected.connect(self.on_stop_selected)
        # Set minimum size for map viewer
        self.map_viewer.setMinimumWidth(600)
        self.map_viewer.setMinimumHeight(400)  # Ensure minimum height
        # Set size policy to expand in both directions
        self.map_viewer.setSizePolicy(
            self.map_viewer.sizePolicy().Expanding,
            self.map_viewer.sizePolicy().Expanding
        )
        layout.addWidget(self.map_viewer, 2)  # Takes more space
        self.map_viewer.show()  # Force show after adding to layout
        # layout.addWidget(self.map_viewer)
        
        # Set the scroll content
        scroll_area.setWidget(scroll_content)
        
        # Layout for the main tab widget
        tab_layout = QVBoxLayout(tab_widget)
        tab_layout.setContentsMargins(0, 0, 0, 0)
        tab_layout.addWidget(scroll_area)

        return tab_widget


    def create_rack_config_tab(self):
        """Create rack configuration tab split 50:50 with Rack Configuration (left) and Add SKU Location (right)"""
        tab_widget = QWidget()
        tab_widget.setSizePolicy(tab_widget.sizePolicy().Expanding, tab_widget.sizePolicy().Expanding)

        # Split layout
        split_layout = QHBoxLayout()
        split_layout.setContentsMargins(0, 0, 0, 0)
        split_layout.setSpacing(12)

        # Left: Rack Configuration container
        rack_container = QFrame(tab_widget)
        rack_container.setStyleSheet("""
            QFrame {
                background-color: #353535;
                border: 1px solid #555555;
                border-radius: 6px;
                padding: 16px;
            }
        """)
        rack_layout = QVBoxLayout(rack_container)
        rack_layout.setContentsMargins(15, 15, 15, 15)
        rack_layout.setSpacing(12)

        # Title (left)
        title_left = QLabel("Rack Configuration")
        title_left.setFont(QFont("Arial", 14, QFont.Bold))
        title_left.setStyleSheet("color: #ff6b35;")
        rack_layout.addWidget(title_left)

        # Form for Rack Configuration
        rack_form = QFormLayout()

        # Zone selector (for selected map)
        self.rack_zone_combo = QComboBox()
        self.apply_combo_style(self.rack_zone_combo)
        self.rack_zone_combo.addItem("Select Zone", "")
        self.rack_zone_combo.currentIndexChanged.connect(self.on_rack_zone_changed)
        rack_form.addRow("Zone:", self.rack_zone_combo)

        # Stop selector (for selected zone)
        self.rack_stop_combo = QComboBox()
        self.apply_combo_style(self.rack_stop_combo)
        self.rack_stop_combo.addItem("Select Stop", "")
        self.rack_stop_combo.currentIndexChanged.connect(self.on_rack_inputs_changed)
        rack_form.addRow("Stop:", self.rack_stop_combo)

        # Rack distance input (mm)
        self.rack_distance_input = QSpinBox()
        self.rack_distance_input.setRange(0, 1000000)
        self.rack_distance_input.setSingleStep(10)
        self.rack_distance_input.setSuffix(" mm")
        self.apply_input_style(self.rack_distance_input)
        self.rack_distance_input.valueChanged.connect(self.on_rack_inputs_changed)
        rack_form.addRow("Distance from ground:", self.rack_distance_input)

        rack_layout.addLayout(rack_form)

        # Add rack button
        self.add_rack_btn = QPushButton("➕ Add Rack")
        self.add_rack_btn.clicked.connect(self.on_add_rack_clicked)
        self.apply_button_style(self.add_rack_btn)
        self.add_rack_btn.setEnabled(False)
        rack_layout.addWidget(self.add_rack_btn)

        split_layout.addWidget(rack_container, 1)

        # Right: Add SKU Location container
        sku_container = QFrame(tab_widget)
        sku_container.setStyleSheet("""
            QFrame {
                background-color: #353535;
                border: 1px solid #555555;
                border-radius: 6px;
                padding: 16px;
            }
        """)
        sku_layout = QVBoxLayout(sku_container)
        sku_layout.setContentsMargins(15, 15, 15, 15)
        sku_layout.setSpacing(12)

        # Title (right)
        title_right = QLabel("Add SKU Location")
        title_right.setFont(QFont("Arial", 14, QFont.Bold))
        title_right.setStyleSheet("color: #ff6b35;")
        sku_layout.addWidget(title_right)

        # Form for Add SKU Location
        sku_form = QFormLayout()

        # Zone selector (for selected map)
        self.sku_zone_combo = QComboBox()
        self.apply_combo_style(self.sku_zone_combo)
        self.sku_zone_combo.addItem("Select Zone", "")
        self.sku_zone_combo.currentIndexChanged.connect(self.on_sku_zone_changed)
        sku_form.addRow("Zone:", self.sku_zone_combo)

        # Stop selector (for selected zone)
        self.sku_stop_combo = QComboBox()
        self.apply_combo_style(self.sku_stop_combo)
        self.sku_stop_combo.addItem("Select Stop", "")
        self.sku_stop_combo.currentIndexChanged.connect(self.on_sku_stop_changed)
        sku_form.addRow("Stop:", self.sku_stop_combo)

        # Rack selector (for selected stop)
        self.sku_rack_combo = QComboBox()
        self.apply_combo_style(self.sku_rack_combo)
        self.sku_rack_combo.addItem("Select Rack", "")
        self.sku_rack_combo.currentIndexChanged.connect(self.on_sku_inputs_changed)
        sku_form.addRow("Rack:", self.sku_rack_combo)

        # Total SKU locations input
        self.sku_count_input = QSpinBox()
        self.sku_count_input.setRange(1, 100000)
        self.sku_count_input.setSingleStep(1)
        self.apply_input_style(self.sku_count_input)
        self.sku_count_input.valueChanged.connect(self.on_sku_inputs_changed)
        sku_form.addRow("Total SKU Locations:", self.sku_count_input)

        sku_layout.addLayout(sku_form)

        # Add SKU Location button
        self.add_sku_btn = QPushButton("➕ Add SKU Location")
        self.add_sku_btn.clicked.connect(self.on_add_sku_location_clicked)
        self.apply_button_style(self.add_sku_btn)
        self.add_sku_btn.setEnabled(False)
        sku_layout.addWidget(self.add_sku_btn)

        split_layout.addWidget(sku_container, 1)

        # Outer tab layout
        outer = QVBoxLayout(tab_widget)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addLayout(split_layout)

        # Populate initial combos
        self.populate_rack_zone_combo()
        self.populate_rack_stop_combo()
        self.populate_sku_zone_combo()
        self.populate_sku_stop_combo()
        self.populate_sku_rack_combo()
        self.populate_sku_zone_combo()
        self.populate_sku_stop_combo()
        self.populate_sku_rack_combo()

        return tab_widget

    def on_rack_inputs_changed(self):
        """Enable add button only when inputs are valid"""
        zone_id = self.rack_zone_combo.currentData() if hasattr(self, 'rack_zone_combo') else None
        stop_id = self.rack_stop_combo.currentData() if hasattr(self, 'rack_stop_combo') else None
        distance_ok = hasattr(self, 'rack_distance_input') and (self.rack_distance_input.value() > 0)
        can_add = bool(zone_id) and bool(stop_id) and distance_ok
        if hasattr(self, 'add_rack_btn'):
            self.add_rack_btn.setEnabled(can_add)

    def populate_rack_zone_combo(self):
        """Populate rack tab zone combo with zones for the selected map"""
        if not hasattr(self, 'rack_zone_combo'):
            return
        self.rack_zone_combo.blockSignals(True)
        self.rack_zone_combo.clear()
        self.rack_zone_combo.addItem("Select Zone", "")
        for zone in getattr(self, 'current_zones', []) or []:
            zone_text = f"{zone.get('from_zone', '')} → {zone.get('to_zone', '')}"
            self.rack_zone_combo.addItem(zone_text, zone.get('id'))
        self.rack_zone_combo.blockSignals(False)

    def populate_rack_stop_combo(self):
        """Populate rack tab stop combo with stops for selected zone"""
        if not hasattr(self, 'rack_stop_combo'):
            return
        self.rack_stop_combo.blockSignals(True)
        self.rack_stop_combo.clear()
        self.rack_stop_combo.addItem("Select Stop", "")
        # Get selected zone id
        zone_id = self.rack_zone_combo.currentData() if hasattr(self, 'rack_zone_combo') else None
        if zone_id:
            for stop in getattr(self, 'current_stops', []) or []:
                if str(stop.get('zone_connection_id')) == str(zone_id):
                    stop_id = stop.get('stop_id')
                    name = stop.get('name', '')
                    display = f"{name} ({stop_id})" if stop_id else name
                    self.rack_stop_combo.addItem(display, stop_id)
        self.rack_stop_combo.blockSignals(False)
        # Update add button state
        self.on_rack_inputs_changed()

    def on_rack_zone_changed(self):
        """Handle zone selection change in rack tab"""
        self.populate_rack_stop_combo()
        self.on_rack_inputs_changed()

    # -------------------- SKU LOCATION (Right panel) --------------------
    def on_sku_inputs_changed(self):
        """Enable Add SKU button only when all inputs are valid"""
        zone_ok = hasattr(self, 'sku_zone_combo') and bool(self.sku_zone_combo.currentData())
        stop_ok = hasattr(self, 'sku_stop_combo') and bool(self.sku_stop_combo.currentData())
        rack_ok = hasattr(self, 'sku_rack_combo') and bool(self.sku_rack_combo.currentData())
        count_ok = hasattr(self, 'sku_count_input') and (self.sku_count_input.value() >= 1)
        can_add = zone_ok and stop_ok and rack_ok and count_ok
        if hasattr(self, 'add_sku_btn'):
            self.add_sku_btn.setEnabled(can_add)

    def populate_sku_zone_combo(self):
        """Populate SKU zone combo with zones for the selected map"""
        if not hasattr(self, 'sku_zone_combo'):
            return
        self.sku_zone_combo.blockSignals(True)
        self.sku_zone_combo.clear()
        self.sku_zone_combo.addItem("Select Zone", "")
        for zone in getattr(self, 'current_zones', []) or []:
            zone_text = f"{zone.get('from_zone', '')} -> {zone.get('to_zone', '')}"
            self.sku_zone_combo.addItem(zone_text, zone.get('id'))
        self.sku_zone_combo.blockSignals(False)

    def populate_sku_stop_combo(self):
        """Populate SKU stop combo with stops for the selected zone"""
        if not hasattr(self, 'sku_stop_combo'):
            return
        self.sku_stop_combo.blockSignals(True)
        self.sku_stop_combo.clear()
        self.sku_stop_combo.addItem("Select Stop", "")
        zone_id = self.sku_zone_combo.currentData() if hasattr(self, 'sku_zone_combo') else None
        if zone_id:
            for stop in getattr(self, 'current_stops', []) or []:
                if str(stop.get('zone_connection_id')) == str(zone_id):
                    stop_id = stop.get('stop_id')
                    name = stop.get('name', '')
                    display = f"{name} ({stop_id})" if stop_id else name
                    self.sku_stop_combo.addItem(display, stop_id)
        self.sku_stop_combo.blockSignals(False)
        self.on_sku_inputs_changed()

    def populate_sku_rack_combo(self):
        """Populate SKU rack combo with racks for the selected stop (and current map)"""
        if not hasattr(self, 'sku_rack_combo'):
            return
        self.sku_rack_combo.blockSignals(True)
        self.sku_rack_combo.clear()
        self.sku_rack_combo.addItem("Select Rack", "")
        stop_id = self.sku_stop_combo.currentData() if hasattr(self, 'sku_stop_combo') else None
        if stop_id:
            # Determine current map name
            map_name = ''
            try:
                selected_map = next((m for m in getattr(self, 'current_maps', []) if str(m.get('id')) == str(self.selected_map_id)), None)
                map_name = selected_map.get('name', '') if selected_map else ''
            except Exception:
                map_name = ''

            racks = self.csv_handler.read_csv('racks') if hasattr(self, 'csv_handler') else []
            for r in racks:
                if str(r.get('stop_id')) == str(stop_id) and (not map_name or str(r.get('map_name')) == str(map_name)):
                    rack_id = r.get('rack_id')
                    self.sku_rack_combo.addItem(rack_id, rack_id)
        self.sku_rack_combo.blockSignals(False)
        self.on_sku_inputs_changed()

    def on_sku_zone_changed(self):
        self.populate_sku_stop_combo()
        self.populate_sku_rack_combo()
        self.on_sku_inputs_changed()

    def on_sku_stop_changed(self):
        self.populate_sku_rack_combo()
        self.on_sku_inputs_changed()

    def on_add_sku_location_clicked(self):
        """Create one or more SKU locations for the selected rack and save to sku_location.csv"""
        try:
            if not self.selected_map_id:
                QMessageBox.warning(self, "No Map", "Please select a map first")
                return

            zone_id = self.sku_zone_combo.currentData()
            stop_id = self.sku_stop_combo.currentData()
            rack_id = self.sku_rack_combo.currentData()
            count = self.sku_count_input.value() if hasattr(self, 'sku_count_input') else 0

            if not zone_id or not stop_id or not rack_id or count < 1:
                QMessageBox.warning(self, "Missing Data", "Please select zone, stop, rack and enter a valid count")
                return

            # Map and Zone names
            selected_map = next((m for m in getattr(self, 'current_maps', []) if str(m.get('id')) == str(self.selected_map_id)), None)
            map_name = selected_map.get('name', 'map') if selected_map else 'map'
            zone = next((z for z in getattr(self, 'current_zones', []) if str(z.get('id')) == str(zone_id)), None)
            zone_name = f"{zone.get('from_zone', '')} -> {zone.get('to_zone', '')}" if zone else ""

            # Determine next SKU index for this rack
            existing = self.csv_handler.read_csv('sku_location') if hasattr(self, 'csv_handler') else []
            prefix = f"{rack_id}_"
            next_index = 1
            if existing:
                indices = []
                for row in existing:
                    sid = (row.get('sku_location_id') or '').strip()
                    if sid.startswith(prefix):
                        try:
                            suffix = int(sid.split('_')[-1])
                            indices.append(suffix)
                        except Exception:
                            continue
                if indices:
                    next_index = max(indices) + 1

            # Append N new rows
            created = 0
            for i in range(count):
                sku_id = f"{prefix}{next_index + i}"
                row = {
                    'sku_location_id': sku_id,
                    'map_name': map_name,
                    'zone_name': zone_name,
                    'stop_id': stop_id,
                    'rack_id': rack_id,
                }
                if self.csv_handler.append_to_csv('sku_location', row):
                    created += 1

            if created:
                QMessageBox.information(self, "Success", f"Added {created} SKU location(s) for rack {rack_id}")
                # keep count as-is for rapid repeat, but ensure button re-evaluates
                self.on_sku_inputs_changed()
            else:
                QMessageBox.warning(self, "Error", "Failed to add SKU locations")

        except Exception as e:
            self.logger.error(f"Error adding SKU locations: {e}")
            QMessageBox.critical(self, "Error", f"Failed to add SKU locations: {e}")

    def on_add_rack_clicked(self):
        """Persist a new rack entry to racks.csv with id mapname_stopid_n"""
        try:
            if not self.selected_map_id:
                QMessageBox.warning(self, "No Map", "Please select a map first")
                return
            zone_id = self.rack_zone_combo.currentData()
            stop_id = self.rack_stop_combo.currentData()
            distance_mm = self.rack_distance_input.value()
            if not zone_id or not stop_id or distance_mm <= 0:
                QMessageBox.warning(self, "Missing Data", "Please select zone and stop, and enter a valid distance")
                return

            # Get map name
            selected_map = next((m for m in self.current_maps if str(m.get('id')) == str(self.selected_map_id)), None)
            map_name = selected_map.get('name', 'map') if selected_map else 'map'

            # Determine next rack index for this map+stop
            existing = self.csv_handler.read_csv('racks')
            prefix = f"{map_name}_{stop_id}_"
            next_index = 1
            if existing:
                indices = []
                for row in existing:
                    rid = (row.get('rack_id') or '').strip()
                    if rid.startswith(prefix):
                        try:
                            suffix = int(rid.split('_')[-1])
                            indices.append(suffix)
                        except Exception:
                            continue
                if indices:
                    next_index = max(indices) + 1

            rack_id = f"{prefix}{next_index}"

            # Build zone display name (from_zone -> to_zone)
            zone = next((z for z in self.current_zones if str(z.get('id')) == str(zone_id)), None)
            zone_name = f"{zone.get('from_zone', '')} -> {zone.get('to_zone', '')}" if zone else ""

            # Prepare row matching required schema
            rack_row = {
                'rack_id': rack_id,
                'map_name': map_name,
                'zone_name': zone_name,
                'stop_id': stop_id,
                'rack_distance_mm': distance_mm,
            }

            if self.csv_handler.append_to_csv('racks', rack_row):
                QMessageBox.information(self, "Success", f"Rack added: {rack_id}")
                # Reset only the distance input to allow quick subsequent adds
                self.rack_distance_input.setValue(0)
                # Also refresh SKU rack combo so the new rack appears immediately
                if hasattr(self, 'populate_sku_rack_combo'):
                    self.populate_sku_rack_combo()
                if hasattr(self, 'on_sku_inputs_changed'):
                    self.on_sku_inputs_changed()
            else:
                QMessageBox.warning(self, "Error", "Failed to save rack entry")

        except Exception as e:
            self.logger.error(f"Error adding rack: {e}")
            QMessageBox.critical(self, "Error", f"Failed to add rack: {e}")

    def create_map_info_section(self):
        """Create map information section"""
        info_frame = QFrame()
        info_frame.setStyleSheet("""
            QFrame {
                background-color: #353535;
                border: 1px solid #555555;
                border-radius: 6px;
                padding: 15px;
            }
        """)
        info_layout = QGridLayout(info_frame)

        # Map stats
        self.map_name_label = QLabel("Map: Not Selected")
        self.map_name_label.setFont(QFont("Arial", 12, QFont.Bold))
        self.map_name_label.setStyleSheet("color: #ff6b35;")
        info_layout.addWidget(self.map_name_label, 0, 0, 1, 2)

        # Stats
        stats = [
            ("Zones:", "zones_count_label"),
            ("Stops:", "stops_count_label"),
            ("Stop Groups:", "groups_count_label"),
            ("Dimensions:", "dimensions_label")
        ]

        for i, (label_text, attr_name) in enumerate(stats):
            label = QLabel(label_text)
            label.setStyleSheet("color: #cccccc; font-weight: bold;")
            info_layout.addWidget(label, 1 + i // 2, (i % 2) * 2)

            value_label = QLabel("0")
            value_label.setStyleSheet("color: #ffffff;")
            setattr(self, attr_name, value_label)
            info_layout.addWidget(value_label, 1 + i // 2, (i % 2) * 2 + 1)

        return info_frame

    def create_zones_tab(self):
        """Create zones management tab with flexible scrollable layout"""
        # Main tab widget
        tab_widget = QWidget()
        tab_widget.setSizePolicy(tab_widget.sizePolicy().Expanding, tab_widget.sizePolicy().Expanding)
        
        # Create scroll area to contain all content
        scroll_area = QScrollArea(tab_widget)
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setFrameStyle(QFrame.NoFrame)
        scroll_area.setStyleSheet("""
            QScrollArea {
                background-color: transparent;
                border: none;
            }
            QScrollBar:vertical {
                background-color: #404040;
                width: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background-color: #ff6b35;
                border-radius: 6px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #e55a2b;
            }
            QScrollBar:horizontal {
                background-color: #404040;
                height: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:horizontal {
                background-color: #ff6b35;
                border-radius: 6px;
                min-width: 20px;
            }
            QScrollBar::handle:horizontal:hover {
                background-color: #e55a2b;
            }
        """)
        
        # Create scrollable content widget
        scroll_content = QWidget()
        scroll_content.setSizePolicy(scroll_content.sizePolicy().Expanding, scroll_content.sizePolicy().Preferred)
        
        # Main content layout with flexible sizing
        main_layout = QVBoxLayout(scroll_content)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(20)

        # Add warning message for new maps without zones
        self.zone_warning_label = QLabel("⚠️ Configure zones first to enable Stop Management and Map Settings tabs")
        self.zone_warning_label.setStyleSheet("""
            QLabel {
                background-color: #ff6b35;
                color: white;
                padding: 10px;
                border-radius: 6px;
                font-weight: bold;
                text-align: center;
            }
        """)
        self.zone_warning_label.setVisible(False)  # Initially hidden
        main_layout.addWidget(self.zone_warning_label)

        # Main section - Zone management with map on right and zone controls at bottom
        main_section = self.create_responsive_zone_section()
        main_layout.addWidget(main_section)
        
        # Add some bottom padding for better scrolling
        main_layout.addSpacing(20)

        # Set the scroll content
        scroll_area.setWidget(scroll_content)
        
        # Layout for the main tab widget
        tab_layout = QVBoxLayout(tab_widget)
        tab_layout.setContentsMargins(0, 0, 0, 0)
        tab_layout.addWidget(scroll_area)

        return tab_widget

    def create_responsive_zone_section(self):
        """Create responsive zone section with form on left, map on right, and table at bottom"""
        section_frame = QFrame()
        section_frame.setStyleSheet("""
            QFrame {
                background-color: transparent;
                border: none;
            }
        """)
        section_frame.setSizePolicy(section_frame.sizePolicy().Expanding, section_frame.sizePolicy().Preferred)
        
        # Main layout - vertical to stack top and bottom sections
        main_layout = QVBoxLayout(section_frame)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(15)
        
        # Top section - horizontal layout with form on left and map on right
        top_section = QFrame()
        top_section.setStyleSheet("QFrame { background-color: transparent; border: none; }")
        top_layout = QHBoxLayout(top_section)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(15)
        
        # Left side - Zone creation form
        left_panel = self.create_zone_creation_form()
        left_panel.setMinimumWidth(400)  # Ensure good usable width for form
        left_panel.setSizePolicy(left_panel.sizePolicy().Expanding, left_panel.sizePolicy().Preferred)
        top_layout.addWidget(left_panel, 1)  # Equal weight
        
        # Right side - Interactive map visualization
        right_panel = self.create_flexible_embedded_map_section()
        right_panel.setMinimumWidth(500)  # Ensure good usable width for map
        right_panel.setSizePolicy(right_panel.sizePolicy().Expanding, right_panel.sizePolicy().Preferred)
        top_layout.addWidget(right_panel, 1)  # Equal weight
        
        main_layout.addWidget(top_section)
        
        # Bottom section - Zone connections table (full width)
        bottom_panel = self.create_zones_table_section()
        bottom_panel.setMinimumHeight(300)  # Ensure enough height for table
        bottom_panel.setSizePolicy(bottom_panel.sizePolicy().Expanding, bottom_panel.sizePolicy().Preferred)
        main_layout.addWidget(bottom_panel)
        
        return section_frame
    
    def create_flexible_embedded_map_section(self):
        """Create flexible embedded map section with dynamic sizing"""
        map_section = QFrame()
        map_section.setStyleSheet("""
            QFrame {
                background-color: #353535;
                border: 1px solid #555555;
                border-radius: 6px;
                padding: 15px;
            }
        """)
        map_section.setSizePolicy(map_section.sizePolicy().Expanding, map_section.sizePolicy().Preferred)
        
        layout = QVBoxLayout(map_section)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # Header with dynamic info
        header_layout = QHBoxLayout()
        
        title = QLabel("🗺️ Interactive Map Visualization")
        title.setFont(QFont("Arial", 14, QFont.Bold))
        title.setStyleSheet("color: #ff6b35;")
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        # Status and info labels
        self.embedded_map_status = QLabel("Ready")
        self.embedded_map_status.setStyleSheet("color: #10B981; font-size: 11px; font-weight: bold;")
        header_layout.addWidget(self.embedded_map_status)
        
        self.embedded_map_info = QLabel("Click zones to select, updates automatically")
        self.embedded_map_info.setStyleSheet("color: #888888; font-size: 10px; font-style: italic;")
        header_layout.addWidget(self.embedded_map_info)
        
        layout.addLayout(header_layout)
        
        # Flexible embedded map viewer
        self.embedded_map_viewer = MapViewerWidget(self.api_client, self.csv_handler)
        # Set flexible sizing constraints with explicit visibility
        self.embedded_map_viewer.setVisible(True)  # Explicitly set visibility
        self.embedded_map_viewer.setMinimumHeight(250)  # Minimum for usability
        self.embedded_map_viewer.setMaximumHeight(500)  # Maximum to prevent oversizing
        self.embedded_map_viewer.setSizePolicy(
            self.embedded_map_viewer.sizePolicy().Expanding, 
            self.embedded_map_viewer.sizePolicy().Expanding
        )
        
        # Connect signals for interactive feedback
        self.embedded_map_viewer.zone_selected.connect(self.on_embedded_map_zone_selected)
        
        # Add widget and force a show() after adding to layout
        layout.addWidget(self.embedded_map_viewer)
        self.embedded_map_viewer.show()
        
        # Interactive controls footer
        controls_layout = QHBoxLayout()
        
        # Quick action buttons
        refresh_map_btn = QPushButton("🔄 Refresh")
        refresh_map_btn.clicked.connect(self.refresh_embedded_map)
        refresh_map_btn.setStyleSheet("""
            QPushButton {
                background-color: #555555;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #666666;
            }
        """)
        controls_layout.addWidget(refresh_map_btn)
        
        fit_map_btn = QPushButton("📐 Fit to View")
        fit_map_btn.clicked.connect(self.fit_embedded_map)
        fit_map_btn.setStyleSheet("""
            QPushButton {
                background-color: #555555;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #666666;
            }
        """)
        controls_layout.addWidget(fit_map_btn)
        
        controls_layout.addStretch()
        
        # Map info display
        self.map_elements_info = QLabel("No data")
        self.map_elements_info.setStyleSheet("color: #cccccc; font-size: 10px;")
        controls_layout.addWidget(self.map_elements_info)
        
        layout.addLayout(controls_layout)
        
        return map_section
    
    def refresh_embedded_map(self):
        """Refresh the embedded map viewer"""
        if hasattr(self, 'embedded_map_viewer') and self.selected_map_id:
            self.embedded_map_viewer.set_map_data(
                self.selected_map_id, 
                self.current_zones, 
                self.current_stops, 
                self.current_stop_groups
            )
            self.update_embedded_map_info()
            if hasattr(self, 'embedded_map_status'):
                self.embedded_map_status.setText("Updated")
                # Reset status after a delay
                QTimer.singleShot(2000, lambda: self.embedded_map_status.setText("Ready"))
    
    def fit_embedded_map(self):
        """Fit the embedded map to the view"""
        if hasattr(self, 'embedded_map_viewer'):
            # Call fit view method if available
            if hasattr(self.embedded_map_viewer, 'fit_to_view'):
                self.embedded_map_viewer.fit_to_view()
            if hasattr(self, 'embedded_map_status'):
                self.embedded_map_status.setText("Fitted")
                QTimer.singleShot(1500, lambda: self.embedded_map_status.setText("Ready"))
    
    def update_embedded_map_info(self):
        """Update the embedded map information display"""
        if hasattr(self, 'map_elements_info'):
            zones_count = len(self.current_zones)
            stops_count = len(self.current_stops)
            info_text = f"{zones_count} zones, {stops_count} stops"
            self.map_elements_info.setText(info_text)

    def create_embedded_map_section(self):
        """Create embedded map visualization section for zone management"""
        map_section = QFrame()
        map_section.setStyleSheet("""
            QFrame {
                background-color: #353535;
                border: 1px solid #555555;
                border-radius: 6px;
                padding: 15px;
            }
        """)
        layout = QVBoxLayout(map_section)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # Title with info
        header_layout = QHBoxLayout()
        
        title = QLabel("🗺️ Map Visualization")
        title.setFont(QFont("Arial", 14, QFont.Bold))
        title.setStyleSheet("color: #ff6b35;")
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        # Live update info
        self.embedded_map_info = QLabel("Map updates automatically when zones are created")
        self.embedded_map_info.setStyleSheet("color: #888888; font-size: 11px; font-style: italic;")
        header_layout.addWidget(self.embedded_map_info)
        
        layout.addLayout(header_layout)

        # Embedded map viewer (compact version)
        self.embedded_map_viewer = MapViewerWidget(self.api_client, self.csv_handler)
        self.embedded_map_viewer.setMinimumHeight(300)
        self.embedded_map_viewer.setMaximumHeight(400)
        
        # Connect zone selection from embedded map to form
        self.embedded_map_viewer.zone_selected.connect(self.on_embedded_map_zone_selected)
        
        layout.addWidget(self.embedded_map_viewer)
        
        return map_section

    def on_embedded_map_zone_selected(self, zone_data):
        """Handle zone selection from embedded map viewer"""
        # Find the zone in our current zones list and select it in the table
        zone_id = zone_data.get('id')
        if zone_id:
            for i, zone in enumerate(self.current_zones):
                if str(zone.get('id')) == str(zone_id):
                    # Select the corresponding row in the zones table
                    self.zones_table.table.selectRow(i)
                    # Update the form with zone data
                    self.on_zone_selected(i)
                    break

    def create_zone_management_panel(self):
        """Create combined zone management panel with forms and table"""
        panel = QFrame()
        panel.setStyleSheet("""
            QFrame {
                background-color: #353535;
                border: 1px solid #555555;
                border-radius: 6px;
                padding: 20px;
            }
        """)
        layout = QVBoxLayout(panel)
        
        # Title
        title = QLabel("Zone Connections Management")
        title.setFont(QFont("Arial", 14, QFont.Bold))
        title.setStyleSheet("color: #ff6b35; margin-bottom: 15px;")
        layout.addWidget(title)
        
        # Zone creation form
        form_section = self.create_zone_creation_form()
        layout.addWidget(form_section)
        
        # Zone list table
        table_section = self.create_zones_table_section()
        layout.addWidget(table_section)
        
        return panel
    
    def create_zone_creation_form(self):
        """Create zone creation form section"""
        form_frame = QFrame()
        form_frame.setStyleSheet("""
            QFrame {
                background-color: #404040;
                border: 1px solid #666666;
                border-radius: 6px;
                padding: 15px;
                margin-bottom: 15px;
            }
        """)
        form_layout = QVBoxLayout(form_frame)
        
        # Sub-title
        subtitle = QLabel("Create New Zone Connection")
        subtitle.setFont(QFont("Arial", 12, QFont.Bold))
        subtitle.setStyleSheet("color: #ffffff; margin-bottom: 10px;")
        form_layout.addWidget(subtitle)
        
        # Form inputs in grid layout
        inputs_layout = QFormLayout()
        
        # From Zone
        self.from_zone_input = QLineEdit()
        self.from_zone_input.setPlaceholderText("e.g., Zone A, Storage 1")
        self.apply_input_style(self.from_zone_input)
        inputs_layout.addRow("From Zone:", self.from_zone_input)
        
        # To Zone
        self.to_zone_input = QLineEdit()
        self.to_zone_input.setPlaceholderText("e.g., Zone B, Packing 1")
        self.apply_input_style(self.to_zone_input)
        inputs_layout.addRow("To Zone:", self.to_zone_input)
        
        # Distance and direction in same row
        distance_direction_layout = QHBoxLayout()
        
        self.magnitude_input = QDoubleSpinBox()
        self.magnitude_input.setRange(0.1, 1000.0)
        self.magnitude_input.setValue(50.0)
        self.magnitude_input.setSuffix(" meters")
        self.magnitude_input.setDecimals(1)
        self.apply_input_style(self.magnitude_input)
        distance_direction_layout.addWidget(self.magnitude_input)
        
        self.direction_combo = QComboBox()
        directions = ["north", "south", "east", "west"]
        self.direction_combo.addItems(directions)
        self.apply_combo_style(self.direction_combo)
        distance_direction_layout.addWidget(self.direction_combo)
        
        inputs_layout.addRow("Distance & Direction:", distance_direction_layout)
        
        # Zone Type
        self.zone_type_combo = QComboBox()
        zone_types = ["storage", "picking", "packing", "shipping", "receiving", "maintenance", "quality_control"]
        self.zone_type_combo.addItems(zone_types)
        self.apply_combo_style(self.zone_type_combo)
        inputs_layout.addRow("Zone Type:", self.zone_type_combo)
        
        form_layout.addLayout(inputs_layout)
        
        # Create button
        create_zone_btn = QPushButton("➕ Create Zone Connection")
        create_zone_btn.clicked.connect(self.create_zone_connection)
        create_zone_btn.setStyleSheet("""
            QPushButton {
                background-color: #ff6b35;
                color: white;
                border: none;
                padding: 12px;
                border-radius: 6px;
                font-weight: bold;
                margin-top: 15px;
            }
            QPushButton:hover {
                background-color: #e55a2b;
            }
        """)
        form_layout.addWidget(create_zone_btn)
        
        return form_frame
    
    def create_zones_table_section(self):
        """Create zones table section with improved visibility"""
        table_frame = QFrame()
        table_frame.setStyleSheet("""
            QFrame {
                background-color: #404040;
                border: 1px solid #666666;
                border-radius: 6px;
                padding: 10px;
            }
        """)
        table_frame.setSizePolicy(table_frame.sizePolicy().Expanding, table_frame.sizePolicy().Expanding)
        table_layout = QVBoxLayout(table_frame)
        table_layout.setSpacing(8)
        
        # Compact header with title and search on same row
        header_layout = QHBoxLayout()
        header_layout.setSpacing(15)
        
        # Table title
        table_title = QLabel("Zone Connections")
        table_title.setFont(QFont("Arial", 12, QFont.Bold))
        table_title.setStyleSheet("color: #ffffff;")
        header_layout.addWidget(table_title)
        
        header_layout.addStretch()
        
        # Compact search field
        search_label = QLabel("Search:")
        search_label.setStyleSheet("color: #cccccc; font-size: 11px;")
        header_layout.addWidget(search_label)
        
        # Custom search input for the table
        self.zones_search_input = QLineEdit()
        self.zones_search_input.setPlaceholderText("Filter zones...")
        self.zones_search_input.setMaximumWidth(150)
        self.zones_search_input.setStyleSheet("""
            QLineEdit {
                background-color: #555555;
                border: 1px solid #777777;
                padding: 4px 8px;
                border-radius: 4px;
                color: #ffffff;
                font-size: 11px;
            }
            QLineEdit:focus {
                border: 1px solid #ff6b35;
            }
        """)
        self.zones_search_input.textChanged.connect(self.filter_zones_table)
        header_layout.addWidget(self.zones_search_input)
        
        table_layout.addLayout(header_layout)
        
        # Zones table with increased height
        self.zones_table = DataTableWidget([
            "From Zone", "To Zone", "Distance", "Direction", "Type", "Created"
        ], searchable=False, selectable=True)  # Disable built-in search since we have custom
        self.zones_table.row_selected.connect(self.on_zone_selected)
        
        # Set minimum height for better visibility
        self.zones_table.setMinimumHeight(250)
        self.zones_table.setSizePolicy(self.zones_table.sizePolicy().Expanding, self.zones_table.sizePolicy().Expanding)
        
        table_layout.addWidget(self.zones_table)
        
        # Compact zone actions
        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(10)
        
        edit_zone_btn = QPushButton("✏️ Edit")
        edit_zone_btn.clicked.connect(self.edit_selected_zone)
        edit_zone_btn.setMaximumWidth(80)
        edit_zone_btn.setStyleSheet("""
            QPushButton {
                background-color: #555555;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
                font-weight: bold;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #666666;
            }
        """)
        actions_layout.addWidget(edit_zone_btn)
        
        delete_zone_btn = QPushButton("🗑️ Delete")
        delete_zone_btn.clicked.connect(self.delete_selected_zone)
        delete_zone_btn.setMaximumWidth(80)
        delete_zone_btn.setStyleSheet("""
            QPushButton {
                background-color: #dc3545;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
                font-weight: bold;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #c82333;
            }
        """)
        actions_layout.addWidget(delete_zone_btn)
        
        actions_layout.addStretch()
        
        # Row count display
        self.zones_count_display = QLabel("0 zones")
        self.zones_count_display.setStyleSheet("color: #888888; font-size: 10px;")
        actions_layout.addWidget(self.zones_count_display)
        
        table_layout.addLayout(actions_layout)
        
        return table_frame
    
    def create_zone_creation_panel(self):
        """Create zone creation panel"""
        panel = QFrame()
        panel.setStyleSheet("""
            QFrame {
                background-color: #353535;
                border: 1px solid #555555;
                border-radius: 6px;
                padding: 20px;
            }
        """)
        layout = QVBoxLayout(panel)

        # Title
        title = QLabel("Create Zone Connection")
        title.setFont(QFont("Arial", 14, QFont.Bold))
        title.setStyleSheet("color: #ff6b35; margin-bottom: 15px;")
        layout.addWidget(title)

        # Form
        form_layout = QFormLayout()

        # From Zone
        self.from_zone_input = QLineEdit()
        self.from_zone_input.setPlaceholderText("e.g., Zone A, Storage 1")
        self.apply_input_style(self.from_zone_input)
        form_layout.addRow("From Zone:", self.from_zone_input)

        # To Zone
        self.to_zone_input = QLineEdit()
        self.to_zone_input.setPlaceholderText("e.g., Zone B, Packing 1")
        self.apply_input_style(self.to_zone_input)
        form_layout.addRow("To Zone:", self.to_zone_input)

        # Distance
        self.magnitude_input = QDoubleSpinBox()
        self.magnitude_input.setRange(0.1, 1000.0)
        self.magnitude_input.setValue(50.0)
        self.magnitude_input.setSuffix(" meters")
        self.magnitude_input.setDecimals(1)
        self.apply_input_style(self.magnitude_input)
        form_layout.addRow("Distance:", self.magnitude_input)

        # Direction
        self.direction_combo = QComboBox()
        directions = ["north", "south", "east", "west"]
        self.direction_combo.addItems(directions)
        self.apply_combo_style(self.direction_combo)
        form_layout.addRow("Direction:", self.direction_combo)

        # Zone Type
        self.zone_type_combo = QComboBox()
        zone_types = ["storage", "picking", "packing", "shipping", "receiving", "maintenance", "quality_control"]
        self.zone_type_combo.addItems(zone_types)
        self.apply_combo_style(self.zone_type_combo)
        form_layout.addRow("Zone Type:", self.zone_type_combo)

        layout.addLayout(form_layout)

        # Create button
        create_zone_btn = QPushButton("➕ Create Zone Connection")
        create_zone_btn.clicked.connect(self.create_zone_connection)
        create_zone_btn.setStyleSheet("""
            QPushButton {
                background-color: #ff6b35;
                color: white;
                border: none;
                padding: 12px;
                border-radius: 6px;
                font-weight: bold;
                margin-top: 15px;
            }
            QPushButton:hover {
                background-color: #e55a2b;
            }
        """)
        layout.addWidget(create_zone_btn)

        layout.addStretch()
        return panel

    def create_zones_list_panel(self):
        """Create zones list panel"""
        panel = QFrame()
        panel.setStyleSheet("""
            QFrame {
                background-color: #353535;
                border: 1px solid #555555;
                border-radius: 6px;
                padding: 20px;
            }
        """)
        layout = QVBoxLayout(panel)

        # Title
        title = QLabel("Zone Connections")
        title.setFont(QFont("Arial", 14, QFont.Bold))
        title.setStyleSheet("color: #ff6b35; margin-bottom: 15px;")
        layout.addWidget(title)

        # Zones table
        self.zones_table = DataTableWidget([
            "From Zone", "To Zone", "Distance", "Direction", "Type", "Created"
        ], searchable=True, selectable=True)
        self.zones_table.row_selected.connect(self.on_zone_selected)
        layout.addWidget(self.zones_table)

        # Zone actions
        actions_layout = QHBoxLayout()

        edit_zone_btn = QPushButton("✏️ Edit Zone")
        edit_zone_btn.clicked.connect(self.edit_selected_zone)
        self.apply_button_style(edit_zone_btn)
        actions_layout.addWidget(edit_zone_btn)

        delete_zone_btn = QPushButton("🗑️ Delete Zone")
        delete_zone_btn.clicked.connect(self.delete_selected_zone)
        delete_zone_btn.setStyleSheet("""
            QPushButton {
                background-color: #dc3545;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #c82333;
            }
        """)
        actions_layout.addWidget(delete_zone_btn)

        layout.addLayout(actions_layout)
        return panel

    def create_stops_tab(self):
        """Create stops management tab with scrollable content"""
        # Create main tab widget
        tab_widget = QWidget()
        tab_widget.setSizePolicy(tab_widget.sizePolicy().Expanding, tab_widget.sizePolicy().Expanding)
        
        # Create scroll area to contain all content
        scroll_area = QScrollArea(tab_widget)
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setFrameStyle(QFrame.NoFrame)
        scroll_area.setStyleSheet("""
            QScrollArea {
                background-color: transparent;
                border: none;
            }
            QScrollBar:vertical {
                background-color: #404040;
                width: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background-color: #ff6b35;
                border-radius: 6px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #e55a2b;
            }
        """)
        
        # Create scrollable content widget
        scroll_content = QWidget()
        scroll_content.setSizePolicy(scroll_content.sizePolicy().Expanding, scroll_content.sizePolicy().Preferred)
        
        # Main content layout
        content_layout = QVBoxLayout(scroll_content)
        content_layout.setContentsMargins(15, 15, 15, 15)
        content_layout.setSpacing(20)

        # Stop generation controls section
        controls_section = self.create_stop_controls_section()
        controls_section.setMinimumHeight(200)
        content_layout.addWidget(controls_section)
        
        # Stop Details section - give it more space and allow expansion
        stop_details_section = self.create_stop_details_section()
        content_layout.addWidget(stop_details_section, 1)  # Add stretch factor of 1


        # Set the scroll content
        scroll_area.setWidget(scroll_content)
        
        # Layout for the main tab widget
        tab_layout = QVBoxLayout(tab_widget)
        tab_layout.setContentsMargins(0, 0, 0, 0)
        tab_layout.addWidget(scroll_area)

        return tab_widget


    def create_settings_tab(self):
        """Create map settings tab"""
        tab_widget = QWidget()
        layout = QVBoxLayout(tab_widget)
        layout.setContentsMargins(20, 20, 20, 20)

        # Map properties
        properties_section = QFrame()
        properties_section.setStyleSheet("""
            QFrame {
                background-color: #353535;
                border: 1px solid #555555;
                border-radius: 6px;
                padding: 20px;
            }
        """)
        properties_layout = QFormLayout(properties_section)

        # Title
        title = QLabel("Map Properties")
        title.setFont(QFont("Arial", 14, QFont.Bold))
        title.setStyleSheet("color: #ff6b35; margin-bottom: 15px;")
        properties_layout.addRow(title)

        # Map settings
        self.map_name_input = QLineEdit()
        self.map_name_input.setPlaceholderText("Enter map name")
        self.apply_input_style(self.map_name_input)
        properties_layout.addRow("Map Name:", self.map_name_input)

        self.map_description_input = QTextEdit()
        self.map_description_input.setPlaceholderText("Enter map description")
        self.map_description_input.setMaximumHeight(80)
        self.apply_input_style(self.map_description_input)
        properties_layout.addRow("Description:", self.map_description_input)

        dimensions_layout = QHBoxLayout()

        self.map_width_input = QSpinBox()
        self.map_width_input.setRange(500, 5000)
        self.map_width_input.setValue(1000)
        self.map_width_input.setSuffix(" px")
        self.apply_input_style(self.map_width_input)
        dimensions_layout.addWidget(self.map_width_input)

        dimensions_layout.addWidget(QLabel("×"))

        self.map_height_input = QSpinBox()
        self.map_height_input.setRange(400, 4000)
        self.map_height_input.setValue(800)
        self.map_height_input.setSuffix(" px")
        self.apply_input_style(self.map_height_input)
        dimensions_layout.addWidget(self.map_height_input)

        properties_layout.addRow("Dimensions:", dimensions_layout)

        layout.addWidget(properties_section)

        # Save button
        save_btn = QPushButton("💾 Save Map Settings")
        save_btn.clicked.connect(self.save_map_settings)
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #10B981;
                color: white;
                border: none;
                padding: 12px 24px;
                border-radius: 6px;
                font-weight: bold;
                margin-top: 20px;
            }
            QPushButton:hover {
                background-color: #059669;
            }
        """)
        layout.addWidget(save_btn)

        layout.addStretch()
        return tab_widget

    def create_action_buttons(self, parent_layout):
        """Create action buttons"""
        action_layout = QHBoxLayout()

        # Refresh button
        refresh_btn = QPushButton("🔄 Refresh Data")
        refresh_btn.clicked.connect(self.refresh_data)
        self.apply_button_style(refresh_btn)
        action_layout.addWidget(refresh_btn)

        # Sync button
        sync_btn = QPushButton("🔄 Sync with API")
        sync_btn.clicked.connect(self.sync_with_api)
        self.apply_button_style(sync_btn)
        action_layout.addWidget(sync_btn)

        action_layout.addStretch()

        # Delete map button
        self.delete_map_btn = QPushButton("🗑️ Delete Current Map")
        self.delete_map_btn.clicked.connect(self.delete_current_map)
        self.delete_map_btn.setEnabled(False)
        self.delete_map_btn.setStyleSheet("""
            QPushButton {
                background-color: #dc3545;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 6px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #c82333;
            }
            QPushButton:disabled {
                background-color: #555555;
                color: #888888;
            }
        """)
        action_layout.addWidget(self.delete_map_btn)

        parent_layout.addLayout(action_layout)

    def apply_combo_style(self, combo):
        """Apply combobox styling with visible dropdown arrow"""
        combo.setStyleSheet("""
            QComboBox {
                background-color: #404040;
                border: 1px solid #555555;
                padding: 8px 25px 8px 8px;
                border-radius: 4px;
                color: #ffffff;
                min-width: 150px;
            }
            QComboBox:focus {
                border: 2px solid #ff6b35;
            }
            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 20px;
                border-left: 1px solid #666666;
                background-color: #555555;
                border-top-right-radius: 4px;
                border-bottom-right-radius: 4px;
            }
            QComboBox::drop-down:hover {
                background-color: #666666;
            }
            QComboBox::down-arrow {
                image: none;
                border: 2px solid #ffffff;
                width: 6px;
                height: 6px;
                border-top: none;
                border-right: none;
                transform: rotate(45deg);
                margin: 2px;
            }
            QComboBox::down-arrow:hover {
                border-color: #ff6b35;
            }
            QComboBox QAbstractItemView {
                background-color: #404040;
                color: #ffffff;
                selection-background-color: #ff6b35;
                border: 1px solid #555555;
                outline: none;
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

    def apply_input_style(self, widget):
        """Apply input styling"""
        widget.setStyleSheet("""
            QLineEdit, QSpinBox, QDoubleSpinBox, QTextEdit {
                background-color: #404040;
                border: 1px solid #555555;
                padding: 8px;
                border-radius: 4px;
                color: #ffffff;
            }
            QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QTextEdit:focus {
                border: 2px solid #ff6b35;
            }
        """)

    def refresh_data(self):
        """Refresh all map data"""
        # Store current tab index to preserve it after refresh
        current_tab_index = self.tab_widget.currentIndex()
        self.logger.debug(f"Refreshing data - current tab index: {current_tab_index}")
        
        self.load_maps()
        if self.selected_map_id:
            self.load_map_data(self.selected_map_id)
        
        # Restore the current tab index to prevent automatic navigation to overview tab
        if current_tab_index >= 0 and current_tab_index < self.tab_widget.count():
            self.tab_widget.setCurrentIndex(current_tab_index)
            self.logger.debug(f"Restored tab index to: {current_tab_index}")
        else:
            self.logger.debug(f"Could not restore tab index: {current_tab_index} (valid range: 0-{self.tab_widget.count()-1})")

    def load_maps(self):
        """Load available maps"""
        try:
            # Try API first, then fallback to CSV
            if self.api_client.is_authenticated():
                response = self.maps_api.list_maps()
                if 'error' not in response:
                    maps_data = response.get('results', response) if isinstance(response, dict) else response
                    self.current_maps = maps_data
                    self.populate_map_selector()
                    return

            # Fallback to CSV
            maps = self.csv_handler.read_csv('maps')
            self.current_maps = maps
            self.populate_map_selector()

        except Exception as e:
            self.logger.error(f"Error loading maps: {e}")
            self.current_maps = []
            self.populate_map_selector()

    def populate_map_selector(self):
        """Populate map selector"""
        current_selection = self.map_selector.currentData()
        current_index = self.map_selector.currentIndex()
        self.map_selector.clear()
        self.map_selector.addItem("No Map Selected", "")

        for map_item in self.current_maps:
            map_name = map_item.get('name', 'Unnamed Map')
            map_id = map_item.get('id')
            self.map_selector.addItem(map_name, map_id)

        # Restore selection if possible
        if current_selection:
            index = self.map_selector.findData(current_selection)
            if index >= 0:
                self.map_selector.setCurrentIndex(index)
            else:
                # If the previously selected map is not found, keep the current tab
                # and don't trigger the on_map_selected method by temporarily blocking signals
                self.map_selector.blockSignals(True)
                self.map_selector.setCurrentIndex(0)  # Set to "No Map Selected"
                self.map_selector.blockSignals(False)
                # Don't call update_tab_accessibility here to preserve current tab
        else:
            # If no previous selection, just set to first item without triggering signals
            self.map_selector.blockSignals(True)
            self.map_selector.setCurrentIndex(0)
            self.map_selector.blockSignals(False)

    def on_map_selected(self):
        """Handle map selection"""
        map_id = self.map_selector.currentData()
        if map_id:
            self.selected_map_id = map_id
            self.load_map_data(map_id)
            self.delete_map_btn.setEnabled(True)
            self.populate_zones_combo()
            self.update_tab_accessibility()
        else:
            self.selected_map_id = None
            self.delete_map_btn.setEnabled(False)
            self.clear_map_data()
            self.update_tab_accessibility()

    def populate_zones_combo(self):
        """Populate zones combo for stop generation"""
        self.zone_for_stops_combo.clear()
        self.zone_for_stops_combo.addItem("Select Zone", "")

        for zone in self.current_zones:
            zone_text = f"{zone.get('from_zone', '')} → {zone.get('to_zone', '')}"
            self.zone_for_stops_combo.addItem(zone_text, zone.get('id'))

    def load_map_data(self, map_id):
        """Load data for specific map"""
        try:
            # Load zones, stops, and stop groups for this map
            zones = self.csv_handler.read_csv('zones')
            self.current_zones = [z for z in zones if str(z.get('map_id')) == str(map_id)]

            stops = self.csv_handler.read_csv('stops')
            self.current_stops = [s for s in stops if str(s.get('map_id')) == str(map_id)]

            stop_groups = self.csv_handler.read_csv('stop_groups')
            self.current_stop_groups = [sg for sg in stop_groups if str(sg.get('map_id')) == str(map_id)]

            # Update UI
            self.update_map_info()
            self.populate_zones_table()
            self.populate_zones_combo()
            self.refresh_stop_details_table()

            # Refresh rack configuration combos if tab exists
            if hasattr(self, 'populate_rack_zone_combo'):
                self.populate_rack_zone_combo()
            if hasattr(self, 'populate_rack_stop_combo'):
                self.populate_rack_stop_combo()
            # Refresh Add SKU Location combos if tab exists
            if hasattr(self, 'populate_sku_zone_combo'):
                self.populate_sku_zone_combo()
            if hasattr(self, 'populate_sku_stop_combo'):
                self.populate_sku_stop_combo()
            if hasattr(self, 'populate_sku_rack_combo'):
                self.populate_sku_rack_combo()

            # Get map dimensions from settings
            map_width = self.map_width_input.value() if hasattr(self, 'map_width_input') else 1000
            map_height = self.map_height_input.value() if hasattr(self, 'map_height_input') else 800
            # Update map viewer with explicit dimensions
            self.map_viewer.set_map_data(
                zones=self.current_zones,
                stops=self.current_stops,
                stop_groups=self.current_stop_groups,
                map_width=map_width,
                map_height=map_height
            )
            
            # Update embedded map viewer (if it exists)
            if hasattr(self, 'embedded_map_viewer'):
                self.embedded_map_viewer.set_map_data(
                    zones=self.current_zones,
                    stops=self.current_stops,
                    stop_groups=self.current_stop_groups,
                    map_width=map_width,
                    map_height=map_height
                )
                self.update_embedded_map_info()

            # Update settings
            selected_map = next((m for m in self.current_maps if str(m.get('id')) == str(map_id)), None)
            if selected_map:
                self.map_name_input.setText(selected_map.get('name', ''))
                self.map_description_input.setPlainText(selected_map.get('description', ''))
                self.map_width_input.setValue(int(selected_map.get('width', 1000)))
                self.map_height_input.setValue(int(selected_map.get('height', 800)))

        except Exception as e:
            self.logger.error(f"Error loading map data: {e}")

    def update_map_info(self):
        """Update map information display"""
        if self.selected_map_id:
            selected_map = next((m for m in self.current_maps if str(m.get('id')) == str(self.selected_map_id)), None)
            if selected_map:
                self.map_name_label.setText(f"Map: {selected_map.get('name', 'Unnamed')}")

            self.zones_count_label.setText(str(len(self.current_zones)))
            self.stops_count_label.setText(str(len(self.current_stops)))
            self.groups_count_label.setText(str(len(self.current_stop_groups)))

            width = self.map_width_input.value() if hasattr(self, 'map_width_input') else 1000
            height = self.map_height_input.value() if hasattr(self, 'map_height_input') else 800
            self.dimensions_label.setText(f"{width} × {height} px")
        else:
            self.map_name_label.setText("Map: Not Selected")
            self.zones_count_label.setText("0")
            self.stops_count_label.setText("0")
            self.groups_count_label.setText("0")
            self.dimensions_label.setText("- × - px")

    def populate_zones_table(self):
        """Populate zones table"""
        # Prepare all data first
        table_data = []
        for zone in self.current_zones:
            # Get direction and display it properly
            direction = zone.get('direction', 'north')  # Default to north for backward compatibility
            direction_display = direction.title() if direction else 'North'
            
            row_data = [
                zone.get('from_zone', ''),
                zone.get('to_zone', ''),
                f"{zone.get('magnitude', 0)} m",
                direction_display,
                zone.get('zone_type', '').title(),
                # Format date with time if available
                self.format_datetime(zone.get('created_at', ''))
            ]
            table_data.append(row_data)
        
        # Set all data at once - this will automatically optimize column widths
        self.zones_table.set_data(table_data)
        
        # Update zones count
        if hasattr(self, 'zones_count_display'):
            self.zones_count_display.setText(f"{len(self.current_zones)} zones")
        
        # Clear search when repopulating
        if hasattr(self, 'zones_search_input'):
            self.zones_search_input.clear()
    
    def format_datetime(self, date_value):
        """Format datetime string to show both date and time"""
        if not date_value:
            return 'N/A'
        
        try:
            # Format the date with time for better display
            dt = datetime.fromisoformat(date_value.replace('Z', '+00:00'))
            return dt.strftime('%Y-%m-%d %H:%M:%S')
        except:
            # If parsing fails, try to include time if available
            if len(date_value) >= 19:  # Length of 'YYYY-MM-DD HH:MM:SS'
                return date_value[:19]
            else:
                return date_value
    
    def filter_zones_table(self, search_text):
        """Filter zones table based on search text"""
        search_text = search_text.lower().strip()
        
        if not search_text:
            # If search is empty, show all zones
            self.populate_zones_table()
            return
        
        # Filter zones based on search text
        filtered_zones = []
        for zone in self.current_zones:
            # Search in various fields
            searchable_text = ' '.join([
                zone.get('from_zone', '').lower(),
                zone.get('to_zone', '').lower(),
                str(zone.get('magnitude', '')).lower(),
                zone.get('direction', '').lower(),
                zone.get('zone_type', '').lower()
            ])
            
            if search_text in searchable_text:
                filtered_zones.append(zone)
        
        # Prepare filtered data for display
        table_data = []
        for zone in filtered_zones:
            direction = zone.get('direction', 'north')
            direction_display = direction.title() if direction else 'North'
            
            row_data = [
                zone.get('from_zone', ''),
                zone.get('to_zone', ''),
                f"{zone.get('magnitude', 0)} m",
                direction_display,
                zone.get('zone_type', '').title(),
                self.format_datetime(zone.get('created_at', ''))
            ]
            table_data.append(row_data)
        
        # Update table with filtered data
        self.zones_table.set_data(table_data)
        
        # Update zones count to show filtered results
        if hasattr(self, 'zones_count_display'):
            total_zones = len(self.current_zones)
            filtered_count = len(filtered_zones)
            if filtered_count != total_zones:
                self.zones_count_display.setText(f"{filtered_count}/{total_zones} zones")
            else:
                self.zones_count_display.setText(f"{total_zones} zones")

    # Populate stops data method removed as part of UI cleanup

    def clear_map_data(self):
        """Clear all map data"""
        self.current_zones = []
        self.current_stops = []
        self.current_stop_groups = []
        self.zones_table.clear_data()
        self.zone_for_stops_combo.clear()
        self.zone_for_stops_combo.addItem("Select Zone", "")
        self.map_viewer.clear_map()
        
        # Clear embedded map viewer (if it exists)
        if hasattr(self, 'embedded_map_viewer'):
            self.embedded_map_viewer.clear_map()
            
        self.update_map_info()
        self.refresh_stop_details_table()

    def create_new_map(self):
        """Create new map with improved dialog"""
        from PyQt5.QtWidgets import QDialog, QVBoxLayout, QFormLayout, QLineEdit, QTextEdit, QSpinBox, QPushButton, \
            QHBoxLayout

        dialog = QDialog(self)
        dialog.setWindowTitle("Create New Map")
        dialog.setModal(True)
        dialog.setFixedSize(400, 350)
        dialog.setStyleSheet("""
            QDialog {
                background-color: #2b2b2b;
                color: #ffffff;
            }
        """)

        layout = QVBoxLayout(dialog)
        form_layout = QFormLayout()

        # Map name
        name_input = QLineEdit()
        name_input.setPlaceholderText("Enter map name")
        self.apply_input_style(name_input)
        form_layout.addRow("Map Name *:", name_input)

        # Description
        desc_input = QTextEdit()
        desc_input.setPlaceholderText("Enter map description (optional)")
        desc_input.setMaximumHeight(60)
        self.apply_input_style(desc_input)
        form_layout.addRow("Description:", desc_input)

        # Dimensions
        width_input = QSpinBox()
        width_input.setRange(500, 5000)
        width_input.setValue(1000)
        width_input.setSuffix(" px")
        self.apply_input_style(width_input)
        form_layout.addRow("Width:", width_input)

        height_input = QSpinBox()
        height_input.setRange(400, 4000)
        height_input.setValue(800)
        height_input.setSuffix(" px")
        self.apply_input_style(height_input)
        form_layout.addRow("Height:", height_input)

        layout.addLayout(form_layout)

        # Buttons
        button_layout = QHBoxLayout()
        cancel_btn = QPushButton("Cancel")
        create_btn = QPushButton("Create Map")

        self.apply_button_style(cancel_btn)
        create_btn.setStyleSheet("""
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

        cancel_btn.clicked.connect(dialog.reject)

        def create_map():
            name = name_input.text().strip()
            if not name:
                QMessageBox.warning(dialog, "Error", "Map name is required")
                return

            map_data = {
                'name': name,
                'description': desc_input.toPlainText().strip(),
                'width': width_input.value(),
                'height': height_input.value(),
                'created_at': datetime.now().isoformat()
            }

            dialog.accept()
            self.save_new_map(map_data)

        create_btn.clicked.connect(create_map)

        button_layout.addWidget(cancel_btn)
        button_layout.addWidget(create_btn)
        layout.addLayout(button_layout)

        dialog.exec_()

    def save_new_map(self, map_data):
        """Save new map"""
        try:
            # Try API first
            if self.api_client.is_authenticated():
                response = self.maps_api.create_map(map_data)
                if 'error' not in response:
                    QMessageBox.information(self, "Success", f"Map '{map_data['name']}' created successfully!")
                    self.refresh_data()
                    # Auto-select the new map
                    new_map_id = response.get('id')
                    if new_map_id:
                        index = self.map_selector.findData(new_map_id)
                        if index >= 0:
                            self.map_selector.setCurrentIndex(index)
                            # Navigate to zone management tab for new map
                            self.tab_widget.setCurrentIndex(1)  # Zone Management tab
                            self.update_tab_accessibility()
                    return

            # Fallback to CSV
            map_data['id'] = self.csv_handler.get_next_id('maps')

            if self.csv_handler.append_to_csv('maps', map_data):
                QMessageBox.information(self, "Success", f"Map '{map_data['name']}' created!")
                self.refresh_data()
                # Auto-select the new map
                index = self.map_selector.findData(str(map_data['id']))
                if index >= 0:
                    self.map_selector.setCurrentIndex(index)
                    # Navigate to zone management tab for new map
                    self.tab_widget.setCurrentIndex(1)  # Zone Management tab
                    self.update_tab_accessibility()
            else:
                raise Exception("Failed to save to CSV")

        except Exception as e:
            self.logger.error(f"Error creating map: {e}")
            QMessageBox.critical(self, "Error", f"Failed to create map: {e}")

    def create_zone_connection(self):
        """Create new zone connection"""
        if not self.selected_map_id:
            QMessageBox.warning(self, "No Map", "Please select a map first")
            return

        from_zone = self.from_zone_input.text().strip()
        to_zone = self.to_zone_input.text().strip()

        if not from_zone or not to_zone:
            QMessageBox.warning(self, "Missing Data", "Please enter both from and to zones")
            return

        zone_data = {
            'map_id': self.selected_map_id,
            'from_zone': from_zone,
            'to_zone': to_zone,
            'magnitude': self.magnitude_input.value(),
            'direction': self.direction_combo.currentText(),
            'zone_type': self.zone_type_combo.currentText(),
            'created_at': datetime.now().isoformat()
        }

        try:
            # Try API first
            if self.api_client.is_authenticated():
                response = self.maps_api.create_zone_connection(self.selected_map_id, zone_data)
                if 'error' not in response:
                    QMessageBox.information(self, "Success", "Zone connection created!")
                    self.load_map_data(self.selected_map_id)
                    self.clear_zone_form()
                    self.update_tab_accessibility()
                    return

            # Fallback to CSV
            zone_data['id'] = self.csv_handler.get_next_id('zones')

            if self.csv_handler.append_to_csv('zones', zone_data):
                QMessageBox.information(self, "Success", "Zone connection created!")
                self.load_map_data(self.selected_map_id)
                self.clear_zone_form()
                self.update_tab_accessibility()
            else:
                raise Exception("Failed to save to CSV")

        except Exception as e:
            self.logger.error(f"Error creating zone: {e}")
            QMessageBox.critical(self, "Error", f"Failed to create zone: {e}")

    def clear_zone_form(self):
        """Clear zone creation form"""
        self.from_zone_input.clear()
        self.to_zone_input.clear()
        self.magnitude_input.setValue(50.0)
        self.direction_combo.setCurrentIndex(0)
        self.zone_type_combo.setCurrentIndex(0)

    def has_zones_configured(self, map_id):
        """Check if the specified map has zones configured"""
        if not map_id:
            return False
        
        zones = self.csv_handler.read_csv('zones')
        map_zones = [z for z in zones if str(z.get('map_id')) == str(map_id)]
        return len(map_zones) > 0

    def update_tab_accessibility(self):
        """Update tab accessibility based on zone configuration"""
        # Store current tab index to preserve it
        current_tab_index = self.tab_widget.currentIndex()
        self.logger.debug(f"Updating tab accessibility - current tab index: {current_tab_index}")
        
        if not self.selected_map_id:
            # No map selected - disable all tabs except overview
            self.tab_widget.setTabEnabled(0, True)   # Map Overview
            self.tab_widget.setTabEnabled(1, False)  # Zone Management
            self.tab_widget.setTabEnabled(2, False)  # Stop Management
            self.tab_widget.setTabEnabled(3, False)  # Rack Configuration
            self.tab_widget.setTabEnabled(4, False)  # Map Settings
            
            # Set tooltips for disabled tabs
            self.tab_widget.setTabToolTip(1, "Select a map first to enable zone management")
            self.tab_widget.setTabToolTip(2, "Select a map first to enable stop management")
            self.tab_widget.setTabToolTip(3, "Select a map first to enable rack configuration")
            self.tab_widget.setTabToolTip(4, "Select a map first to enable map settings")
            
            # Hide warning label if no map selected
            if hasattr(self, 'zone_warning_label'):
                self.zone_warning_label.setVisible(False)
            
            # If no map is selected, it's okay to be on overview tab
            return
        
        has_zones = self.has_zones_configured(self.selected_map_id)
        
        # Always enable overview and zone management tabs
        self.tab_widget.setTabEnabled(0, True)   # Map Overview
        self.tab_widget.setTabEnabled(1, True)   # Zone Management
        
        # Only enable other tabs if zones are configured
        self.tab_widget.setTabEnabled(2, has_zones)  # Stop Management
        self.tab_widget.setTabEnabled(3, has_zones)  # Rack Configuration
        self.tab_widget.setTabEnabled(4, has_zones)  # Map Settings
        
        # Show/hide warning label and set tooltips
        if hasattr(self, 'zone_warning_label'):
            self.zone_warning_label.setVisible(not has_zones)
        
        if not has_zones:
            self.tab_widget.setTabToolTip(2, "⚠️ Configure zones first to enable stop management")
            self.tab_widget.setTabToolTip(3, "⚠️ Configure zones first to enable rack configuration")
            self.tab_widget.setTabToolTip(4, "⚠️ Configure zones first to enable map settings")
        else:
            self.tab_widget.setTabToolTip(2, "")
            self.tab_widget.setTabToolTip(3, "")
            self.tab_widget.setTabToolTip(4, "")
        
        # Restore the current tab index to prevent automatic navigation
        if current_tab_index >= 0 and current_tab_index < self.tab_widget.count():
            self.tab_widget.setCurrentIndex(current_tab_index)
            self.logger.debug(f"Restored tab index to: {current_tab_index} in update_tab_accessibility")
        else:
            self.logger.debug(f"Could not restore tab index: {current_tab_index} in update_tab_accessibility")

    def on_zone_selected(self, row):
        """Handle zone selection"""
        if row < len(self.current_zones):
            zone = self.current_zones[row]
            # Populate form with selected zone data
            self.from_zone_input.setText(zone.get('from_zone', ''))
            self.to_zone_input.setText(zone.get('to_zone', ''))
            self.magnitude_input.setValue(float(zone.get('magnitude', 50)))
            
            # Restore direction combo
            direction = zone.get('direction', 'north')  # Default to north only if completely missing
            direction_index = self.direction_combo.findText(direction)
            if direction_index >= 0:
                self.direction_combo.setCurrentIndex(direction_index)
            else:
                self.direction_combo.setCurrentIndex(0)  # Default to first item if not found

            zone_type = zone.get('zone_type', 'storage')
            index = self.zone_type_combo.findText(zone_type)
            if index >= 0:
                self.zone_type_combo.setCurrentIndex(index)

    def edit_selected_zone(self):
        """Edit selected zone"""
        # Implementation for editing zones
        QMessageBox.information(self, "Feature", "Zone editing will be implemented in the next update")

    def delete_selected_zone(self):
        """Delete selected zone"""
        current_row = self.zones_table.table.currentRow()
        if current_row < len(self.current_zones):
            zone = self.current_zones[current_row]
            zone_name = f"{zone.get('from_zone', '')} → {zone.get('to_zone', '')}"

            reply = QMessageBox.question(
                self, "Confirm Delete",
                f"Delete zone connection '{zone_name}'?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )

            if reply == QMessageBox.Yes:
                try:
                    zone_id = zone.get('id')
                    if self.csv_handler.delete_csv_row('zones', zone_id):
                        QMessageBox.information(self, "Success", "Zone deleted!")
                        self.load_map_data(self.selected_map_id)
                        self.update_tab_accessibility()
                    else:
                        raise Exception("Failed to delete from CSV")
                except Exception as e:
                    QMessageBox.critical(self, "Error", f"Failed to delete zone: {e}")

    def generate_stops(self):
        """Generate stops for selected zone using intelligent position calculation (rack config removed)"""

        zone_id = self.zone_for_stops_combo.currentData()
        if not zone_id:
            QMessageBox.warning(self, "No Zone", "Please select a zone first")
            return

        try:
            # Get zone data
            zone = next((z for z in self.current_zones if str(z.get('id')) == str(zone_id)), None)
            if not zone:
                QMessageBox.warning(self, "Error", "Selected zone not found")
                return


            
            # Import and use the EXACT position calculator
            from exact_bin_integration import ExactBinIntegration
            integration = ExactBinIntegration()
            
            # Generate coordinates for zones if they don't exist
            from_x = zone.get('from_x', 100)  # Default starting point
            from_y = zone.get('from_y', 100)
            
            # Calculate end coordinates based on direction and distance
            magnitude = float(zone.get('magnitude', 50))
            direction = zone.get('direction', 'east')  # Default direction
            
            # Use direction to calculate end coordinates - CORRECT MAPPING
            # south=down, north=up, east=right, west=left
            direction_vectors = {
                'north': (0, -1),   # UP (negative Y)
                'south': (0, 1),    # DOWN (positive Y)
                'east': (1, 0),     # RIGHT (positive X)
                'west': (-1, 0),    # LEFT (negative X)
                'northeast': (0.707, -0.707), 
                'northwest': (-0.707, -0.707),
                'southeast': (0.707, 0.707), 
                'southwest': (-0.707, 0.707)
            }
            
            dx, dy = direction_vectors.get(direction.lower(), (1, 0))
            to_x = from_x + dx * magnitude
            to_y = from_y + dy * magnitude
            

            
            # Prepare zone data for exact calculation
            zone_data_for_calc = {
                'from_x': from_x,
                'from_y': from_y,
                'to_x': to_x,
                'to_y': to_y,
                'magnitude': magnitude,
                'left_bins_count': self.left_bins_input.value(),
                'right_bins_count': self.right_bins_input.value(),
                'bin_offset_distance': 2.0,  # Default offset distance
                'left_bins_distance': self.left_bin_distance_input.value(),
                'right_bins_distance': self.right_bin_distance_input.value(),
                'from_zone': zone.get('from_zone', 'A'),
                'to_zone': zone.get('to_zone', 'B')
            }
            
            # Use exact bin calculator to get proper stop positions
            exact_result = integration.calculate_bins_for_ui(zone_data_for_calc)
            
            if not exact_result.get('success'):
                raise Exception("Failed to calculate exact bin positions")
            
            # Extract sequential stops from the result
            sequential_stops = exact_result['calculated_bins']['sequential_stops']
            

            
            # Find the highest existing stop number for continuous numbering
            existing_stop_numbers = []
            for existing_stop in self.current_stops:
                stop_id = existing_stop.get('stop_id', '')
                # Extract stop number from stop_id format like "STOP_01_RIGHT1" or "STOP_05_LEFT2"
                if stop_id.startswith('STOP_'):
                    try:
                        # Split by underscore and get the number part
                        parts = stop_id.split('_')
                        if len(parts) >= 2:
                            stop_number = int(parts[1])  # Get the number part (e.g., "01" -> 1)
                            existing_stop_numbers.append(stop_number)
                    except (ValueError, IndexError):
                        continue
            
            # Determine the starting stop number for new stops
            if existing_stop_numbers:
                next_stop_number = max(existing_stop_numbers) + 1
                
            else:
                next_stop_number = 1

            
            # Convert to CSV format and save all stops with continuous numbering
            stops_saved = 0
            for i, stop_info in enumerate(sequential_stops):
                # Calculate the actual stop number (continuous from existing stops)
                actual_stop_number = next_stop_number + i
                
                stop_data = {
                    'id': self.csv_handler.get_next_id('stops'),
                    'zone_connection_id': zone_id,
                    'map_id': self.selected_map_id,
                    'stop_id': f"STOP_{actual_stop_number:02d}_{stop_info['side'].upper()}{stop_info['bin_number']}",
                    'name': f"Stop {actual_stop_number} - {stop_info['side'].title()} Bin {stop_info['bin_number']}",
                    'x_coordinate': stop_info['coordinates']['x'],
                    'y_coordinate': stop_info['coordinates']['y'],
                    'display_x': stop_info['coordinates']['x'],  # For map viewer compatibility
                    'display_y': stop_info['coordinates']['y'],  # For map viewer compatibility
                    'left_bins_count': self.left_bins_input.value(),
                    'right_bins_count': self.right_bins_input.value(),
                    'left_bins_distance': self.left_bin_distance_input.value(),
                    'right_bins_distance': self.right_bin_distance_input.value(),
                    'distance_from_start': stop_info['distance_from_start'],
                    'created_at': datetime.now().isoformat()
                }
                
                if self.csv_handler.append_to_csv('stops', stop_data):
                    stops_saved += 1
                    coords = stop_info['coordinates']

                else:
                    print(f"DEBUG: Failed to save stop: {stop_data['stop_id']}")
            
            # Use the exact result's message and include stop positioning details only
            success_message = exact_result['message']
            
            # Create detailed summary with stop positioning from exact calculation with correct numbering
            summary_text = "Stop Positioning:"
            for i, stop_info in enumerate(sequential_stops):
                actual_stop_number = next_stop_number + i
                coords = stop_info['coordinates']
                summary_text += f"\nStop {actual_stop_number}: {stop_info['distance_from_start']:.2f}m from start"
                summary_text += f"\n  Position: ({coords['x']:.1f}, {coords['y']:.1f})"
                summary_text += f"\n  Bins: 1 (1 {stop_info['side']}, 0 other)"
            
            QMessageBox.information(self, "Success", 
                f"{success_message}\n\n{summary_text}")
            self.load_map_data(self.selected_map_id)

        except Exception as e:
            self.logger.error(f"Error generating stops: {e}")
            QMessageBox.critical(self, "Error", f"Failed to generate stops: {e}")

    def save_map_settings(self):
        """Save map settings"""
        if not self.selected_map_id:
            QMessageBox.warning(self, "No Map", "Please select a map first")
            return

        map_data = {
            'name': self.map_name_input.text().strip(),
            'description': self.map_description_input.toPlainText().strip(),
            'width': self.map_width_input.value(),
            'height': self.map_height_input.value()
        }

        if not map_data['name']:
            QMessageBox.warning(self, "Error", "Map name is required")
            return

        try:
            # Try API first
            if self.api_client.is_authenticated():
                response = self.maps_api.update_map(self.selected_map_id, map_data)
                if 'error' not in response:
                    QMessageBox.information(self, "Success", "Map settings saved!")
                    self.refresh_data()
                    return

            # Fallback to CSV
            if self.csv_handler.update_csv_row('maps', self.selected_map_id, map_data):
                QMessageBox.information(self, "Success", "Map settings saved!")
                self.refresh_data()
            else:
                raise Exception("Failed to update CSV")

        except Exception as e:
            self.logger.error(f"Error saving map: {e}")
            QMessageBox.critical(self, "Error", f"Failed to save map: {e}")

    def delete_current_map(self):
        """Delete current map"""
        if not self.selected_map_id:
            return

        selected_map = next((m for m in self.current_maps if str(m.get('id')) == str(self.selected_map_id)), None)
        map_name = selected_map.get('name', 'Unknown') if selected_map else 'Unknown'

        reply = QMessageBox.question(
            self, "Confirm Delete",
            f"Delete map '{map_name}'?\n\nThis will also delete all zones, stops, and stop groups.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            try:
                # Delete from CSV
                if self.csv_handler.delete_csv_row('maps', self.selected_map_id):
                    # Delete related data
                    self.delete_map_related_data(self.selected_map_id)
                    QMessageBox.information(self, "Success", "Map deleted!")
                    self.selected_map_id = None
                    self.refresh_data()
                else:
                    raise Exception("Failed to delete from CSV")

            except Exception as e:
                self.logger.error(f"Error deleting map: {e}")
                QMessageBox.critical(self, "Error", f"Failed to delete map: {e}")

    def delete_map_related_data(self, map_id):
        """Delete all data related to a map"""
        try:
            # Get current data
            zones = self.csv_handler.read_csv('zones')
            stops = self.csv_handler.read_csv('stops')
            stop_groups = self.csv_handler.read_csv('stop_groups')

            # Filter out data for this map
            zones = [z for z in zones if str(z.get('map_id')) != str(map_id)]
            stops = [s for s in stops if str(s.get('map_id')) != str(map_id)]
            stop_groups = [sg for sg in stop_groups if str(sg.get('map_id')) != str(map_id)]

            # Write back filtered data
            self.csv_handler.write_csv('zones', zones)
            self.csv_handler.write_csv('stops', stops)
            self.csv_handler.write_csv('stop_groups', stop_groups)

        except Exception as e:
            self.logger.error(f"Error deleting related data: {e}")

    def on_stop_selected(self, stop_data):
        """Handle stop selection from map viewer"""
        # This will be implemented when map viewer is improved
        pass

    def sync_with_api(self):
        """Sync maps with API"""
        if not self.api_client.is_authenticated():
            QMessageBox.warning(self, "Not Connected", "Please connect to API first")
            return

        try:
            success = self.sync_manager.sync_data_type('maps')
            if success:
                QMessageBox.information(self, "Success", "Maps synced successfully!")
                self.refresh_data()
            else:
                QMessageBox.warning(self, "Sync Failed", "Failed to sync maps")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Sync error: {e}")
    
    def create_stop_controls_section(self):
        """Create horizontal stop controls section (rack distances removed)"""
        controls_frame = QFrame()
        controls_frame.setStyleSheet("""
            QFrame {
                background-color: #353535;
                border: 1px solid #555555;
                border-radius: 6px;
                padding: 3px;
            }
        """)
        controls_frame.setSizePolicy(controls_frame.sizePolicy().Expanding, controls_frame.sizePolicy().Preferred)
        
        main_layout = QHBoxLayout(controls_frame)
        main_layout.setContentsMargins(4, 4, 4, 4)
        main_layout.setSpacing(4)
        
        # Left side - Basic stop configuration
        left_panel = self.create_basic_stop_config_panel()
        left_panel.setSizePolicy(left_panel.sizePolicy().Expanding, left_panel.sizePolicy().Preferred)
        main_layout.addWidget(left_panel, 1)
        
        return controls_frame
    
    def create_basic_stop_config_panel(self):
        """Create basic stop configuration panel with presets and validation"""
        panel = QFrame()
        panel.setStyleSheet("""
            QFrame {
                background-color: #404040;
                border: 1px solid #666666;
                border-radius: 8px;
                padding: 4px;
            }
        """)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)
        
        # Title with better styling
        title = QLabel("Basic Configuration")
        title.setFont(QFont("Arial", 14, QFont.Bold))
        title.setStyleSheet("color: #ff6b35; border: none; margin-bottom: 3px;")
        layout.addWidget(title)
        
        # Form layout for inputs with improved spacing
        form_layout = QFormLayout()
        form_layout.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        form_layout.setFormAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        form_layout.setVerticalSpacing(5)
        form_layout.setHorizontalSpacing(5)
        form_layout.setContentsMargins(0, 0, 0, 0)
        
        # Zone selection with validation indicator and improved styling
        zone_frame = QFrame()
        zone_frame.setStyleSheet("background-color: #454545; border-radius: 6px; padding: 6px;")
        zone_layout = QHBoxLayout(zone_frame)
        zone_layout.setContentsMargins(6, 6, 6, 6)
        zone_layout.setSpacing(8)
        
        self.zone_for_stops_combo = QComboBox()
        self.zone_for_stops_combo.addItem("Select Zone", "")
        self.zone_for_stops_combo.currentTextChanged.connect(self.validate_stop_inputs)
        
        # Enhanced combo box styling for better visibility and functionality
        self.zone_for_stops_combo.setStyleSheet("""
            QComboBox {
                background-color: #505050;
                border: 2px solid #666666;
                padding: 8px 10px;
                border-radius: 6px;
                color: #ffffff;
                font-size: 12px;
                font-weight: bold;
                min-width: 200px;
                min-height: 26px;
            }
            QComboBox:hover {
                border: 2px solid #ff6b35;
                background-color: #555555;
            }
            QComboBox:focus {
                border: 2px solid #ff6b35;
                background-color: #555555;
            }
            QComboBox::drop-down {
                border: 0px;
                width: 20px;
            }
            QComboBox::down-arrow {
                image: url(:/icons/dropdown.png);
                width: 12px;
                height: 12px;
            }
            QComboBox QAbstractItemView {
                background-color: #404040;
                color: #ffffff;
                selection-background-color: #ff6b35;
                selection-color: white;
                border: 2px solid #666666;
                outline: none;
                padding: 4px;
                font-size: 13px;
            }
            QComboBox QAbstractItemView::item {
                padding: 12px 8px;
                border-bottom: 1px solid #666666;
                min-height: 25px;
            }
            QComboBox QAbstractItemView::item:hover {
                background-color: #ff6b35;
                color: #ffffff;
            }
            QComboBox QAbstractItemView::item:selected {
                background-color: #ff6b35;
                color: #ffffff;
                font-weight: bold;
            }
        """)
        
        zone_layout.addWidget(self.zone_for_stops_combo)
        
        self.zone_validation_icon = QLabel("⚠️")
        self.zone_validation_icon.setStyleSheet("""
            color: #ff6b35; 
            font-size: 18px; 
            background-color: #505050; 
            border-radius: 4px; 
            padding: 8px;
        """)
        self.zone_validation_icon.setToolTip("Please select a zone")
        self.zone_validation_icon.setAlignment(Qt.AlignCenter)
        self.zone_validation_icon.setFixedSize(28, 28)
        zone_layout.addWidget(self.zone_validation_icon)
        
        form_layout.addRow("Zone:", zone_frame)
        
        # Bin configuration with improved layout
        bins_frame = QFrame()
        bins_frame.setStyleSheet("background-color: #454545; border-radius: 6px; padding: 6px;")
        bins_layout = QHBoxLayout(bins_frame)
        bins_layout.setContentsMargins(6, 6, 6, 6)
        bins_layout.setSpacing(8)
        
        # Left bins section with better styling
        left_frame = QFrame()
        left_frame.setStyleSheet("background-color: #505050; border-radius: 5px; padding: 6px;")
        left_layout = QVBoxLayout(left_frame)
        left_layout.setSpacing(6)
        
        left_label = QLabel("Left")
        left_label.setStyleSheet("color: #ffffff; font-weight: bold; font-size: 13px; margin-bottom: 5px;")
        left_label.setAlignment(Qt.AlignCenter)
        left_layout.addWidget(left_label)
        
        self.left_bins_input = QSpinBox()
        self.left_bins_input.setRange(0, 50)
        self.left_bins_input.setValue(2)
        self.left_bins_input.valueChanged.connect(self.validate_stop_inputs)
        self.apply_input_style(self.left_bins_input)
        left_layout.addWidget(self.left_bins_input)
        
        # Left bin distance with better label
        distance_label = QLabel("Distance (m)")
        distance_label.setStyleSheet("color: #cccccc; font-size: 11px; margin-top: 2px;")
        distance_label.setAlignment(Qt.AlignCenter)
        left_layout.addWidget(distance_label)
        
        self.left_bin_distance_input = QDoubleSpinBox()
        self.left_bin_distance_input.setRange(0.1, 10.0)
        self.left_bin_distance_input.setValue(2.0)
        self.left_bin_distance_input.setSingleStep(0.1)
        self.left_bin_distance_input.setDecimals(1)
        self.apply_input_style(self.left_bin_distance_input)
        left_layout.addWidget(self.left_bin_distance_input)
        bins_layout.addWidget(left_frame)
        
        # Quick adjust buttons with better vertical alignment
        adjust_layout = QVBoxLayout()
        adjust_layout.setContentsMargins(0, 0, 0, 0)
        adjust_layout.addStretch()
        
        match_btn = QPushButton("↔")
        match_btn.setToolTip("Match left and right bin counts")
        match_btn.clicked.connect(self.match_bin_counts)
        match_btn.setStyleSheet("""
            QPushButton {
                background-color: #ff6b35;
                color: white;
                border: none;
                padding: 8px;
                border-radius: 4px;
                font-size: 14px;
                font-weight: bold;
                min-width: 36px;
                min-height: 36px;
            }
            QPushButton:hover { 
                background-color: #e55a2a; 
            }
        """)
        adjust_layout.addWidget(match_btn)
        adjust_layout.addStretch()
        bins_layout.addLayout(adjust_layout)
        
        # Right bins section with better styling
        right_frame = QFrame()
        right_frame.setStyleSheet("background-color: #505050; border-radius: 5px; padding: 6px;")
        right_layout = QVBoxLayout(right_frame)
        right_layout.setSpacing(6)
        
        right_label = QLabel("Right")
        right_label.setStyleSheet("color: #ffffff; font-weight: bold; font-size: 13px; margin-bottom: 5px;")
        right_label.setAlignment(Qt.AlignCenter)
        right_layout.addWidget(right_label)
        
        self.right_bins_input = QSpinBox()
        self.right_bins_input.setRange(0, 50)
        self.right_bins_input.setValue(2)
        self.right_bins_input.valueChanged.connect(self.validate_stop_inputs)
        self.apply_input_style(self.right_bins_input)
        right_layout.addWidget(self.right_bins_input)
        
        # Right bin distance with better label
        distance_label = QLabel("Distance (m)")
        distance_label.setStyleSheet("color: #cccccc; font-size: 11px; margin-top: 2px;")
        distance_label.setAlignment(Qt.AlignCenter)
        right_layout.addWidget(distance_label)
        
        self.right_bin_distance_input = QDoubleSpinBox()
        self.right_bin_distance_input.setRange(0.1, 10.0)
        self.right_bin_distance_input.setValue(2.0)
        self.right_bin_distance_input.setSingleStep(0.1)
        self.right_bin_distance_input.setDecimals(1)
        self.apply_input_style(self.right_bin_distance_input)
        right_layout.addWidget(self.right_bin_distance_input)
        bins_layout.addWidget(right_frame)
        
        form_layout.addRow("Bins:", bins_frame)
        
        # Rack levels configuration removed
        
        # Add some spacing between form and validation
        layout.addLayout(form_layout)
        layout.addSpacing(6)
        
        # Validation summary with improved styling
        self.validation_label = QLabel("")
        self.validation_label.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-size: 11px;
                padding: 6px;
                background-color: rgba(255, 107, 53, 0.2);
                border-radius: 6px;
                border: 1px solid #ff6b35;
                margin-top: 6px;
            }
        """)
        self.validation_label.setWordWrap(True)
        self.validation_label.setAlignment(Qt.AlignCenter)
        self.validation_label.hide()
        layout.addWidget(self.validation_label)
        
        # Add spacing before generate button
        layout.addSpacing(10)
        
        # Info text
        info = QLabel("Configure parameters and click to generate warehouse stops.")
        info.setWordWrap(True)
        info.setStyleSheet("""
            color: #cccccc;
            font-size: 12px;
            padding: 10px;
            text-align: center;
        """)
        info.setAlignment(Qt.AlignCenter)
        layout.addWidget(info)
        
        # Generate button
        generate_btn = QPushButton("🔧 Generate Stops")
        generate_btn.clicked.connect(self.generate_stops)
        generate_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #12c482, stop: 1 #0ea86f);
                color: white;
                border: none;
                padding: 15px 25px;
                border-radius: 8px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #0ea86f, stop: 1 #059669);
            }
        """)
        layout.addWidget(generate_btn)
        
        return panel
    
    # Rack distances panel removed
    
    def create_stop_details_section(self):
        """Create a section to display stop details in a table format with dedicated scroll bar"""
        # Create the section widget
        stop_details_widget = QWidget()
        stop_details_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        stop_details_layout = QVBoxLayout(stop_details_widget)
        stop_details_layout.setContentsMargins(15, 15, 15, 15)
        stop_details_layout.setSpacing(10)

        # Create title and summary section
        title_layout = QHBoxLayout()
        
        # Title label
        title_label = QLabel("Stop Details")
        title_label.setFont(QFont("Arial", 14, QFont.Bold))
        title_label.setStyleSheet("color: #ff6b35; margin-bottom: 10px;")
        title_layout.addWidget(title_label)
        
        title_layout.addStretch()
        
        # Summary statistics
        self.stop_summary_label = QLabel("Total Stops: 0 | Active: 0 | Total Bins: 0")
        self.stop_summary_label.setStyleSheet("""
            color: #cccccc; 
            font-size: 12px; 
            font-weight: bold; 
            background-color: #454545; 
            padding: 8px 12px; 
            border-radius: 6px; 
            border: 1px solid #666666;
        """)
        title_layout.addWidget(self.stop_summary_label)
        
        stop_details_layout.addLayout(title_layout)

        # Create the stop details table using DataTableWidget with enhanced scroll functionality
        self.stop_details_table = DataTableWidget([
            "Stop ID", "Stop Name", "Distance (m)",
            "Side Dist (m)", "Created"
        ], searchable=False, selectable=True)
        
        # Configure table size and scroll behavior for optimal scroll bar visibility
        self.stop_details_table.setMinimumHeight(250)  # Minimum height to ensure scroll bar appears
        self.stop_details_table.setMaximumHeight(400)  # Maximum height to force scroll bar when needed
        
        # Ensure the table widget itself can expand properly
        self.stop_details_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        # Configure the internal table widget for dedicated scroll bar functionality
        table_widget = self.stop_details_table.table
        table_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        # Force vertical scroll bar to always be visible for consistent UI
        table_widget.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        table_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        # Enhanced scroll bar styling with better visibility
        enhanced_scroll_style = """
            QTableWidget {
                background-color: #404040;
                alternate-background-color: #454545;
                gridline-color: #555555;
                color: #ffffff;
                border: 1px solid #555555;
                border-radius: 6px;
            }
            QTableWidget::item {
                padding: 8px;
                border: none;
            }
            QTableWidget::item:selected {
                background-color: #ff6b35;
                color: #ffffff;
            }
            QHeaderView::section {
                background-color: #2a2a2a;
                padding: 12px 8px;
                border: 1px solid #666666;
                font-weight: bold;
                font-size: 12px;
                color: #ff6b35;
                margin: 1px;
                border-radius: 3px;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }
            QScrollBar:vertical {
                background-color: #353535;
                width: 16px;
                border-radius: 8px;
                margin: 2px;
                border: 1px solid #555555;
            }
            QScrollBar::handle:vertical {
                background-color: #ff6b35;
                border-radius: 6px;
                min-height: 30px;
                margin: 2px;
                border: 1px solid #e55a2b;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #e55a2b;
                border: 1px solid #d14d21;
            }
            QScrollBar::handle:vertical:pressed {
                background-color: #d14d21;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
                background: transparent;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: transparent;
            }
            QScrollBar:horizontal {
                background-color: #353535;
                height: 16px;
                border-radius: 8px;
                margin: 2px;
                border: 1px solid #555555;
            }
            QScrollBar::handle:horizontal {
                background-color: #ff6b35;
                border-radius: 6px;
                min-width: 30px;
                margin: 2px;
                border: 1px solid #e55a2b;
            }
            QScrollBar::handle:horizontal:hover {
                background-color: #e55a2b;
                border: 1px solid #d14d21;
            }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                width: 0px;
                background: transparent;
            }
        """
        
        table_widget.setStyleSheet(enhanced_scroll_style)
        
        # Ensure scroll bars update properly when data changes
        table_widget.verticalScrollBar().setVisible(True)
        
        # Add the table to the layout with stretch factor to allow expansion
        stop_details_layout.addWidget(self.stop_details_table, 1)

        # Style the section widget with better contrast
        stop_details_widget.setStyleSheet("""
            QWidget {
                background-color: #2b2b2b;
                border: 2px solid #ff6b35;
                border-radius: 10px;
                margin: 5px;
            }
        """)

        return stop_details_widget

    def calculate_stop_distances(self):
        """Calculate distance_from_start for stops that don't have it"""
        import math
        
        # Get zones for this map
        zones = self.current_zones
        if not zones:
            return
            
        # Group stops by zone_connection_id
        stops_by_zone = {}
        for stop in self.current_stops:
            zone_id = stop.get('zone_connection_id')
            if zone_id:
                if zone_id not in stops_by_zone:
                    stops_by_zone[zone_id] = []
                stops_by_zone[zone_id].append(stop)
        
        # Calculate distances for each zone's stops
        for zone_id, zone_stops in stops_by_zone.items():
            # Find the corresponding zone
            zone = next((z for z in zones if str(z.get('id')) == str(zone_id)), None)
            if not zone:
                continue
                
            # Get zone start and end coordinates
            from_x = float(zone.get('from_x', 100))
            from_y = float(zone.get('from_y', 100))
            magnitude = float(zone.get('magnitude', 50))
            direction = zone.get('direction', 'east')
            
            # Calculate end coordinates based on direction
            direction_vectors = {
                'north': (0, -1),   # UP (negative Y)
                'south': (0, 1),    # DOWN (positive Y)
                'east': (1, 0),     # RIGHT (positive X)
                'west': (-1, 0),    # LEFT (negative X)
                'northeast': (0.707, -0.707), 
                'northwest': (-0.707, -0.707),
                'southeast': (0.707, 0.707), 
                'southwest': (-0.707, 0.707)
            }
            
            dx, dy = direction_vectors.get(direction.lower(), (1, 0))
            to_x = from_x + dx * magnitude
            to_y = from_y + dy * magnitude
            
            # Calculate path vector
            path_dx = to_x - from_x
            path_dy = to_y - from_y
            path_length = math.sqrt(path_dx * path_dx + path_dy * path_dy)
            
            if path_length == 0:
                continue
                
            # Normalize path vector
            path_dx /= path_length
            path_dy /= path_length
            
            # Calculate distance for each stop
            for stop in zone_stops:
                # Skip if distance already calculated
                if stop.get('distance_from_start') and stop.get('distance_from_start') != 'N/A':
                    continue
                    
                # Get stop coordinates
                stop_x = float(stop.get('x_coordinate', stop.get('display_x', 0)))
                stop_y = float(stop.get('y_coordinate', stop.get('display_y', 0)))
                
                # Calculate projection onto the path
                # Vector from start to stop
                stop_dx = stop_x - from_x
                stop_dy = stop_y - from_y
                
                # Project onto path vector
                distance = stop_dx * path_dx + stop_dy * path_dy
                
                # Ensure distance is within bounds
                distance = max(0, min(distance, magnitude))
                
                # Update the stop data
                stop['distance_from_start'] = distance
                
                # Also update the CSV file
                self.csv_handler.update_csv_row('stops', stop.get('id'), {'distance_from_start': distance})

    def refresh_stop_details_table(self):
        """Refresh the stop details table with current map's stops"""
        if not hasattr(self, 'stop_details_table'):
            return
            
        # Clear existing data
        self.stop_details_table.clear_data()
        
        if not self.selected_map_id:
            # No map selected - show empty table
            if hasattr(self, 'stop_summary_label'):
                self.stop_summary_label.setText("Total Stops: 0 | Active: 0 | Total Bins: 0")
            return
            
        if not self.current_stops:
            # Map selected but no stops - show message row
            self.stop_details_table.set_data([["No stops available", "Generate stops using the controls above", "", "", ""]])
            
            # Update summary for no stops
            if hasattr(self, 'stop_summary_label'):
                self.stop_summary_label.setText("Total Stops: 0 | Active: 0 | Total Bins: 0")
            return
            
        # Calculate distances for stops that don't have them
        self.calculate_stop_distances()
            
        # Calculate summary statistics
        total_stops = len(self.current_stops)
        active_stops = sum(1 for stop in self.current_stops if stop.get('x_coordinate') and stop.get('y_coordinate'))
        total_bins = sum(
            (int(stop.get('left_bins_count', 0)) + int(stop.get('right_bins_count', 0))) 
            for stop in self.current_stops
        )
        
        # Update summary label
        if hasattr(self, 'stop_summary_label'):
            self.stop_summary_label.setText(f"Total Stops: {total_stops} | Active: {active_stops} | Total Bins: {total_bins}")
        
        # Prepare data for DataTableWidget
        table_data = []
        for stop in self.current_stops:
            # Stop ID
            stop_id = stop.get('stop_id', 'N/A')
            
            # Stop Name
            stop_name = stop.get('name', 'Unnamed Stop')
            
            # X Coordinate
            x_coord = stop.get('x_coordinate', stop.get('display_x', 'N/A'))
            x_coord_str = f"{x_coord:.2f}" if isinstance(x_coord, (int, float)) else str(x_coord)
            
            # Y Coordinate
            y_coord = stop.get('y_coordinate', stop.get('display_y', 'N/A'))
            y_coord_str = f"{y_coord:.2f}" if isinstance(y_coord, (int, float)) else str(y_coord)
            
            # Distance from Start
            distance = stop.get('distance_from_start', 'N/A')
            distance_str = f"{distance:.2f}m" if isinstance(distance, (int, float)) else str(distance)
            
            # Left/Right bins distance (robust parsing from CSV strings)
            def _to_float(value):
                try:
                    return float(value)
                except (TypeError, ValueError):
                    return None
            left_dist_raw = stop.get('left_bins_distance', 'N/A')
            right_dist_raw = stop.get('right_bins_distance', 'N/A')
            left_dist_val = _to_float(left_dist_raw)
            right_dist_val = _to_float(right_dist_raw)
            left_dist = left_dist_val if left_dist_val is not None else left_dist_raw
            right_dist = right_dist_val if right_dist_val is not None else right_dist_raw
            left_dist_str = f"{left_dist_val:.1f}m" if left_dist_val is not None else str(left_dist_raw)
            right_dist_str = f"{right_dist_val:.1f}m" if right_dist_val is not None else str(right_dist_raw)

            # Side Distance based on stop name (Left/Right Bin)
            side_distance_value = None
            try:
                name_lower = str(stop_name).lower()
                if ('right' in name_lower) and ('bin' in name_lower):
                    side_distance_value = right_dist_val
                elif ('left' in name_lower) and ('bin' in name_lower):
                    side_distance_value = left_dist_val
            except Exception:
                side_distance_value = None
            side_dist_str = f"{side_distance_value:.1f}" if side_distance_value is not None else "N/A"
            
            # Created Date/Time
            created_at = stop.get('created_at', 'N/A')
            if created_at and created_at != 'N/A':
                try:
                    # Format the datetime for better display
                    dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    formatted_date = dt.strftime('%Y-%m-%d %H:%M')
                except:
                    formatted_date = created_at[:19] if len(created_at) >= 19 else created_at
            else:
                formatted_date = 'N/A'
            
            # Add row data
            table_data.append([
                str(stop_id), str(stop_name), distance_str,
                side_dist_str, formatted_date
            ])
        
        # Set data in DataTableWidget
        self.stop_details_table.set_data(table_data)


    # ===== HELPER METHODS =====
    
    def match_bin_counts(self):
        """Match right bins to left bins count"""
        left_count = self.left_bins_input.value()
        self.right_bins_input.setValue(left_count)
        self.validate_stop_inputs()
    
    # Rack level change and height preview removed
    
    def validate_stop_inputs(self):
        """Validate stop generation inputs and show feedback"""
        issues = []
        
        # Check zone selection
        if not self.zone_for_stops_combo.currentData():
            issues.append("No zone selected")
            self.zone_validation_icon.show()
        else:
            self.zone_validation_icon.hide()
        
        # Check bin counts
        total_bins = self.left_bins_input.value() + self.right_bins_input.value()
        if total_bins == 0:
            issues.append("No bins configured")
        elif total_bins > 20:
            issues.append(f"High bin count ({total_bins}) may impact performance")
        
        # Rack configuration validation removed
        
        # Update validation display
        if issues:
            self.validation_label.setText("Issues: " + "; ".join(issues))
            self.validation_label.show()
        else:
            self.validation_label.hide()
        
        return len(issues) == 0
    
    # Enhanced stops table section method removed as part of UI cleanup
    
    # Stops table filtering and population methods removed as part of UI cleanup
    
    # Export stops data method removed as part of UI cleanup

    
    # Duplicate selected stop method removed as part of UI cleanup
