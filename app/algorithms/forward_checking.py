"""Forward Checking constraint propagation module.

Responsibility:
    After placing a student in a seat, prune newly invalid seats (occupied seat
    and 4 orthogonal neighbors for same-subject / same-group peers) from affected
    students' candidate domains, recording every removal on an undo trail so
    backtracking can restore domains cleanly.

Implementation scheduled for Phase 7.
"""


def propagate_forward_check(*args, **kwargs):
    """Prune invalid candidate seats and record removals for backtracking restoration."""
    raise NotImplementedError("Forward Checking will be implemented in Phase 7.")


def restore_domains(*args, **kwargs) -> None:
    """Undo domain removals recorded at the current search depth."""
    raise NotImplementedError("Domain restoration will be implemented in Phase 7.")
