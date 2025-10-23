# Device status options
DEVICE_STATUS = {
    'working': 'Working',
    'charging': 'Charging',
    'issues': 'Issues',
    'maintenance': 'Maintenance'
}

# Task types
TASK_TYPES = {
    'picking': 'Picking',
    'auditing': 'Auditing',
    'maintenance': 'Maintenance',
    'delivery': 'Delivery'
}

# Task status
TASK_STATUS = {
    'pending': 'Pending',
    'running': 'Running',
    'completed': 'Completed',
    'failed': 'Failed',
    'cancelled': 'Cancelled'
}

# Priority levels
PRIORITY_LEVELS = {
    'low': 'Low Priority',
    'medium': 'Medium Priority',
    'high': 'High Priority',
    'urgent': 'Urgent'
}

# Device types section removed

# Map visualization constants
MAP_COLORS = {
    'zone': '#3B82F6',
    'connection': '#10B981',
    'selected_stop': '#EF4444',
    'stop_group': '#8B5CF6',
    'background': '#F8FAFC'
}

# Stop configuration
DEFAULT_BIN_DISTANCE = 2.0

# CSV Headers
CSV_HEADERS = {
    'devices': ['id', 'device_id', 'device_name', 'device_model', 'forward_speed', 'turning_speed', 'status', 'battery_level', 'current_location', 'wheel_diameter', 'distance_between_wheels', 'gear_ratio', 'length', 'width', 'height', 'lifting_height', 'max_forward_speed', 'max_turning_speed', 'distance', 'created_at', 'updated_at'],
    'tasks': ['id', 'task_id', 'task_name', 'task_type', 'status', 'assigned_device_id', 'assigned_user_id', 'description', 'estimated_duration', 'actual_duration', 'created_at', 'started_at', 'completed_at', 'map_id', 'zone_ids', 'stop_ids', 'task_details'],
    'users': ['id', 'username', 'email', 'employee_id', 'profile_picture', 'is_active', 'created_at'],
    'maps': ['id', 'name', 'description', 'width', 'height', 'created_at'],
    'zones': ['id', 'map_id', 'from_zone', 'to_zone', 'magnitude', 'direction', 'zone_type', 'created_at'],
    'stops': ['id', 'zone_connection_id', 'map_id', 'stop_id', 'name', 'x_coordinate', 'y_coordinate', 'left_bins_count', 'right_bins_count', 'left_bins_distance', 'right_bins_distance', 'distance_from_start', 'created_at'],
    'stop_groups': ['id', 'map_id', 'name', 'stop_ids', 'created_at'],
    'products': ['id', 'product_id', 'product_name', 'sku_location_id', 'sku_weight', 'created_at', 'updated_at']
}