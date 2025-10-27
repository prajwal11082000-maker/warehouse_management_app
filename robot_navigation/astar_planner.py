#!/usr/bin/env python3
"""
A* Path Planner and Command Generator for zone-based maps.

- Builds a directed graph from `zones.csv` for a given `map_id`.
- Optionally runs A* to compute a shortest path between zones.
- Generates motor commands for moving along each edge and handling stops.
- Serializes commands to a list of CSV rows [command, value, unit].

Assumptions and conventions:
- Distance/magnitude in `zones.csv` are in meters. We convert to millimeters for F,SR,SL commands.
- Turn commands: PVTR (right), PVTL (left), 90/180 DEG.
- Forward command: F,<mm>,MM
- Side commands: SR/SL,<mm>,MM then return SL/SR with same distance.
- Stops are described in `stops.csv` using `zone_connection_id` that maps to an edge (from_zone->to_zone).
- Side selection heuristic:
    1) If left_bins_count>0 and right_bins_count==0 => left
    2) If right_bins_count>0 and left_bins_count==0 => right
    3) Else parse stop_id/name for 'LEFT'/'RIGHT' tokens (case-insensitive)
    4) Else default to right

Orientation logic (critical and consistent with existing `ZoneNavigationManager`):
- north + right => east
- north + left  => west
- south + right => west
- south + left  => east
- east + right  => south
- east + left   => north
- west + right  => north
- west + left   => south

Author: Cascade A* module
"""
from __future__ import annotations

import csv
import heapq
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional, Any

# Types
ZoneId = str
Direction = str  # 'north'|'south'|'east'|'west'


@dataclass
class Edge:
    from_zone: ZoneId
    to_zone: ZoneId
    distance_m: float
    direction: Direction
    connection_id: Optional[int] = None


class ZoneGraph:
    def __init__(self):
        self.adj: Dict[ZoneId, List[Edge]] = {}

    def add_edge(self, edge: Edge):
        self.adj.setdefault(edge.from_zone, []).append(edge)

    def neighbors(self, zone: ZoneId) -> List[Edge]:
        return self.adj.get(zone, [])


# Directions and turning logic
TURN_MAP = {
    'north': {'left': 'west', 'right': 'east'},
    'south': {'left': 'east', 'right': 'west'},
    'east':  {'left': 'north', 'right': 'south'},
    'west':  {'left': 'south', 'right': 'north'},
}

# Determine required turn from current_direction to target_direction
# Returns tuple (turn_cmd: Optional[str], degrees: Optional[int])
# turn_cmd in {'PVTR','PVTL'}; degrees in {90,180} or None when no turn

def compute_turn(current_direction: Direction, target_direction: Direction) -> Tuple[Optional[str], Optional[int]]:
    cur = current_direction.lower()
    tgt = target_direction.lower()
    if cur == tgt:
        return None, None
    # 180 U-turn if opposite
    opposite = {
        'north': 'south', 'south': 'north', 'east': 'west', 'west': 'east'
    }
    if opposite.get(cur) == tgt:
        # Use right 180 as in user examples
        return 'PVTR', 180
    # figure left/right 90
    for turn, ndir in TURN_MAP[cur].items():
        if ndir == tgt:
            return ('PVTL', 90) if turn == 'left' else ('PVTR', 90)
    # Fallback
    return 'PVTR', 90


# A* (zones weighted by distance)

def heuristic(a: ZoneId, b: ZoneId) -> float:
    # Simple admissible heuristic: 0 (Dijkstra). Extend later if we have coordinates.
    return 0.0


def astar_path(graph: ZoneGraph, start: ZoneId, goal: ZoneId) -> List[ZoneId]:
    frontier: List[Tuple[float, ZoneId]] = []
    heapq.heappush(frontier, (0.0, start))
    came_from: Dict[ZoneId, Optional[ZoneId]] = {start: None}
    cost_so_far: Dict[ZoneId, float] = {start: 0.0}

    while frontier:
        _, current = heapq.heappop(frontier)
        if current == goal:
            break
        for edge in graph.neighbors(current):
            new_cost = cost_so_far[current] + edge.distance_m
            if edge.to_zone not in cost_so_far or new_cost < cost_so_far[edge.to_zone]:
                cost_so_far[edge.to_zone] = new_cost
                priority = new_cost + heuristic(edge.to_zone, goal)
                heapq.heappush(frontier, (priority, edge.to_zone))
                came_from[edge.to_zone] = current

    # Reconstruct
    if goal not in came_from:
        return []
    path: List[ZoneId] = []
    cur: Optional[ZoneId] = goal
    while cur is not None:
        path.append(cur)
        cur = came_from[cur]
    path.reverse()
    return path


