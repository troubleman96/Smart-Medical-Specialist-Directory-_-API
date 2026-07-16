# Kindamba API — Smart Medical Specialist Directory

Django REST Framework backend for a multi-hospital medical specialist directory covering Dar es Salaam. Hospitals register and manage their own specialists and availability; patients search nearby specialists by location and book appointments; a Super Admin verifies hospitals and views platform reports.

Companion frontend: [`kindamba-ui`](../kindamba-ui) (TanStack Start + React).

## Domain model (read this first)

- **Hospital is the account-owning actor.** A hospital registers itself; a Hospital Admin user manages that hospital's specialists and availability. Specialists do not log in and do not self-update.
- **A specialist belongs to exactly one hospital.** Every specialist-scoped write is restricted to the owning hospital.
- **Only verified hospitals appear in patient-facing search.** A hospital starts `PENDING` and only a Super Admin can move it to `VERIFIED` or `SUSPENDED`.
- **Patients search by location** — nearby search ranks results by distance from patient-supplied coordinates.
- **Notifications go out by SMS** (via SendAfrica) for appointment confirmation/reminder/cancellation, sent asynchronously through Celery — never inline in the request/response cycle.

Roles (`apps/common/models.py: User.Role`): `PATIENT`, `HOSPITAL_ADMIN`, `SUPER_ADMIN`.

See [`docs/DRF_Backend_Build_Prompt.md`](docs/DRF_Backend_Build_Prompt.md) for the full original build spec and [`docs/Smart_Medical_Directory_SRS.docx`](docs/Smart_Medical_Directory_SRS.docx) for the requirements document.

## Tech stack

| Layer | Choice |
|---|---|
| Framework | Django 5.x + Django REST Framework |
| Auth | JWT (`djangorestframework-simplejwt`) |
| Database | PostgreSQL (SQLite fallback for local dev) |
| Async tasks | Celery + Redis |
| SMS gateway | SendAfrica |
| API docs | drf-spectacular (OpenAPI 3 / Swagger) |
| Testing | pytest + pytest-django + factory_boy |
| Timezone | `Africa/Dar_es_Salaam` |

## Project layout

```
backend/
├── manage.py
├── config/
│   ├── settings/{base,dev,prod}.py
│   ├── urls.py
│   └── celery.py
├── apps/
│   ├── common/          # User model, response envelope, permissions, pagination, enums
│   ├── accounts/        # registration, login, /me
│   ├── hospitals/       # hospital registration, verification, listing
│   ├── specialists/     # specialist CRUD (hospital-scoped) + public detail
│   ├── availability/    # daily availability + schedule templates
│   ├── search/          # nearby search
│   ├── appointments/    # booking + status updates
│   ├── notifications/   # SMS/email dispatch (Celery tasks, no public API)
│   └── reports/         # admin overview + search reports
└── requirements/{base,dev,prod}.txt
```

## Getting started

### Prerequisites

