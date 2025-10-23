from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
                             QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QPushButton,
                             QLabel, QFrame, QMessageBox, QScrollArea)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from pathlib import Path
import csv
from config.constants import DEVICE_STATUS
from datetime import datetime
from utils.device_movement_tracker import DeviceMovementTracker
from utils.zone_navigation_manager import get_zone_navigation_manager

class AddDeviceDialog(QDialog):
    def __init__(self, parent=None, device_data=None):
        super().__init__(parent)
        self.device_data = device_data
        self.is_edit_mode = device_data is not None

        self.setup_ui()
        self.setup_validation()

        if self.is_edit_mode:
            self.populate_fields()

    def populate_location_dropdown(self):
        """Populate location dropdown with unique zones from all maps"""
        try:
            # Get the CSV handler instance from the parent widget
            csv_handler = self.parent().csv_handler
            zones = csv_handler.read_csv('zones')
            
            # Create a set to store unique zone names
            unique_zones = set()
            
            # Add both from_zones and to_zones to the set
            for zone in zones:
                from_zone = zone.get('from_zone', '')
                to_zone = zone.get('to_zone', '')
                if from_zone:
                    unique_zones.add(from_zone)
                if to_zone:
                    unique_zones.add(to_zone)
            
            # Add a default option
            self.current_location_combo.addItem("Select Location", "")
            
            # Add sorted unique zones to the dropdown
            for zone in sorted(unique_zones):
                self.current_location_combo.addItem(zone, zone)
                
        except Exception as e:
            self.parent().logger.error(f"Error populating location dropdown: {e}")

    def setup_ui(self):
        """Setup dialog UI"""
        self.setWindowTitle("Edit Device" if self.is_edit_mode else "Add New Device")
        self.setModal(True)
        self.setFixedSize(900, 900)

        # Apply dark theme
        self.setStyleSheet("""
            QDialog {
                background-color: #2b2b2b;
                color: #ffffff;
            }
            QLabel {
                color: #ffffff;
            }
            QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {
                background-color: #404040;
                border: 1px solid #555555;
                padding: 8px;
                border-radius: 4px;
                color: #ffffff;
            }
            QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {
                border: 2px solid #ff6b35;
                background-color: #454545;
            }
            QComboBox::drop-down {
                border: none;
                padding-right: 15px;
            }
            QComboBox::down-arrow {
                width: 12px;
                height: 12px;
            }
            QPushButton {
                background-color: #555555;
                border: 1px solid #666666;
                padding: 10px 20px;
                border-radius: 4px;
                color: #ffffff;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #666666;
            }
            QPushButton:pressed {
                background-color: #444444;
            }
            QFormLayout {
                spacing: 12px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(30)  # Further increased spacing between sections
        layout.setContentsMargins(40, 40, 40, 40)  # Further increased margins

        # Title
        title = QLabel("Edit Device Details" if self.is_edit_mode else "Add New Device")
        title.setFont(QFont("Arial", 16, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("color: #ff6b35; margin-bottom: 10px;")
        layout.addWidget(title)

        # Form (wrapped in a scroll area)
        form_frame = QFrame()
        form_frame.setStyleSheet("""
            QFrame {
                background-color: #353535;
                border: 1px solid #555555;
                border-radius: 6px;
                padding: 25px;
            }
        """)
        form_layout = QFormLayout(form_frame)
        form_layout.setSpacing(15)

        # Device Model (Add mode only)
        if not self.is_edit_mode:
            model_label = QLabel("Device Model:")
            model_label.setStyleSheet("""
                QLabel {
                    color: #ffffff;
                    font-weight: bold;
                    font-size: 14px;
                    min-width: 120px;
                }
            """)
            self.device_model_combo = QComboBox()
            self.device_model_combo.addItems(["V1", "V2"]) 
            form_layout.addRow(model_label, self.device_model_combo)

        # Device ID
        id_label = QLabel("Device ID *:")
        id_label.setStyleSheet("""
            QLabel {
                color: #ff6b35;
                font-weight: bold;
                font-size: 14px;
                min-width: 120px;
            }
        """)
        self.device_id_input = QLineEdit()
        self.device_id_input.setPlaceholderText("e.g., DEV001, ROBOT_01")
        form_layout.addRow(id_label, self.device_id_input)

        # Device Name
        name_label = QLabel("Device Name *:")
        name_label.setStyleSheet("""
            QLabel {
                color: #ff6b35;
                font-weight: bold;
                font-size: 14px;
                min-width: 120px;
            }
        """)
        self.device_name_input = QLineEdit()
        self.device_name_input.setPlaceholderText("e.g., Main Picker Robot")
        form_layout.addRow(name_label, self.device_name_input)

        # Forward Speed
        fwd_label = QLabel("Forward Speed:")
        fwd_label.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-weight: bold;
                font-size: 14px;
                min-width: 120px;
            }
        """)
        self.forward_speed_spinbox = QDoubleSpinBox()
        self.forward_speed_spinbox.setRange(0, 10000)
        self.forward_speed_spinbox.setDecimals(0)
        self.forward_speed_spinbox.setSingleStep(1)
        self.forward_speed_spinbox.setValue(0)
        form_layout.addRow(fwd_label, self.forward_speed_spinbox)

        # Turning Speed
        turn_label = QLabel("Turning Speed:")
        turn_label.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-weight: bold;
                font-size: 14px;
                min-width: 120px;
            }
        """)
        self.turning_speed_spinbox = QDoubleSpinBox()
        self.turning_speed_spinbox.setRange(0, 1000)
        self.turning_speed_spinbox.setDecimals(0)
        self.turning_speed_spinbox.setSingleStep(1)
        self.turning_speed_spinbox.setValue(0)
        form_layout.addRow(turn_label, self.turning_speed_spinbox)

        # Status
        status_label = QLabel("Status:")
        status_label.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-weight: bold;
                font-size: 14px;
                min-width: 120px;
            }
        """)
        self.status_combo = QComboBox()
        for key, value in DEVICE_STATUS.items():
            self.status_combo.addItem(value, key)
        self.status_combo.setCurrentText("Working")
        form_layout.addRow(status_label, self.status_combo)

        # Battery Level
        battery_label = QLabel("Battery Level:")
        battery_label.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-weight: bold;
                font-size: 14px;
                min-width: 120px;
            }
        """)
        self.battery_spinbox = QSpinBox()
        self.battery_spinbox.setRange(0, 100)
        self.battery_spinbox.setValue(100)
        self.battery_spinbox.setSuffix("%")
        form_layout.addRow(battery_label, self.battery_spinbox)

        # Current Location
        current_location_label = QLabel("Current Location:")
        current_location_label.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-weight: bold;
                font-size: 14px;
                min-width: 120px;
            }
        """)
        self.current_location_combo = QComboBox()
        self.current_location_combo.setPlaceholderText("Select Zone")
        self.populate_location_dropdown()
        form_layout.addRow(current_location_label, self.current_location_combo)

        # Additional sections (Add mode only)
        if not self.is_edit_mode:
            # Driving-Parameters section header
            driving_header = QLabel("Driving-Parameters")
            driving_header.setStyleSheet("color: #ff6b35; font-weight: bold; font-size: 14px; margin-top: 10px;")
            form_layout.addRow(driving_header)

            # Wheel Diameter
            wheel_label = QLabel("Wheel Diameter:")
            wheel_label.setStyleSheet("""
                QLabel {
                    color: #ffffff;
                    font-weight: bold;
                    font-size: 14px;
                    min-width: 120px;
                }
            """)
            self.wheel_diameter_spinbox = QDoubleSpinBox()
            self.wheel_diameter_spinbox.setRange(0, 100000)
            self.wheel_diameter_spinbox.setDecimals(2)
            self.wheel_diameter_spinbox.setSingleStep(0.1)
            self.wheel_diameter_spinbox.setValue(0.0)
            form_layout.addRow(wheel_label, self.wheel_diameter_spinbox)

            # Distance Between Wheels
            dbw_label = QLabel("Distance Between Wheels:")
            dbw_label.setStyleSheet("""
                QLabel {
                    color: #ffffff;
                    font-weight: bold;
                    font-size: 14px;
                    min-width: 120px;
                }
            """)
            self.distance_between_wheels_spinbox = QDoubleSpinBox()
            self.distance_between_wheels_spinbox.setRange(0, 100000)
            self.distance_between_wheels_spinbox.setDecimals(2)
            self.distance_between_wheels_spinbox.setSingleStep(0.1)
            self.distance_between_wheels_spinbox.setValue(0.0)
            form_layout.addRow(dbw_label, self.distance_between_wheels_spinbox)

            # Gear Ratio
            gear_label = QLabel("Gear Ratio:")
            gear_label.setStyleSheet("""
                QLabel {
                    color: #ffffff;
                    font-weight: bold;
                    font-size: 14px;
                    min-width: 120px;
                }
            """)
            self.gear_ratio_spinbox = QDoubleSpinBox()
            self.gear_ratio_spinbox.setRange(0, 1000)
            self.gear_ratio_spinbox.setDecimals(2)
            self.gear_ratio_spinbox.setSingleStep(0.1)
            self.gear_ratio_spinbox.setValue(0.0)
            form_layout.addRow(gear_label, self.gear_ratio_spinbox)

            # Physical-Dimentions section header
            physical_header = QLabel("Physical-Dimentions")
            physical_header.setStyleSheet("color: #ff6b35; font-weight: bold; font-size: 14px; margin-top: 10px;")
            form_layout.addRow(physical_header)

            # Length
            length_label = QLabel("Length:")
            length_label.setStyleSheet("""
                QLabel {
                    color: #ffffff;
                    font-weight: bold;
                    font-size: 14px;
                    min-width: 120px;
                }
            """)
            self.length_spinbox = QDoubleSpinBox()
            self.length_spinbox.setRange(0, 100000)
            self.length_spinbox.setDecimals(2)
            self.length_spinbox.setSingleStep(0.1)
            self.length_spinbox.setValue(0.0)
            form_layout.addRow(length_label, self.length_spinbox)

            # Width
            width_label = QLabel("Width:")
            width_label.setStyleSheet("""
                QLabel {
                    color: #ffffff;
                    font-weight: bold;
                    font-size: 14px;
                    min-width: 120px;
                }
            """)
            self.width_spinbox = QDoubleSpinBox()
            self.width_spinbox.setRange(0, 100000)
            self.width_spinbox.setDecimals(2)
            self.width_spinbox.setSingleStep(0.1)
            self.width_spinbox.setValue(0.0)
            form_layout.addRow(width_label, self.width_spinbox)

            # Height
            height_label = QLabel("Height:")
            height_label.setStyleSheet("""
                QLabel {
                    color: #ffffff;
                    font-weight: bold;
                    font-size: 14px;
                    min-width: 120px;
                }
            """)
            self.height_spinbox = QDoubleSpinBox()
            self.height_spinbox.setRange(0, 100000)
            self.height_spinbox.setDecimals(2)
            self.height_spinbox.setSingleStep(0.1)
            self.height_spinbox.setValue(0.0)
            form_layout.addRow(height_label, self.height_spinbox)

            # Lifting Height
            lifting_label = QLabel("Lifting Height:")
            lifting_label.setStyleSheet("""
                QLabel {
                    color: #ffffff;
                    font-weight: bold;
                    font-size: 14px;
                    min-width: 120px;
                }
            """)
            self.lifting_height_spinbox = QDoubleSpinBox()
            self.lifting_height_spinbox.setRange(0, 100000)
            self.lifting_height_spinbox.setDecimals(2)
            self.lifting_height_spinbox.setSingleStep(0.1)
            self.lifting_height_spinbox.setValue(0.0)
            form_layout.addRow(lifting_label, self.lifting_height_spinbox)

            # Maximum Forward Speed
            max_fwd_label = QLabel("Maximum Forward Speed:")
            max_fwd_label.setStyleSheet("""
                QLabel {
                    color: #ffffff;
                    font-weight: bold;
                    font-size: 14px;
                    min-width: 120px;
                }
            """)
            self.max_forward_speed_spinbox = QDoubleSpinBox()
            self.max_forward_speed_spinbox.setRange(0, 100000)
            self.max_forward_speed_spinbox.setDecimals(0)
            self.max_forward_speed_spinbox.setSingleStep(1)
            self.max_forward_speed_spinbox.setValue(0)
            form_layout.addRow(max_fwd_label, self.max_forward_speed_spinbox)

            # Maximum Turning Speed
            max_turn_label = QLabel("Maximum Turning Speed:")
            max_turn_label.setStyleSheet("""
                QLabel {
                    color: #ffffff;
                    font-weight: bold;
                    font-size: 14px;
                    min-width: 120px;
                }
            """)
            self.max_turning_speed_spinbox = QDoubleSpinBox()
            self.max_turning_speed_spinbox.setRange(0, 100000)
            self.max_turning_speed_spinbox.setDecimals(0)
            self.max_turning_speed_spinbox.setSingleStep(1)
            self.max_turning_speed_spinbox.setValue(0)
            form_layout.addRow(max_turn_label, self.max_turning_speed_spinbox)

        # Place form in a scroll area to make it scrollable
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("QScrollArea { background-color: transparent; }")
        scroll_area.setWidget(form_frame)
        layout.addWidget(scroll_area)

        # Validation info
        validation_label = QLabel("* Required fields")
        validation_label.setStyleSheet("color: #cccccc; font-size: 12px;")
        layout.addWidget(validation_label)

        # Buttons
        self.create_buttons(layout)

    def create_buttons(self, parent_layout):
        """Create dialog buttons"""
        button_layout = QHBoxLayout()

        # Cancel button
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        # Save button
        save_btn = QPushButton("Update Device" if self.is_edit_mode else "Add Device")
        save_btn.clicked.connect(self.save_device)
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #ff6b35;
                color: white;
            }
            QPushButton:hover {
                background-color: #e55a2b;
            }
        """)
        button_layout.addWidget(save_btn)

        parent_layout.addLayout(button_layout)

    def setup_validation(self):
        """Setup input validation"""
        # Connect validation to input changes
        self.device_id_input.textChanged.connect(self.validate_inputs)
        self.device_name_input.textChanged.connect(self.validate_inputs)

    def validate_inputs(self):
        """Validate required inputs"""
        device_id = self.device_id_input.text().strip()
        device_name = self.device_name_input.text().strip()

        # Change border color based on validation
        inputs_validation = [
            (self.device_id_input, bool(device_id)),
            (self.device_name_input, bool(device_name))
        ]

        for widget, is_valid in inputs_validation:
            if is_valid:
                widget.setStyleSheet(widget.styleSheet().replace("border: 2px solid #ff0000;", ""))
            else:
                if "border: 2px solid #ff0000;" not in widget.styleSheet():
                    current_style = widget.styleSheet()
                    widget.setStyleSheet(current_style + "border: 2px solid #ff0000;")

    def populate_fields(self):
        """Populate fields with existing device data"""
        if not self.device_data:
            return

        self.device_id_input.setText(self.device_data.get('device_id', ''))
        self.device_name_input.setText(self.device_data.get('device_name', ''))

        # Device type handling removed

        # Set status
        status = self.device_data.get('status', 'working')
        for i in range(self.status_combo.count()):
            if self.status_combo.itemData(i) == status:
                self.status_combo.setCurrentIndex(i)
                break

        self.battery_spinbox.setValue(int(self.device_data.get('battery_level', 100)))

        # Set speeds if available
        try:
            fs = self.device_data.get('forward_speed', '')
            if fs is not None and str(fs) != '':
                self.forward_speed_spinbox.setValue(int(float(fs)))
        except Exception:
            pass
        try:
            ts = self.device_data.get('turning_speed', '')
            if ts is not None and str(ts) != '':
                self.turning_speed_spinbox.setValue(int(float(ts)))
        except Exception:
            pass

        # Set current location if it exists
        current_location = self.device_data.get('current_location', '')
        if current_location:
            index = self.current_location_combo.findData(current_location)
            if index >= 0:
                self.current_location_combo.setCurrentIndex(index)

    def save_device(self):
        """Save device data"""
        # Validate required fields
        device_id = self.device_id_input.text().strip()
        device_name = self.device_name_input.text().strip()

        if not device_id:
            QMessageBox.warning(self, "Validation Error", "Device ID is required")
            self.device_id_input.setFocus()
            return

        if not device_name:
            QMessageBox.warning(self, "Validation Error", "Device Name is required")
            self.device_name_input.setFocus()
            return

        # Check for duplicate device ID (only for new devices)
        if not self.is_edit_mode:
            # Create device log file
            if not self.create_device_log_file(device_id):
                QMessageBox.warning(self, "Error", "Failed to create device log file")
                return

            # Add initial log entry
            if not self.add_device_log_entry(
                device_id,
                self.status_combo.currentData(),
                self.battery_spinbox.value(),
                "Device initialized"
            ):
                QMessageBox.warning(self, "Error", "Failed to add initial device log entry")
                return

            

        self.accept()

    def create_device_log_file(self, device_id: str) -> bool:
        """Create a new device log file with headers"""
        try:
            device_file_path = Path('data/device_logs') / f"{device_id}.csv"
            device_file_path.parent.mkdir(parents=True, exist_ok=True)

            # Define headers for device-specific CSV
            headers = [
                'timestamp',
                'right_drive',
                'left_drive',
                'right_motor',
                'left_motor',
                'current_location'
            ]

            # Create new file with headers
            with open(device_file_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(headers)

            return True
        except Exception as e:
            print(f"Error creating device log file: {e}")
            return False

    def add_device_log_entry(self, device_id: str, status: str, battery_level: int, notes: str = '') -> bool:
        """Add a new entry to device log file"""
        try:
            current_location = self.current_location_combo.currentData() or ''
            
            # Use DeviceMovementTracker to log initial position (no movement)
            success, error = DeviceMovementTracker.log_device_movement(
                device_id=device_id,
                right_drive=0,  # No initial movement
                left_drive=0,   # No initial movement
                right_motor=0,  # Motors off
                left_motor=0,   # Motors off
                current_location=current_location
            )
            
            if not success:
                raise Exception(error)

            # Set initial facing direction to 'north' for the new device so UI shows Facing immediately
            try:
                nav = get_zone_navigation_manager()
                nav.set_initial_direction(device_id, str(current_location) if current_location else '', 'north')
            except Exception as _e:
                print(f"Warning: failed to set initial facing direction: {_e}")
            return True
        except Exception as e:
            print(f"Error adding device log entry: {e}")
            return False

    def get_device_data(self):
        """Get device data from form"""
        current_time = datetime.now().isoformat()

        data = {
            'device_id': self.device_id_input.text().strip(),
            'device_name': self.device_name_input.text().strip(),
            'forward_speed': int(self.forward_speed_spinbox.value()),
            'turning_speed': int(self.turning_speed_spinbox.value()),
            'status': self.status_combo.currentData(),
            'battery_level': self.battery_spinbox.value(),
            'current_location': self.current_location_combo.currentData() or ''
        }

        # Include additional fields only if present (i.e., in Add mode)
        if hasattr(self, 'device_model_combo'):
            data['device_model'] = self.device_model_combo.currentText()
        if hasattr(self, 'wheel_diameter_spinbox'):
            data['wheel_diameter'] = f"{float(self.wheel_diameter_spinbox.value()):.2f}"
        if hasattr(self, 'distance_between_wheels_spinbox'):
            data['distance_between_wheels'] = f"{float(self.distance_between_wheels_spinbox.value()):.2f}"
        if hasattr(self, 'gear_ratio_spinbox'):
            data['gear_ratio'] = f"{float(self.gear_ratio_spinbox.value()):.2f}"
        if hasattr(self, 'length_spinbox'):
            data['length'] = f"{float(self.length_spinbox.value()):.2f}"
        if hasattr(self, 'width_spinbox'):
            data['width'] = f"{float(self.width_spinbox.value()):.2f}"
        if hasattr(self, 'height_spinbox'):
            data['height'] = f"{float(self.height_spinbox.value()):.2f}"
        if hasattr(self, 'lifting_height_spinbox'):
            data['lifting_height'] = f"{float(self.lifting_height_spinbox.value()):.2f}"
        if hasattr(self, 'max_forward_speed_spinbox'):
            data['max_forward_speed'] = int(self.max_forward_speed_spinbox.value())
        if hasattr(self, 'max_turning_speed_spinbox'):
            data['max_turning_speed'] = int(self.max_turning_speed_spinbox.value())

        # Try to derive current_location and distance from the latest device log entry
        try:
            device_id = data.get('device_id')
            if device_id:
                device_file_path = Path('data/device_logs') / f"{device_id}.csv"
                if device_file_path.exists():
                    with open(device_file_path, 'r', newline='', encoding='utf-8') as f:
                        rows = list(csv.DictReader(f))
                        if rows:
                            last = rows[-1]
                            # Update current_location from log if available
                            log_location = last.get('current_location')
                            if log_location is not None and str(log_location) != '':
                                data['current_location'] = str(log_location)
                            # Set distance from right_drive
                            rd = last.get('right_drive')
                            if rd is not None and str(rd) != '':
                                try:
                                    data['distance'] = f"{float(rd):.2f}"
                                except ValueError:
                                    data['distance'] = "0.00"
                            else:
                                data['distance'] = "0.00"
        except Exception:
            # Non-fatal: if any error occurs, distance may be omitted and handled by sync later
            pass

        if not self.is_edit_mode:
            data['created_at'] = current_time

        data['updated_at'] = current_time

        return data