# Stops handling
@dataclass
class Stop:
    connection_id: int
    name: str
    distance_from_start_m: float
    side: str  # 'left'|'right'
    side_distance_m: float
    stop_type: str  # 'left'|'right'|'center'|''


def infer_side(stop_row: Dict[str, Any]) -> str:
    left_count = int(float(stop_row.get('left_bins_count', 0) or 0))
    right_count = int(float(stop_row.get('right_bins_count', 0) or 0))
    stop_id = (stop_row.get('stop_id') or '').lower()
    name = (stop_row.get('name') or '').lower()
    if left_count > 0 and right_count == 0:
        return 'left'
    if right_count > 0 and left_count == 0:
        return 'right'
    if 'left' in stop_id or 'left' in name:
        return 'left'
    if 'right' in stop_id or 'right' in name:
        return 'right'
    # default
    return 'right'


def build_graph_from_zones(zones_rows: List[Dict[str, str]], map_id: str) -> ZoneGraph:
    g = ZoneGraph()
    for r in zones_rows:
        if str(r.get('map_id')) != str(map_id):
            continue
        try:
            edge = Edge(
                from_zone=str(r['from_zone']).strip(),
                to_zone=str(r['to_zone']).strip(),
                distance_m=float(r['magnitude']),
                direction=str(r['direction']).lower().strip(),
                connection_id=int(r['id']) if r.get('id') else None,
            )
            g.add_edge(edge)
        except Exception:
            continue
    return g


def load_stops(stops_rows: List[Dict[str, str]], map_id: str) -> Dict[int, List[Stop]]:
    by_conn: Dict[int, List[Stop]] = {}
    for r in stops_rows:
        if str(r.get('map_id')) != str(map_id):
            continue
        try:
            conn_id = int(r['zone_connection_id'])
            dist_m = float(r['distance_from_start'])
            # Stop type from CSV (may be missing in legacy rows)
            stype = str(r.get('stop_type', '') or '').strip().lower()
            # Prefer explicit stop_type for side; otherwise infer
            if stype in ('left', 'right'):
                side = stype
            else:
                side = infer_side(r)
            # Robust parse for distances; treat N/A or blanks as 0
            def _to_float(val: Any) -> float:
                try:
                    return float(val)
                except Exception:
                    return 0.0
            left_d = _to_float(r.get('left_bins_distance'))
            right_d = _to_float(r.get('right_bins_distance'))
            # For center, no lateral movement
            side_dist_m = 0.0 if stype == 'center' else (left_d if side == 'left' else right_d)
            by_conn.setdefault(conn_id, []).append(
                Stop(
                    connection_id=conn_id,
                    name=r.get('name') or '',
                    distance_from_start_m=dist_m,
                    side=side,
                    side_distance_m=side_dist_m,
                    stop_type=stype,
                )
            )
        except Exception:
            continue
    # sort by distance
    for k in by_conn:
        by_conn[k].sort(key=lambda s: s.distance_from_start_m)
    return by_conn


def mm(meters: float) -> int:
    return int(round(meters * 1000))


def generate_edge_commands(
    edge: Edge,
    current_direction: Direction,
    current_offset_m: float,
    stops_on_edge: List[Stop],
) -> Tuple[List[Tuple[Any, ...]], Direction]:
    """
    Generate commands to traverse a single edge from current offset to end, visiting stops.
    Returns (commands, new_direction)
    """
    commands: List[Tuple[Any, ...]] = []

    # Turn if needed before entering edge direction
    turn_cmd, deg = compute_turn(current_direction, edge.direction)
    if turn_cmd and deg:
        commands.append(('ALIGN', str(edge.from_zone), '0', '0'))
        commands.append((turn_cmd, deg, 'DEG'))
        current_direction = edge.direction  # orientation after the turn

    # Travel along the edge, accounting for current offset
    traveled_m = max(0.0, float(current_offset_m))
    total_m = float(edge.distance_m)

    def forward_to(target_m: float):
        nonlocal traveled_m
        delta = max(0.0, target_m - traveled_m)
        if delta > 0:
            commands.append(('F', mm(delta), 'MM'))
            traveled_m += delta

    # Visit each stop in order
    for stop in stops_on_edge:
        # Go forward to stop longitudinal position
        forward_to(stop.distance_from_start_m)
        # If center stop or side distance is 0/N/A, wait-in instead of lateral move
        stype = (stop.stop_type or '').lower()
        if stype == 'center' or (stop.side_distance_m is None or stop.side_distance_m <= 0.0):
            commands.append(('WAITIN', 2, 5, 1))
        else:
            # Side approach and return
            if stop.side == 'left':
                commands.append(('SL', mm(stop.side_distance_m), 'MM'))
                commands.append(('SR', mm(stop.side_distance_m), 'MM'))
            else:
                commands.append(('SR', mm(stop.side_distance_m), 'MM'))
                commands.append(('SL', mm(stop.side_distance_m), 'MM'))

    # Finish remaining forward distance to end of edge
    forward_to(total_m)

    return commands, current_direction


