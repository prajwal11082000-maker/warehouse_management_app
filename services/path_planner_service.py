#!/usr/bin/env python3
"""
Path Planner Service

High-level API to generate path-planning commands (A* + stop handling)
for a device and write them to data/device_logs/path_{device_id}.csv

Usage example:

from services.path_planner_service import plan_and_write_path

plan_and_write_path(
    device_id="DEV001",
    map_id="13",
    zone_sequence=[("1","2"),("2","4"),("4","2"),("2","3"),("3","2"),("2","1")],
    initial_direction="north",   # robot's current facing direction
)

Notes:
- Initial forward offset is taken from latest device log row's right_drive (in mm),
  converted to meters. If missing, defaults to 0.
- Stops are gathered from `data/stops.csv` filtered by the `map_id` and
  matched by zone_connection_id to the edges in `data/zones.csv`.
- The output CSV headers: [command,value,unit]

"""
from __future__ import annotations

import csv
import json
import os
from typing import List, Tuple, Dict, Any, Optional

from robot_navigation.astar_planner import (
    build_graph_from_zones,
    load_stops,
    generate_path_commands,
    serialize_commands_to_csv_rows,
    write_commands_csv,
)

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
ZONES_CSV = os.path.join(DATA_DIR, "zones.csv")
STOPS_CSV = os.path.join(DATA_DIR, "stops.csv")
DEVICE_LOGS_DIR = os.path.join(DATA_DIR, "device_logs")
DEVICES_CSV = os.path.join(DATA_DIR, "devices.csv")


def _read_csv(path: str) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    if not os.path.exists(path):
        return rows
    with open(path, "r", newline="") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append(r)
    return rows


def _read_latest_device_state(device_id: str) -> Dict[str, Any]:
    """Read the last row from data/device_logs/{device_id}.csv.
    Returns fields including right_drive,left_drive,right_motor,left_motor,current_location.
    """
    path = os.path.join(DEVICE_LOGS_DIR, f"{device_id}.csv")
    if not os.path.exists(path):
        return {}
    last: Optional[Dict[str, str]] = None
    with open(path, "r", newline="") as f:
        reader = csv.DictReader(f)
        for r in reader:
            last = r
    return last or {}


def _initial_offset_from_logs(device_id: str) -> float:
    """Meters offset along the current zone from its starting point, based on right_drive (mm)."""
    row = _read_latest_device_state(device_id)
    try:
        rd_mm = float(row.get("right_drive", 0) or 0)
        return rd_mm / 1000.0
    except Exception:
        return 0.0


def _read_device_speeds(device_id: str) -> tuple[int, int]:
    """Read forward_speed and turning_speed from data/devices.csv for the device.
    Returns a tuple (forward_speed, turning_speed) as integers. Defaults to (0,0) if not found.
    """
    fs, ts = 0, 0
    try:
        if not os.path.exists(DEVICES_CSV):
            return fs, ts
        with open(DEVICES_CSV, "r", newline="") as f:
            reader = csv.DictReader(f)
            for r in reader:
                if str(r.get("device_id", "")).strip() == str(device_id).strip():
                    try:
                        fs = int(float(r.get("forward_speed", 0) or 0))
                    except Exception:
                        fs = 0
                    try:
                        ts = int(float(r.get("turning_speed", 0) or 0))
                    except Exception:
                        ts = 0
                    break
    except Exception:
        pass
    return fs, ts


def plan_and_write_path(
    device_id: str,
    map_id: str,
    zone_sequence: List[Tuple[str, str]],
    initial_direction: str,
    output_dir: Optional[str] = None,
) -> str:
    """
    Generate path commands and write to data/device_logs/path_{device_id}.csv.

    - device_id: unique device identifier (used for input log and output file name)
    - map_id: which map to use from zones/stops
    - zone_sequence: ordered list of (from_zone,to_zone) pairs to traverse
    - initial_direction: robot's current facing direction ('north','south','east','west')
    - output_dir: optional override of output directory (defaults to data/device_logs)

    Returns the path to the written file.
    """
    zones_rows = _read_csv(ZONES_CSV)
    stops_rows = _read_csv(STOPS_CSV)

    graph = build_graph_from_zones(zones_rows, map_id)
    stops_by_conn = load_stops(stops_rows, map_id)

    initial_offset_m = _initial_offset_from_logs(device_id)

    fs, ts = _read_device_speeds(device_id)

    cmds = generate_path_commands(
        graph=graph,
        zones_rows=zones_rows,
        stops_by_conn=stops_by_conn,
        zone_sequence=zone_sequence,
        initial_direction=initial_direction,
        initial_offset_m=initial_offset_m,
        forward_speed=fs,
        turning_speed=ts,
    )

    rows = serialize_commands_to_csv_rows(cmds)

    out_dir = output_dir or DEVICE_LOGS_DIR
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"path_{device_id}.csv")

    # Overwrite fully, per-user requirement
    write_commands_csv(out_path, rows)

    return out_path


if __name__ == "__main__":
    # Simple manual smoke test using the example described by the user (map_id 13)
    device = "DEV001"
    path = plan_and_write_path(
        device_id=device,
        map_id="13",
        zone_sequence=[("1","2"),("2","4"),("4","2"),("2","3"),("3","2"),("2","1")],
        initial_direction="north",
    )

