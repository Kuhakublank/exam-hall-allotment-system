"""Shared pure-Python data structures for hall allotment and seating algorithms.

These classes keep the algorithm layer independent of Flask and SQLAlchemy.
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class StudentInput:
    """Represents one examinee entering the allocation pipeline."""

    student_id: int
    roll_number: str
    subject_code: str
    group_label: str
    requires_accessible_seat: bool = False


@dataclass(frozen=True)
class SeatNode:
    """Represents one physical seat in a hall grid."""

    seat_id: int
    hall_id: int
    row_num: int
    col_num: int
    seat_label: str
    is_blocked: bool = False
    is_accessible: bool = False


@dataclass
class HallGrid:
    """Represents a hall's capacity and seat layout."""

    hall_id: int
    hall_name: str
    rows: int
    columns: int
    capacity: int
    seats: list[SeatNode] = field(default_factory=list)


@dataclass(frozen=True)
class ConstraintOptions:
    """Active constraint settings passed to the seating engine."""

    separate_same_subject: bool = True
    separate_same_group: bool = True
    accessibility_mandatory: bool = True
    deterministic: bool = True
    random_seed: int | None = None
    max_nodes: int = 100000
    time_limit_seconds: int = 10