def generate_path_commands(
    graph: ZoneGraph,
    zones_rows: List[Dict[str, str]],
    stops_by_conn: Dict[int, List[Stop]],
    zone_sequence: List[Tuple[ZoneId, ZoneId]],
    initial_direction: Direction,
    initial_offset_m: float,
    forward_speed: Optional[int] = None,
    turning_speed: Optional[int] = None,
) -> List[Tuple[Any, ...]]:
    # map connection by (from,to) to edge
    conn_lookup: Dict[Tuple[str, str], Edge] = {}
    for r in zones_rows:
        try:
            edge = Edge(
                from_zone=str(r['from_zone']).strip(),
                to_zone=str(r['to_zone']).strip(),
                distance_m=float(r['magnitude']),
                direction=str(r['direction']).lower().strip(),
                connection_id=int(r['id']) if r.get('id') else None,
            )
            conn_lookup[(edge.from_zone, edge.to_zone)] = edge
        except Exception:
            continue

    cmds: List[Tuple[Any, ...]] = []
    cur_dir = initial_direction
    offset_m_for_first_edge = initial_offset_m

    last_arrival_zone: Optional[str] = None
    for i, (fz, tz) in enumerate(zone_sequence):
        if i == 0 and initial_offset_m <= 0.0:
            try:
                cmds.append(('ALIGN', str(fz), '0', '0'))
            except Exception:
                pass
        edge = conn_lookup.get((str(fz), str(tz)))
        if not edge:
            # try to compute A* between zones and expand
            path = astar_path(graph, str(fz), str(tz))
            if not path or len(path) < 2:
                # cannot move, skip
                continue
            # turn path into pair edges
            sub_pairs = list(zip(path[:-1], path[1:]))
            for j, (sf, st) in enumerate(sub_pairs):
                sub_edge = conn_lookup.get((sf, st))
                if not sub_edge:
                    continue
                stops = stops_by_conn.get(sub_edge.connection_id or -1, [])
                seg_cmds, cur_dir = generate_edge_commands(
                    sub_edge, cur_dir, offset_m_for_first_edge if (i == 0 and j == 0) else 0.0, stops
                )
                cmds.extend(seg_cmds)
                last_arrival_zone = sub_edge.to_zone
            offset_m_for_first_edge = 0.0
        else:
            stops = stops_by_conn.get(edge.connection_id or -1, [])
            seg_cmds, cur_dir = generate_edge_commands(
                edge, cur_dir, offset_m_for_first_edge if i == 0 else 0.0, stops
            )
            cmds.extend(seg_cmds)
            offset_m_for_first_edge = 0.0
            last_arrival_zone = edge.to_zone

    # Append final ALIGN at the last arrival zone, if available
    if last_arrival_zone is not None:
        try:
            cmds.append(('ALIGN', str(last_arrival_zone), '0', '0'))
        except Exception:
            pass
    # Augment commands with speeds where requested
    aug_cmds: List[Tuple[Any, ...]] = []
    for c in cmds:
        try:
            if not isinstance(c, (tuple, list)) or len(c) < 3:
                aug_cmds.append(c)
                continue
            op = str(c[0]).upper()
            if op == 'F' and forward_speed is not None:
                aug_cmds.append((c[0], c[1], c[2], int(forward_speed)))
            elif op in ('PVTR', 'PVTL') and turning_speed is not None:
                aug_cmds.append((c[0], c[1], c[2], int(turning_speed)))
            elif op in ('SR', 'SL') and turning_speed is not None:
                aug_cmds.append((c[0], c[1], c[2], int(turning_speed)))
            else:
                aug_cmds.append(c)
        except Exception:
            aug_cmds.append(c)
    return aug_cmds


def serialize_commands_to_csv_rows(cmds: List[Tuple[Any, ...]]) -> List[List[str]]:
    rows: List[List[str]] = [["command", "value", "unit"]]
    # Ensure first command row is HOMING,ALL as requested
    rows.append(["HOMING", "ALL"])
    for item in cmds:
        try:
            if isinstance(item, (list, tuple)):
                rows.append([str(x) for x in item])
            else:
                rows.append([str(item)])
        except Exception:
            rows.append([str(item)])
    return rows


def write_commands_csv(path: str, rows: List[List[str]]):
    with open(path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerows(rows)
