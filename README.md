# Exam Duties Allocation System

A web application that assigns teachers and staff to exam invigilation duties for an existing examination schedule.
The coordinator enters staff availability, duty limits, exam sessions and rooms; the system generates allocations,
shows unfilled duties and validates replacements before publishing.

**Course:** Software Construction (SEN-311), Bahria University Karachi Campus, Fall 2026

## Tech Stack
- Python 3 and Django
- PostgreSQL
- HTML, CSS, JavaScript with Bootstrap 5
- Django Channels (WebSockets) for notifications
- Docker and GitHub Actions (to be added)

## Folder Structure
```
config/          Django project settings and root URLs
accounts/        Custom user model and login (role: coordinator / staff)
roster/          Roster app
  services/      Business logic (rules.py, allocation.py)
  tests/         Tests
templates/       HTML templates (base.html, home.html)
```

## Setup
1. Clone the repository and open the folder.
2. Create and activate a virtual environment:
   - Windows: `python -m venv .venv` then `.venv\Scripts\activate`
   - Mac/Linux: `python3 -m venv .venv` then `source .venv/bin/activate`
3. Install packages: `pip install -r requirements.txt`
4. Copy `.env.example` to `.env` and set your PostgreSQL password.
5. Create a PostgreSQL database named `exam_duties`.
6. Run migrations: `python manage.py migrate`
7. Start the server: `python manage.py runserver`
8. Run tests: `pytest`

## Team
- Kanwal Bibi (Team Leader)
- Aamnah Attariah
- Iffat Batool
