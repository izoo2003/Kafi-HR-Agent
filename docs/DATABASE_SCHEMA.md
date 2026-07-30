# DATABASE SCHEMA — HR & Admin Agent

> SQLite, accessed via SQLAlchemy models under `backend/app/models/`. Migrations via Alembic under `backend/alembic/`. This doc is the source of truth for schema — models must match this exactly; if they diverge, update this file in the same PR/session.

Naming convention: `snake_case` table and column names, singular model class names, plural table names (e.g. class `Employee` → table `employees`). All tables have `id` (integer PK, autoincrement), `created_at`, `updated_at` (UTC timestamps) unless noted otherwise.

---

## 1. Identity & Access (RBAC backbone)

### `users`
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| email | TEXT UNIQUE NOT NULL | login identifier |
| password_hash | TEXT NOT NULL | bcrypt/argon2 |
| full_name | TEXT NOT NULL | |
| is_active | BOOLEAN DEFAULT TRUE | soft-disable instead of delete |
| last_login_at | DATETIME NULL | |
| created_at | DATETIME | |
| updated_at | DATETIME | |

### `roles`
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| name | TEXT UNIQUE NOT NULL | e.g. `super_admin`, `hr_manager`, `payroll_officer`, `department_head`, `employee`, `readonly_auditor` |
| description | TEXT | |

### `user_roles` (many-to-many)
| Column | Type | Notes |
|---|---|---|
| user_id | INTEGER FK → users.id | |
| role_id | INTEGER FK → roles.id | |
| PRIMARY KEY (user_id, role_id) | | |

### `agent_access_matrix`
This is the **user role matrix** (in-scope item 6) — who can access which agent/module in the eventual multi-agent system, not just this one.
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| role_id | INTEGER FK → roles.id | |
| agent_key | TEXT NOT NULL | e.g. `hr_admin`, `utilities_maintenance` (future sibling agents referenced by key only, never by foreign import) |
| module_key | TEXT NOT NULL | e.g. `cv_screening`, `payroll`, `kpi`, `attendance`, `admin_panel` |
| permission | TEXT NOT NULL | enum: `none`, `read`, `write`, `approve`, `admin` |

### `permissions` (optional fine-grained layer, if role-level is too coarse)
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| code | TEXT UNIQUE | e.g. `payroll.approve`, `cv.override_score` |
| description | TEXT | |

### `role_permissions` (many-to-many, only if `permissions` table is used)
| Column | Type |
|---|---|
| role_id | INTEGER FK |
| permission_id | INTEGER FK |

---

## 2. Employee & Org Data

### `departments`
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| name | TEXT UNIQUE NOT NULL | |
| head_employee_id | INTEGER FK → employees.id NULL | department head |

### `employees`
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| user_id | INTEGER FK → users.id NULL | linked login account, nullable until employee gets system access |
| employee_code | TEXT UNIQUE NOT NULL | internal ID |
| full_name | TEXT NOT NULL | |
| department_id | INTEGER FK → departments.id | |
| role_title | TEXT NOT NULL | job title, not RBAC role |
| employment_type | TEXT | `full_time`, `part_time`, `contract` |
| date_joined | DATE | |
| date_exited | DATE NULL | |
| status | TEXT | `active`, `on_leave`, `terminated` |
| base_salary | DECIMAL | current base salary, feeds payroll |
| manager_id | INTEGER FK → employees.id NULL | self-referential reporting line |

---

## 3. CV Screening

### `job_descriptions`
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| title | TEXT NOT NULL | |
| department_id | INTEGER FK → departments.id | |
| description_text | TEXT NOT NULL | |
| requirements_text | TEXT | |
| file_path | TEXT NULL | stored Word/PDF source |
| status | TEXT | `draft`, `open`, `closed` |
| created_by | INTEGER FK → users.id | |

### `scoring_criteria`
Per-role CV scoring rubric (in-scope item 2).
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| job_description_id | INTEGER FK → job_descriptions.id | |
| criterion_name | TEXT NOT NULL | e.g. `years_experience`, `required_skill_match`, `education_level` |
| weight | FLOAT NOT NULL | contributes to total score, weights per job description should sum to 1.0 or 100 |
| scoring_rules | JSON | structured rule definition (thresholds, keyword lists, point mapping) — schema detailed in `FEATURE_CV_SCREENING.md` |

### `candidates`
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| job_description_id | INTEGER FK → job_descriptions.id | |
| full_name | TEXT | extracted or manually entered |
| email | TEXT NULL | |
| phone | TEXT NULL | |
| cv_file_path | TEXT NOT NULL | original uploaded file |
| parsed_data | JSON | structured extraction output (education, experience, skills, etc.) |
| status | TEXT | `uploaded`, `parsed`, `scored`, `shortlisted`, `rejected`, `hired` |

### `candidate_scores`
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| candidate_id | INTEGER FK → candidates.id | |
| scoring_criteria_id | INTEGER FK → scoring_criteria.id | |
| raw_score | FLOAT | score for this individual criterion |
| notes | TEXT NULL | |

### `candidate_rankings`
Denormalized/cached ranking result per job description, refreshed on scoring changes.
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| job_description_id | INTEGER FK → job_descriptions.id | |
| candidate_id | INTEGER FK → candidates.id | |
| total_score | FLOAT | |
| rank_position | INTEGER | |
| computed_at | DATETIME | |

---

## 4. Attendance

### `attendance_rules`
Attendance sheet format & rules (in-scope item 3), configurable rather than hardcoded.
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| name | TEXT | e.g. `standard_9to6` |
| shift_start | TIME | |
| shift_end | TIME | |
| grace_period_minutes | INTEGER | before marked late |
| half_day_threshold_minutes | INTEGER | minutes present to count as half day |
| applies_to_department_id | INTEGER FK → departments.id NULL | NULL = company-wide |

