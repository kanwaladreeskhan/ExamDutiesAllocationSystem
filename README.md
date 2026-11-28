# Exam Duties Allocation System

A web application that assigns teachers and staff to exam invigilation duties for an existing examination schedule.
The coordinator enters staff availability, duty limits, exam sessions and rooms; the system generates allocations,
shows unfilled duties and validates replacements before publishing.

**Course:** Software Construction (SEN-311), Bahria University Karachi Campus, Fall 2026

## Tech Stack
- Python 3.12 and Django
- PostgreSQL 16 (runs in Docker)
- Redis (channel layer for notifications)
- HTML, CSS, JavaScript with Bootstrap 5
- Django Channels (WebSockets) for notifications
- Docker, Docker Compose and GitHub Actions
- pytest and pytest-django for testing

## Folder Structure
```
config/          Django project settings and root URLs
accounts/        Custom user model, login, role permissions (mixins, decorators)
roster/          Roster app
  models.py      Database tables (staff, availability, rooms, sessions, rosters, assignments)
  forms.py       Forms with validation
  data_views.py  Coordinator data management screens (CRUD) and replacement
  data_urls.py   URLs under /manage/
  services/      Business logic (rules.py, allocation.py, adapters.py)
  management/    seed_data command
  tests/         Tests
templates/       HTML templates (login, coordinator, staff)
```

## Setup (Docker)

Requirements: Git and Docker Desktop (Engine running).

1. Clone the repository and open the folder:
   ```
   git clone <repository-url>
   cd ExamDutiesAllocationSystem
   ```
2. Build and start everything (PostgreSQL, Redis, web). Migrations run automatically:
   ```
   docker compose up --build
   ```
3. In a second terminal, load the demo data (safe to run more than once):
   ```
   docker compose exec web python manage.py seed_data
   ```
4. Open http://localhost:8000/accounts/login/ in the browser.
   (Use `localhost`, not `0.0.0.0`.)

To stop: `Ctrl+C`, then `docker compose down`.
Do **not** use `docker compose down -v`, it deletes the database volume.

## Login Credentials (demo data)

| Role | Username | Password |
|---|---|---|
| Examination Coordinator | `coordinator` | `Coord@12345` |
| Staff Member | `ali.khan` | `Staff@12345` |

Other staff (same password `Staff@12345`): `sara.ahmed`, `bilal.raza`, `hina.malik`,
`usman.tariq`, `zara.noor`, `fahad.iqbal`, `maria.shah`.

To create an admin account for `/admin/`:
```
docker compose exec web python manage.py createsuperuser
```
Then set its Role to "Examination Coordinator" in the admin if it should use coordinator pages.

## Main Pages (coordinator login required)

| Page | URL |
|---|---|
| Coordinator dashboard | `/coordinator/` |
| Staff and duty limits | `/manage/staff/` |
| Staff availability | `/manage/availability/` |
| Rooms | `/manage/rooms/` |
| Exam sessions and required invigilators | `/manage/sessions/` |
| Assignments and replacement | `/manage/assignments/` |

Staff members see their own duties at `/`.

## Business Rules Enforced
- BR-01: no overlapping duties
- BR-02: unavailable staff are not assigned
- BR-03: each staff member's maximum duty limit is respected
- BR-05: manual replacements use the same rules as automatic allocation (`roster/services/rules.py`)

## Database
PostgreSQL runs in the `db` container (database `exam_duty_db`, user `exam_admin`).
Data is stored in the Docker volume `postgres_data`. Passwords are stored hashed (PBKDF2).

Inspect tables:
```
docker compose exec db psql -U exam_admin -d exam_duty_db -c "\dt"
```

## Running Tests
With the containers running:
```
docker compose exec web python -m pytest -q
```
pytest creates a temporary test database, your real data is not touched.

## Team
- Kanwal Bibi (Team Leader): allocation algorithm, business rules, tests
- Aamnah Attariah: database, authentication, data management, replacement, Docker setup
- Iffat Batool: front end, rosters, notifications, CI