"""Minimum Remaining Values (MRV) heuristic module.

Responsibility:
    Select the next unassigned student who currently has the fewest valid
    candidate seats remaining, ensuring special-needs and tightly constrained
    students are placed before dead ends multiply.

Implementation scheduled for Phase 7.
"""


def select_next_student_mrv(domains: dict[int, list[int]], assigned: dict[int, int]) -> int:
    """Return the unassigned student_id with the smallest remaining candidate domain."""
    raise NotImplementedError("MRV heuristic will be implemented in Phase 7.")
