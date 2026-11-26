"""First-Fit Decreasing (FFD) hall allotment algorithm.

Responsibility:
    Sort student groups (by subject or configured group) from largest to smallest
    and assign each group to the first hall with enough remaining usable capacity,
    splitting a group only when no single hall can hold it.

Implementation scheduled for Phase 6.
"""

from app.algorithms.structures import HallGrid, StudentInput


def allot_halls_ffd(students: list[StudentInput], halls: list[HallGrid]) -> dict:
    """Allocate examinee groups to halls using standard First-Fit Decreasing."""
    raise NotImplementedError("FFD hall allotment will be implemented in Phase 6.")