- Python 3.12
- PostgreSQL (optional locally — defaults to SQLite if `DATABASE_URL` is unset)
- Redis (for Celery; optional if you're not touching notifications)

### Setup

```bash
cd Kindamba
python3 -m venv venv
source venv/bin/activate            # Windows: venv\Scripts\activate

cd backend
pip install -r requirements/dev.txt

cp .env.example .env                # then fill in real values
```

`.env` variables:

| Variable | Purpose | Local default |
|---|---|---|
| `DJANGO_SECRET_KEY` | Django secret key | insecure dev key |
| `DJANGO_DEBUG` | Debug mode | `False` (set `True` locally) |
| `DJANGO_ALLOWED_HOSTS` | Allowed hosts | `*` in dev |
| `DATABASE_URL` | DB connection string | `sqlite:///db.sqlite3` if unset |
| `CELERY_BROKER_URL` / `CELERY_RESULT_BACKEND` | Redis URLs | `redis://localhost:6379/0` |
| `SENDAFRICA_API_KEY` / `SENDAFRICA_BASE_URL` | SMS gateway | — |

### Run migrations and start the server

```bash
python manage.py migrate
python manage.py createsuperuser     # optional, for /admin/
python manage.py runserver           # http://localhost:8000
```

The dev server uses `config.settings.dev` by default (set in `manage.py`). For production, run with `DJANGO_SETTINGS_MODULE=config.settings.prod` behind gunicorn:

```bash
gunicorn config.wsgi:application --bind 0.0.0.0:8000
```

### Run the Celery worker (for SMS notifications)

```bash
celery -A config worker -l info
```

### Run tests

```bash
pytest
```

Configured via [`pytest.ini`](backend/pytest.ini) to use `config.settings.dev` and discover `tests.py` / `test_*.py` / `*_tests.py`.

## API overview

Base path: `/api/`. All authenticated endpoints use `Authorization: Bearer <access_token>`.

Every response follows a standard envelope (`apps/common/responses.py`):

```json
{
  "success": true,
  "message": "Success",
  "data": { "...": "..." },
  "errors": null,
  "meta": { "pagination": { "count": 0, "next": null, "previous": null, "page_size": 25 } }
}
```

| Area | Endpoint | Notes |
|---|---|---|
| Health | `GET /api/health/` | Liveness check |
| Auth | `POST /api/auth/register/patient/` | Patient self-registration |
| Auth | `POST /api/auth/login/` | Returns JWT access + refresh |
| Auth | `POST /api/auth/refresh/` | Refresh access token |
| Auth | `GET /api/auth/me/` | Current user profile |
| Hospitals | `POST /api/hospitals/register/` | Hospital self-registration (starts `PENDING`) |
| Hospitals | `GET /api/hospitals/me/` | Own hospital (Hospital Admin) |
| Hospitals | `POST /api/hospitals/<id>/verify/` | Super Admin: verify/suspend |
| Hospitals | `GET /api/hospitals/` | List hospitals |
| Specialists | `POST /api/specialists/` | Create (Hospital Admin, own hospital) |
| Specialists | `PATCH /api/specialists/<id>/` | Update |
| Specialists | `DELETE /api/specialists/<id>/delete/` | Delete |
| Specialists | `GET /api/specialists/mine/` | List own hospital's specialists |
| Specialists | `GET /api/specialists/public/<id>/` | Public detail (patient-facing) |
| Availability | `POST /api/availability/` | Set availability |
| Availability | `GET /api/availability/list/` | List availability |
| Availability | `POST /api/availability/schedule-template/` | Recurring schedule template |
| Search | `GET /api/search/nearby/` | Nearby specialists/hospitals by lat/lng |
| Appointments | `POST /api/appointments/` | Book (Patient) |
| Appointments | `GET /api/appointments/mine/` | Patient's own appointments |
| Appointments | `GET /api/appointments/hospital/` | Hospital's appointments |
| Appointments | `PATCH /api/appointments/<id>/status/` | Update status (confirm/cancel/complete) |
| Reports | `GET /api/reports/overview/` | Super Admin dashboard stats |
| Reports | `GET /api/reports/searches/` | Search analytics |
| Docs | `GET /api/docs/` | Swagger UI |
| Docs | `GET /api/schema/` | Raw OpenAPI schema |

For exact request/response shapes, run the server and open `http://localhost:8000/api/docs/`.

## Deployment / pushing changes

This repo is separate from the frontend (`kindamba-ui`) and has its own git history and remote — commit and push it independently:

```bash
git status
git add <files>
git commit -m "..."
git push origin master
```

For production, set `DJANGO_SETTINGS_MODULE=config.settings.prod`, provide a real `DATABASE_URL` (PostgreSQL), set `DJANGO_ALLOWED_HOSTS` and `CORS_ALLOWED_ORIGINS`, and serve behind gunicorn with a reverse proxy. Run `python manage.py collectstatic` before deploying.