### `attendance_records`
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| employee_id | INTEGER FK → employees.id | |
| date | DATE NOT NULL | |
| check_in | DATETIME NULL | |
| check_out | DATETIME NULL | |
| source | TEXT | `biometric`, `manual`, `import` |
| status | TEXT | `present`, `absent`, `late`, `half_day`, `on_leave`, `holiday` |
| notes | TEXT NULL | |
| UNIQUE (employee_id, date) | | one record per employee per day |

### `leave_requests`
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| employee_id | INTEGER FK → employees.id | |
| leave_type | TEXT | `annual`, `sick`, `unpaid`, `other` |
| start_date | DATE | |
| end_date | DATE | |
| status | TEXT | `pending`, `approved`, `rejected` |
| approved_by | INTEGER FK → users.id NULL | |
| reason | TEXT NULL | |

---

## 5. Payroll

### `payroll_structures`
Per-employee or per-role pay structure (in-scope item 4).
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| employee_id | INTEGER FK → employees.id | |
| base_salary | DECIMAL NOT NULL | |
| overtime_rate_per_hour | DECIMAL NULL | |
| effective_from | DATE | |
| effective_to | DATE NULL | |

### `payroll_runs`
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| period_month | INTEGER | 1-12 |
| period_year | INTEGER | |
| status | TEXT | `draft`, `pending_approval`, `approved`, `paid` |
| created_by | INTEGER FK → users.id | |
| approved_by | INTEGER FK → users.id NULL | |
| approved_at | DATETIME NULL | |

### `payslips`
One row per employee per payroll run.
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| payroll_run_id | INTEGER FK → payroll_runs.id | |
| employee_id | INTEGER FK → employees.id | |
| base_amount | DECIMAL | |
| overtime_hours | DECIMAL DEFAULT 0 | |
| overtime_amount | DECIMAL DEFAULT 0 | |
| deductions_amount | DECIMAL DEFAULT 0 | |
| advances_deducted | DECIMAL DEFAULT 0 | |
| net_pay | DECIMAL | computed |
| generated_pdf_path | TEXT NULL | |

### `deductions`
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| payslip_id | INTEGER FK → payslips.id | |
| type | TEXT | `absence`, `late`, `tax`, `other` |
| amount | DECIMAL | |
| notes | TEXT NULL | |

### `salary_advances`
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| employee_id | INTEGER FK → employees.id | |
| amount | DECIMAL | |
| date_requested | DATE | |
| status | TEXT | `pending`, `approved`, `rejected`, `fully_recovered` |
| amount_recovered | DECIMAL DEFAULT 0 | |
| approved_by | INTEGER FK → users.id NULL | |

---

## 6. KPI

### `kpi_definitions`
Per-department KPI definitions (in-scope item 5).
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| department_id | INTEGER FK → departments.id | |
| name | TEXT NOT NULL | |
| description | TEXT | |
| measurement_unit | TEXT | e.g. `%`, `count`, `score_1_5` |
| target_value | DECIMAL | |
| weight | FLOAT | contribution to overall department/employee score |
| review_period | TEXT | `monthly`, `quarterly`, `annual` |
| is_archived | BOOLEAN | soft-archive via DELETE; excluded from weight checks & rollups |

### `kpi_entries`
Actuals recorded per employee per period. Unique on `(kpi_definition_id, employee_id, period_start, period_end)`.
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| kpi_definition_id | INTEGER FK → kpi_definitions.id | |
| employee_id | INTEGER FK → employees.id | |
| period_start | DATE | |
| period_end | DATE | |
| actual_value | DECIMAL | |
| score | FLOAT | normalized score against target |
| recorded_by | INTEGER FK → users.id | |
| notes | TEXT NULL | |

---

## 7. Audit Logging

### `audit_logs`
Every meaningful action across all modules (in-scope item 7).
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| user_id | INTEGER FK → users.id NULL | null for system actions |
| action | TEXT NOT NULL | e.g. `payroll.approve`, `cv.score_override`, `user.role_change` |
| entity_type | TEXT | e.g. `payslip`, `candidate`, `kpi_entry` |
| entity_id | INTEGER NULL | |
| before_state | JSON NULL | snapshot before change |
| after_state | JSON NULL | snapshot after change |
| ip_address | TEXT NULL | |
| timestamp | DATETIME NOT NULL | |

Retention, filtering UI, and query patterns are detailed in `FEATURE_AUDIT_LOG.md`.

---

## 8. Integration / System Config

### `integration_registry`
Stub table for future orchestrator wiring — no-op today, referenced by `interface.py`.
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| agent_key | TEXT UNIQUE | `hr_admin` |
| status | TEXT | `standalone`, `registered` |
| registered_at | DATETIME NULL | |

### `system_config`
Generic key-value store for scoring weight defaults, KPI templates, etc. (avoids hardcoding, keeps `config/` as source but allows runtime overrides).
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| key | TEXT UNIQUE | |
| value | JSON | |
| updated_by | INTEGER FK → users.id NULL | |

---

## 9. Migration Notes

- Every schema change goes through an Alembic migration — never hand-edit the SQLite file.
- Migrations must be additive/backward-compatible where possible, since this agent may run alongside sibling agents' own databases eventually (each agent owns its own DB — no cross-agent foreign keys).
- `agent_key` and `module_key` fields anywhere in this schema are plain strings, not foreign keys into another agent's tables — this preserves the bounded-module principle from `PROJECT_OVERVIEW.md`.
