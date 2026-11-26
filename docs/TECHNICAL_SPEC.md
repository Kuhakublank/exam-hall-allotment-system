# Technical Specification & Implementation Roadmap

**Project Title:** Automated Examination Hall Allotment and Seating Arrangement System  
**Author:** Gobinda Basak (034973-23) — Kathmandu University School of Education (ITEX 499)  
**Primary Reference:** Revised Project Proposal (October 2026) + Approved Design Decisions

---

## 1. Approved Technology Stack

- **Frontend:** HTML, CSS, JavaScript, Bootstrap 5
- **Backend:** Python (3.15.2 verified locally via `py`) with Flask
- **Database:** PostgreSQL 17 (`exam_seating_db` on `localhost:5432`) with SQLAlchemy + Flask-Migrate (Alembic)
- **File Processing:** `pandas` + `openpyxl` (CSV/XLSX import)
- **Reporting:** HTML print view (`@media print`) + `reportlab` PDF export
- **Testing:** `pytest` (using synthetic data only)
- **Optional Verification Solver:** Google OR-Tools CP-SAT (`ortools`, verification aid only)

---

## 2. Core Seating Constraints (All Must Be Enforced)

1. A student must receive **exactly one** seat.
2. A seat can accommodate **at most one** student.
3. Students taking the **same subject** cannot sit immediately beside one another.
4. Students belonging to the **same configured group** cannot sit immediately beside one another.
5. Adjacency restriction applies in **four orthogonal directions**: **Left, Right, Front, Back**.
6. **Diagonal** seating is permitted under this adjacency rule.
7. **Blocked seats** must never be assigned.
8. Students with **accessibility requirements** must receive appropriate seats when mandatory.
9. **Hall capacity** must never be exceeded.

---

## 3. Approved Design Decisions

1. **FFD + Same-Subject Separation:** Use standard **First-Fit Decreasing (FFD)** without imposing an arbitrary 50% subject capacity limit per hall. FFD allocates groups based on group size and available usable hall capacity. The seating engine enforces separation and reports infeasibility (never producing an invalid plan) if a hall cannot be seated validly.
2. **Exam & Subject Structure:** A single **Exam Session** (same date and time) can contain **multiple subjects**. Students from different subjects can share halls while respecting 4-way orthogonal separation.
3. **Accessible Seats:** Accessible seats are **prioritized** for students requiring accessible seating. Once all such students are accommodated, remaining accessible seats may be assigned to regular students.
4. **Configured Group Definition:** Default configured group is **`class + section`** (e.g., `CS-A`, `CS-B`, `IT-A`), designed flexibly so administrators can configure grouping rules in Constraint Management.
5. **Database & Project Root:** PostgreSQL 17 at `exam_seating_db`, project directory `C:\Users\kuhaku\Documents\Exam-Hall-Allotment-System`.

---

## 4. Algorithms & Strict Separation of Responsibilities

- **Hall Allotment:** **First-Fit Decreasing (FFD)** — sort groups largest-first, place each in the first hall with enough remaining usable capacity (splitting only when no single hall fits). Report capacity shortfalls immediately.
- **Main Seating Engine:** **Backtracking Search + Minimum Remaining Values (MRV) + Forward Checking** — maintains candidate-seat domains, restores domains cleanly on backtrack via an undo trail, enforces configurable node/time limits, and distinguishes `infeasible` from `inconclusive`.
- **Baseline Comparison:** **Greedy First-Fit** — strictly separate baseline (never replaces Backtracking) for quantitative comparison on the same synthetic datasets.
- **Validation & Conflict Checker:** Independent auditor checking all 9 constraints and computing completeness, capacity violations, duplicate seats, same-subject/group conflicts, blocked-seat violations, utilization, processing time, and search effort.
- **Optional Verifier:** **Google OR-Tools CP-SAT** for cross-checking small/medium test cases.

---

## 5. Database Schema (PostgreSQL)

