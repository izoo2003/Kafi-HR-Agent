# DATABASE SCHEMA — HR & Admin Agent

> SQLite, accessed via SQLAlchemy models under `backend/app/models/`. Migrations via Alembic under `backend/alembic/`. This doc is the source of truth for schema — models must match this exactly; if they diverge, update this file in the same PR/session.

Naming convention: `snake_case` table and column names, singular model class names, plural table names (e.g. class `Employee` → table `employees`). All tables have `id` (integer PK, autoincrement), `created_at`, `updated_at` (UTC timestamps) unless noted otherwise.

---

## 1. Identity & Access (RBAC backbone)

### `users`
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| email | TEXT UNIQUE NOT NULL | login identifier (staff); self-registered accounts use `{username}@self.kafi-hr.local` |
| username | TEXT UNIQUE NULL | self-service login identifier; null for staff who sign in with email |
| password_hash | TEXT NOT NULL | bcrypt/argon2 of password or PIN |
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
| job_description_text | TEXT NULL | department-level duties / job description |
| sops_text | TEXT NULL | department standard operating procedures |

### `employees`
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| user_id | INTEGER FK → users.id NULL | linked login account, nullable until employee gets system access |
| employee_code | TEXT UNIQUE NOT NULL | internal ID |
| full_name | TEXT NOT NULL | |
| department_id | INTEGER FK → departments.id | Role assignment in UI — departments act as selectable roles |
| role_title | TEXT NOT NULL | synced from department name when role is assigned |
| job_description_text | TEXT NULL | duties/requirements for this employee (internal JD — not a hiring job posting) |
| employment_type | TEXT | `full_time`, `part_time`, `contract` |
| date_joined | DATE | |
| date_exited | DATE NULL | |
| status | TEXT | `active`, `on_leave`, `terminated` |
| base_salary | DECIMAL | net/base salary shown in Salary details; feeds payroll |
| manager_id | INTEGER FK → employees.id NULL | self-referential reporting line |
| cnic | TEXT NULL | national ID |
| email | TEXT NULL | personal email |
| personal_mobile | TEXT NULL | |
| alternate_mobile | TEXT NULL | |
| father_name | TEXT NULL | |
| date_of_birth | DATE NULL | |
| gender | TEXT NULL | |
| marital_status | TEXT NULL | |
| current_address | TEXT NULL | |
| permanent_address | TEXT NULL | |
| city | TEXT NULL | |
| nationality | TEXT NULL | |
| location | TEXT NULL | workplace site: `Mill`, `Clifton Office`, `KMP House` |
| bank_name | TEXT NULL | |
| account_title | TEXT NULL | |
| account_number | TEXT NULL | |
| iban | TEXT NULL | |
| branch_name | TEXT NULL | |
| branch_code | TEXT NULL | |

### `employee_documents`
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| employee_id | INTEGER FK → employees.id | |
| category | TEXT NOT NULL | `cnic_front`, `cnic_back`, `cnic` (legacy), `education`, `photo`, `other`, `client` — CNIC front/back are images only (no PDF) |
| title | TEXT NULL | optional label |
| file_path | TEXT NOT NULL | Prefer Supabase Storage URI `supabase://{bucket}/emp_{id}/...` when Storage is configured; legacy local paths under `data/uploads/employees/` still supported |
| original_filename | TEXT NOT NULL | |
| mime_type | TEXT NULL | |
| created_at / updated_at | DATETIME | |

### `employee_references` (Client Referrals in UI)
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| employee_id | INTEGER FK → employees.id | |
| full_name | TEXT NOT NULL | reference name |
| relation | TEXT NOT NULL | relation to the employee |
| phone | TEXT NULL | phone number |
| cnic | TEXT NULL | |
| notes | TEXT NULL | |
| created_at / updated_at | DATETIME | |

### `employee_reference_documents`
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| reference_id | INTEGER FK → employee_references.id | |
| file_path | TEXT NOT NULL | Prefer `supabase://{bucket}/emp_{id}/references/...`; legacy local paths OK |
| original_filename | TEXT NOT NULL | |
| mime_type | TEXT NULL | |
| created_at / updated_at | DATETIME | |

---

## 3. CV Screening

### `job_descriptions`
Hiring **job postings** (open roles for CV screening). UI label: Job Postings. Distinct from `employees.job_description_text` (internal duties for current staff).
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| title | TEXT NOT NULL | |
| department_id | INTEGER FK → departments.id | |
| description_text | TEXT NOT NULL | |
| requirements_text | TEXT | |
| file_path | TEXT NULL | stored Word/PDF source |
| image_paths | JSON NULL | list of posting image URIs (Supabase or local `data/uploads/jobs/`) |
| status | TEXT | `draft`, `open`, `closed` |
| created_by | INTEGER FK → users.id | |
| linkedin_posts | JSON NULL | per-account results when posted (`account`, `author_urn`, `post_urn`, `post_url`, `posted_at`, `error`) |

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
| job_description_id | INTEGER FK → job_descriptions.id NULL | NULL = fetched but not yet matched/assigned to a role (see §11 of `FEATURE_CV_SCREENING.md`) |
| full_name | TEXT | extracted or manually entered |
| email | TEXT NULL | |
| phone | TEXT NULL | |
| cv_file_path | TEXT NOT NULL | original uploaded file |
| parsed_data | JSON | structured extraction output (education, experience, skills, etc.) |
| status | TEXT | `uploaded`, `parsed`, `scored`, `shortlisted`, `rejected`, `hired` |
| source | TEXT | `manual`, `gmail`, `google_form` — how this CV entered the system |
| source_ref | TEXT NULL | dedupe key for automated sources (Outlook/Graph message id, WhatsApp message id, Gmail message id, form row id) — never re-imported twice |
| match_confidence | FLOAT NULL | AI job-match confidence (0–1) when auto-matched; NULL for manual uploads/assignments |
| match_reasoning | TEXT NULL | user-facing match line, e.g. `72% confident this is Sales Executive` (never includes API-key / matcher internals) |
| submitted_at | DATETIME NULL | actual submission time from the source, distinct from `created_at` (ingestion time) |

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