1. `users` (`user_id`, `username`, `email`, `password_hash`, `role`, `created_at`)
2. `students` (`student_id`, `roll_number` unique, `name`, `class_name`, `section`, `requires_accessible_seat`, `accessibility_notes`)
3. `subjects` (`subject_id`, `subject_code` unique, `subject_name`)
4. `exam_sessions` (`session_id`, `title`, `exam_date`, `start_time`, `end_time`)
5. `exam_registrations` (`registration_id`, `session_id` FK, `student_id` FK, `subject_id` FK, `group_label`) — resolves M:N between students, subjects, and sessions
6. `halls` (`hall_id`, `hall_name` unique, `rows`, `columns`, `capacity`)
7. `seats` (`seat_id`, `hall_id` FK, `row_num`, `col_num`, `seat_label`, `is_blocked`, `is_accessible`)
8. `constraint_configs` (`config_id`, `session_id` FK, `separate_same_subject`, `separate_same_group`, `group_rule`, `accessibility_mandatory`, `deterministic`, `random_seed`, `max_nodes`, `time_limit_seconds`)
9. `allocation_runs` (`run_id`, `session_id` FK, `config_id` FK, `algorithm_type`, `status`, `is_authorized`, `processing_time_ms`, `placements_tried`, `backtracks_count`, `metrics_json`, `created_at`)
10. `seating_assignments` (`assignment_id`, `run_id` FK, `session_id` FK, `student_id` FK, `hall_id` FK, `seat_id` FK)

---

## 6. Modular Directory Layout

- `app/__init__.py`, `app/config.py` — Flask app factory & `.env`-backed config
- `app/models/` — SQLAlchemy models (`user.py`, `student.py`, `exam.py`, `hall.py`, `allocation.py`)
- `app/algorithms/` — Pure Python algorithms (`structures.py`, `hall_allotment_ffd.py`, `mrv.py`, `forward_checking.py`, `backtracking.py`, `greedy.py`, `validator.py`, `cpsat_verifier.py`)
- `app/services/` — Service layer (`import_service.py`, `allocation_service.py`, `report_service.py`)
- `app/routes/` — Flask Blueprints with server-side validation & admin auth protection
- `app/templates/`, `app/static/` — Bootstrap 5 UI, interactive hall grid, print views
- `migrations/` — Flask-Migrate / Alembic migrations
- `tests/` — `unit/`, `integration/`, `synthetic/`

---

## 7. Phased Implementation Roadmap (Build & Test Incrementally)

- **Phase 1 (Current):** Project skeleton, `.venv` (Python 3.15), `.gitignore`, `.env.example`, PostgreSQL config, all SQLAlchemy models, initial Flask-Migrate migration to `exam_seating_db`, `README.md`, and schema tests.
- **Phase 2:** User & Access Management (login/logout, password hashing, `@login_required`, admin CLI seed, Bootstrap 5 base layout & dashboard).
- **Phase 3:** Hall & Seat Layout Management (hall CRUD, auto seat grid, interactive blocked/accessible seat editor, tests).
- **Phase 4:** Student Management & Pandas/OpenPyXL CSV/XLSX Importer (validation, sample template, error reporting, tests).
- **Phase 5:** Subject, Exam Session, Registration & Constraint Configuration UI + tests.
- **Phase 6:** Hall Allotment Engine (standard FFD + capacity/shortfall checks + unit tests).
- **Phase 7:** Seating Engines (Backtracking + MRV + Forward Checking + undo trail + limits, and separate Greedy First-Fit baseline + unit tests).
- **Phase 8:** Validation & Conflict Checker + optional OR-Tools CP-SAT verifier + tests.
- **Phase 9:** Web Integration, Visual Hall Grid, Greedy vs. Backtracking Comparison UI, Student Lookup & Printable/PDF Reports.
- **Phase 10:** Synthetic Evaluation Benchmark Suite (Proposal Table 8 metrics), full integration tests, and final `README.md` polish.