### `whatsapp_inbound_messages`
Pending Meta WhatsApp Cloud API document messages waiting for **Sync CVs** (FEATURE_CV_SCREENING.md §11).
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| wa_message_id | TEXT UNIQUE NOT NULL | Meta message id |
| from_phone | TEXT NULL | sender E.164 |
| media_id | TEXT NOT NULL | Meta media id for download |
| filename | TEXT NULL | |
| mime_type | TEXT NULL | |
| caption | TEXT NULL | used as position hint when present |
| status | TEXT NOT NULL | `pending`, `imported`, `skipped`, `failed` |
| skip_reason | TEXT NULL | classifier / error reason |
| received_at | DATETIME NOT NULL | |
| created_at | DATETIME | |
| updated_at | DATETIME | |

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

### `payroll_sheet_adjustments`
Monthly extras on the Kafi salary sheet (allowance, bonus, loan, advance, payment mode, remarks). Unique per employee per month.
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| employee_id | INTEGER FK → employees.id | |
| period_month | INTEGER | 1–12 |
| period_year | INTEGER | |
| allowance_amount | DECIMAL DEFAULT 0 | |
| bonus_amount | DECIMAL DEFAULT 0 | |
| loan_deduction_amount | DECIMAL DEFAULT 0 | |
| advance_amount | DECIMAL DEFAULT 0 | |
| payment_mode | TEXT NULL | `IBFT`, `Cheque`, or `Cash` (salary sheet dropdown) |
| remarks | TEXT NULL | |
| days_present | INTEGER NULL | salary-sheet override; NULL = use attendance |
| days_absent | INTEGER NULL | unpaid absents override |
| days_late | INTEGER NULL | late count override |
| days_half_day | INTEGER NULL | half-day count override |
| overtime_bonus_days | INTEGER NULL | OT days override |
| monthly_tax_override | DECIMAL NULL | typed tax/other; NULL = slab formula |
| UNIQUE (employee_id, period_month, period_year) | | |

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
Per-department KPI definitions (in-scope item 5). Personal/self-service KPIs set `owner_employee_id`.
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| department_id | INTEGER FK → departments.id | |
| owner_employee_id | INTEGER FK → employees.id NULL | set for personal KPIs; NULL = department-owned |
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

### `employee_monthly_performance`
Finalized monthly Employee Development score (/10) with optional AI summary. Unique on `(employee_id, period_year, period_month)`.
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| employee_id | INTEGER FK → employees.id | |
| period_year | INTEGER | |
| period_month | INTEGER | 1–12 |
| score_out_of_10 | DECIMAL(4,2) | weighted KPI achievement mapped to 0–10 (capped) |
| overall_pct | FLOAT NULL | weighted average of entry scores (%) |
| entries_count | INTEGER | KPI entries counted for the month |
| ai_summary | TEXT NULL | Gemini narrative |
| finalized_at | DATETIME NULL | set when past month is snapshotted |
| created_at | DATETIME | |
| updated_at | DATETIME | |

### `employee_training_assignments`
Courses recommended by AI and assigned to an employee (Things To Learn).
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| employee_id | INTEGER FK → employees.id | |
| title | TEXT NOT NULL | |
| level | TEXT | `intermediate` or `advanced` |
| description | TEXT NOT NULL | |
| provider | TEXT NULL | e.g. Coursera, Udemy |
| url_hint | TEXT NULL | search phrase or URL |
| topic_prompt | TEXT NOT NULL | what HR typed when recommending |
| department_name | TEXT NULL | snapshot at assign time |
| role_title | TEXT NULL | snapshot at assign time |
| status | TEXT | `assigned`, `in_progress`, `completed` |
| assigned_by | INTEGER FK → users.id | |
| assigned_at | DATETIME | |
| completed_at | DATETIME NULL | |
| created_at | DATETIME | |
| updated_at | DATETIME | |

### `employee_resignation_notices`
HR-issued resignation letters. When the employee accepts, the employee is terminated and their login is deactivated.
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| employee_id | INTEGER FK → employees.id | |
| subject | TEXT NOT NULL | |
| letter_body | TEXT NOT NULL | full letter text |
| reason | TEXT NULL | |
| effective_date | DATE NULL | exit date applied on accept |
| status | TEXT | `pending`, `accepted`, `cancelled` |
| issued_by | INTEGER FK → users.id | |
| issued_at | DATETIME | |
| accepted_at | DATETIME NULL | |
| created_at | DATETIME | |
| updated_at | DATETIME | |

### `app_notifications`
In-app reminders (KPI incomplete / at-risk and future kinds). Not an email queue.
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| user_id | INTEGER FK → users.id | recipient (nullable reserved for future broadcast) |
| title | TEXT NOT NULL | |
| body | TEXT NOT NULL | |
| kind | TEXT NOT NULL | e.g. `kpi_incomplete`, `kpi_at_risk` |
| payload | JSON NULL | e.g. `{ department_id, period_start, period_end }` |
| read_at | DATETIME NULL | null = unread |
| created_at | DATETIME | |
| updated_at | DATETIME | |

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
