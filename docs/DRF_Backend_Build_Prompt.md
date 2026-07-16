# MASTER BUILD PROMPT — Smart Medical Specialist Directory API
### Django REST Framework backend · apps-per-service · standard response envelope · SMS notifications · phased build

Paste this entire document to your coding agent as the system/task prompt. Do not skip phases or reorder them — each phase is a checkpoint specifically designed to catch errors before they compound into the next layer.

---

## 0. Project Context (read first)

You are building the backend for a **Smart Medical Specialist Directory System** covering multiple hospitals in Dar es Salaam. Key domain rules that must hold everywhere in the codebase:

1. **Hospital is the account-owning actor.** A hospital registers itself, and a Hospital Admin user manages that hospital's specialists and availability. Specialists do **not** log in and do **not** self-update.
2. **A specialist belongs to exactly one hospital.** Every specialist-scoped write must be restricted to the hospital that owns the specialist — enforce this in a service/permission layer, never trust the client.
3. **Only verified hospitals appear in patient-facing search.** A hospital starts `PENDING`, and only a Super Admin can move it to `VERIFIED` or `SUSPENDED`.
4. **Patients search by location.** Nearby search ranks hospitals/specialists by distance from patient-supplied coordinates.
5. **Notifications go out by SMS** (and optionally email) for appointment confirmation, reminder, and cancellation — sent asynchronously, never inline in the request/response cycle.

---

## 1. Tech Stack (fixed — do not substitute without asking)

| Layer | Choice |
|---|---|
| Framework | Django 5.x + Django REST Framework |
| Language | Python 3.12 |
| Database | PostgreSQL 15+ with PostGIS extension |
| Auth | JWT via `djangorestframework-simplejwt` |
| Async tasks | Celery + Redis (broker + result backend) |
| SMS gateway | Africa's Talking (`africastalking` Python SDK) |
| API docs | `drf-spectacular` (OpenAPI 3) |
| Testing | `pytest` + `pytest-django` + `factory_boy` |
| Timezone | `Africa/Dar_es_Salaam` everywhere; store UTC in DB |

If PostGIS is not available in the target environment, fall back to a Haversine formula computed in a raw SQL `annotate()` — flag this explicitly in your output, do not silently swap it in.

---

## 2. Repository Layout — apps folder, one app per service

All domain services live under a single `apps/` package. **Do not scatter apps at the project root.** Each app follows the same internal shape so the codebase is predictable.

```
backend/
├── manage.py
├── config/
│   ├── settings/
│   │   ├── base.py
│   │   ├── dev.py
│   │   └── prod.py
│   ├── urls.py
│   ├── celery.py
│   └── wsgi.py / asgi.py
├── apps/
│   ├── common/                # shared kernel — build this FIRST
│   │   ├── responses.py       # standard envelope helpers
│   │   ├── exceptions.py      # custom exception handler
│   │   ├── permissions.py     # IsHospitalAdmin, IsOwnHospital, IsSuperAdmin, IsPatient
│   │   ├── pagination.py      # standard pagination class
│   │   ├── models.py          # TimeStampedModel, SoftDeleteModel abstract bases
│   │   └── enums.py           # shared choices/enums
│   │
│   ├── accounts/               # PHASE 1
│   │   ├── domain/             # User role rules, password policy
│   │   ├── services/           # RegisterUserService, AuthService
│   │   ├── api/                # serializers.py, views.py, urls.py
│   │   ├── models.py           # custom User (AbstractUser + role)
│   │   └── tests/
│   │
│   ├── hospitals/               # PHASE 2
│   │   ├── domain/              # Hospital entity rules, Coordinates value object
│   │   ├── services/            # RegisterHospitalService, VerifyHospitalService
│   │   ├── repositories/        # HospitalRepository
│   │   ├── api/
│   │   ├── models.py
│   │   └── tests/
│   │
│   ├── specialists/             # PHASE 3
│   │   ├── domain/
│   │   ├── services/            # ManageSpecialistService (create/edit/soft-delete, hospital-scoped)
│   │   ├── api/
│   │   ├── models.py
│   │   └── tests/
│   │
│   ├── availability/            # PHASE 4
│   │   ├── domain/
│   │   ├── services/            # AvailabilityService, ScheduleTemplateService
│   │   ├── api/
│   │   ├── models.py
│   │   └── tests/
│   │
│   ├── search/                  # PHASE 5
│   │   ├── services/            # GeoSearchService (PostGIS distance query)
│   │   ├── api/
│   │   └── tests/
│   │
│   ├── appointments/            # PHASE 6
│   │   ├── domain/               # reference number generator, state machine
│   │   ├── services/
│   │   ├── api/
│   │   ├── models.py
│   │   └── tests/
│   │
│   ├── notifications/           # PHASE 7
│   │   ├── services/            # SmsService, EmailService, NotificationDispatcher
│   │   ├── tasks.py             # Celery tasks
│   │   ├── models.py            # NotificationLog
│   │   ├── api/                  # (internal/admin only — no public endpoints)
│   │   └── tests/
│   │
│   └── reports/                 # PHASE 8
│       ├── services/
│       ├── api/
│       └── tests/
│
├── requirements/
│   ├── base.txt
│   ├── dev.txt
│   └── prod.txt
└── pytest.ini
```

**Rule:** an app's `api/views.py` should only orchestrate — parse input, call a service, wrap the result in the standard envelope. Business rules (ownership checks, distance ranking, state transitions) live in `services/`, never in the view.

---

## 3. Standard API Response Envelope (build this before anything else)

Every endpoint — success or failure — returns this exact shape. No endpoint returns a bare DRF default response.

```json
{
  "success": true,
  "message": "Specialist created successfully.",
  "data": { "id": 12, "full_name": "Dr. Amina Juma" },
  "errors": null,
  "meta": { "pagination": null }
}
```

Error case:

```json
{
  "success": false,
  "message": "Validation failed.",
  "data": null,
  "errors": { "specialization": ["This field is required."] },
  "meta": null
}
```

### 3.1 `apps/common/responses.py`

```python
from rest_framework.response import Response
from rest_framework import status

def success_response(data=None, message="Success", meta=None, status_code=status.HTTP_200_OK):
    return Response(
        {"success": True, "message": message, "data": data, "errors": None, "meta": meta},
        status=status_code,
    )

def error_response(errors=None, message="Something went wrong.", status_code=status.HTTP_400_BAD_REQUEST):
    return Response(
        {"success": False, "message": message, "data": None, "errors": errors, "meta": None},
        status=status_code,
    )
```

### 3.2 `apps/common/exceptions.py`

Implement a **custom DRF exception handler** (`EXCEPTION_HANDLER` in settings) that catches `ValidationError`, `PermissionDenied`, `NotFound`, `AuthenticationFailed`, and any uncaught `Exception`, and reshapes them into the `error_response` envelope above — so a raised exception anywhere in the stack still returns the standard shape, not DRF's default `{"detail": "..."}`.

### 3.3 Pagination

`apps/common/pagination.py` — a `PageNumberPagination` subclass whose `get_paginated_response()` also returns the standard envelope, with `meta.pagination = {count, next, previous, page_size}`.

**Verification for this section:** write one throwaway view, hit it with a valid and an invalid payload, and confirm both come back in the exact envelope shape before moving to Phase 1.

---

## 4. Build Phases — follow in order, do not skip ahead

For every phase: implement → write tests → run tests → run the manual checklist at the end of that phase → only then start the next phase. If a phase's tests fail, fix them before continuing; do not carry forward a red test suite.

### PHASE 0 — Project Bootstrap
- Initialize Django project (`config/`), split settings (`base/dev/prod`).
- Configure PostgreSQL + PostGIS, `.env` handling (`django-environ`), `TIME_ZONE = "Africa/Dar_es_Salaam"`.
- Install and wire: DRF, SimpleJWT, `drf-spectacular`, Celery + Redis, `django-cors-headers`.
- Build `apps/common/` completely (responses, exceptions, permissions stubs, pagination, abstract `TimeStampedModel` / `SoftDeleteModel`).
- Wire the custom exception handler into `REST_FRAMEWORK["EXCEPTION_HANDLER"]`.
- ✅ Checklist: `python manage.py runserver` boots with no errors; a dummy `/api/health/` endpoint returns the standard envelope; `drf-spectacular` schema page loads.

### PHASE 1 — Accounts & Auth (`apps/accounts`)
- Custom `User` model: `AbstractUser` + `role` (`PATIENT`, `HOSPITAL_ADMIN`, `SUPER_ADMIN`) + `hospital` FK (nullable, only set for `HOSPITAL_ADMIN`).
- Endpoints: `POST /api/auth/register/patient/`, `POST /api/auth/login/`, `POST /api/auth/refresh/`, `GET /api/auth/me/`.
- JWT access + refresh tokens; embed `role` and `hospital_id` in the token payload.
- Implement `apps/common/permissions.py` for real: `IsPatient`, `IsHospitalAdmin`, `IsSuperAdmin`, `IsOwnHospital` (compares `request.user.hospital_id` to the object's `hospital_id`).
- ✅ Checklist: register a patient, log in, call `/me/`, confirm role-based 403s on a protected dummy endpoint for the wrong role.

### PHASE 2 — Hospitals (`apps/hospitals`)
- Model: `Hospital` (name, registration_no, latitude, longitude, address, phone, email, status: `PENDING/VERIFIED/SUSPENDED`, timestamps).
- `RegisterHospitalService`: creates hospital in `PENDING` + creates the first `HOSPITAL_ADMIN` user atomically (use `transaction.atomic`).
- `VerifyHospitalService`: Super-Admin-only status transitions with a valid state machine (`PENDING → VERIFIED`, `VERIFIED → SUSPENDED`, etc. — reject invalid transitions with a clear error).
- Endpoints: `POST /api/hospitals/register/`, `GET/PATCH /api/hospitals/me/` (own hospital), `PATCH /api/hospitals/{id}/verify/` (Super Admin), `GET /api/hospitals/` (Super Admin, paginated).
- ✅ Checklist: register a hospital → confirm it does NOT show in any public list; verify it as Super Admin → confirm it now does; a Hospital Admin cannot PATCH another hospital's profile.

### PHASE 3 — Specialists (`apps/specialists`)
- Model: `Specialist` (hospital FK, full_name, specialization, license_no, photo, is_active, created_by, timestamps) — soft delete via `SoftDeleteModel`.
- `ManageSpecialistService`: every write method takes the acting user and asserts `user.hospital_id == specialist.hospital_id` before proceeding — this check lives once in the service, not repeated per view.
- Endpoints (all `IsHospitalAdmin`): `POST /api/specialists/`, `PATCH /api/specialists/{id}/`, `DELETE /api/specialists/{id}/` (soft delete), `GET /api/specialists/` (own hospital only).
- Public read endpoint: `GET /api/specialists/{id}/` — only returns specialists whose hospital is `VERIFIED` and who are `is_active=True`.
- ✅ Checklist: Hospital A admin cannot see or edit Hospital B's specialists (test both list and detail); soft-deleted specialists disappear from public + owner list but remain in the DB.

### PHASE 4 — Availability (`apps/availability`)
- Model: `AvailabilityStatus` (specialist FK, hospital FK, date, status: `AVAILABLE/BUSY/OFF`, updated_by, `unique_together=(specialist, hospital, date)`).
- `AvailabilityService.set_status(user, specialist_id, date, status)` — hospital-scope check identical pattern to Phase 3.
- `ScheduleTemplateService` — optional recurring weekly template that generates daily `AvailabilityStatus` rows via a Celery beat task (nightly).
- Endpoints: `POST /api/availability/`, `GET /api/availability/?specialist_id=&date_from=&date_to=` (own hospital), `POST /api/availability/schedule-template/`.
- ✅ Checklist: setting availability twice for the same (specialist, date) updates rather than duplicates; a second hospital cannot set availability for a specialist it doesn't own.

### PHASE 5 — Nearby Search (`apps/search`)
- `GeoSearchService.nearby(lat, lng, specialization=None, radius_km=None, status=None)`:
  - Filters to `Hospital.status == VERIFIED` and `Specialist.is_active == True`.
  - Uses PostGIS `ST_DistanceSphere` (or `django.contrib.gis.db.models.functions.Distance` with a `PointField`) annotated and ordered by distance.
  - Returns hospital name, distance_km, specialist summary, current availability for **today's date**.
- Endpoint: `GET /api/search/nearby/?lat=&lng=&specialization=&radius=&status=` — public, paginated, rate-limited (DRF throttle class) to prevent scraping.
- Fire-and-forget: on each call, enqueue a Celery task to write a `NearbySearchLog` row (`apps/search` or reuse `apps/reports`) — never block the response on this write.
- ✅ Checklist: seed 3 hospitals at known coordinates, confirm ordering matches expected distance; confirm a `PENDING` hospital never appears; confirm the log write doesn't add latency (check via task queue, not inline).

### PHASE 6 — Appointments (`apps/appointments`)
- Model: `Appointment` (patient FK, specialist FK, hospital FK, reference `APT-YYYY-NNNNN` auto-generated, status: `REQUESTED/CONFIRMED/CANCELLED/COMPLETED`, scheduled_at, timestamps).
- Reference generator: per-year atomic counter (avoid race conditions — use `select_for_update()` or a DB sequence, not `Model.objects.count()`).
- State machine service enforcing valid transitions only (`REQUESTED → CONFIRMED/CANCELLED`, `CONFIRMED → COMPLETED/CANCELLED`).
- On create/confirm/cancel: call into `apps/notifications` (Phase 7) via its public service interface — **do not** import notification internals directly from views.
- Endpoints: `POST /api/appointments/`, `GET /api/appointments/mine/` (patient), `GET /api/appointments/?hospital=` (hospital admin), `PATCH /api/appointments/{id}/status/`.
- ✅ Checklist: two concurrent booking requests never produce a duplicate reference number (write a test that fires them concurrently or asserts the locking mechanism); invalid transitions are rejected with a clear message.

### PHASE 7 — Notifications / SMS (`apps/notifications`)
- Integrate **Africa's Talking** SMS SDK. Store credentials via env vars: `AT_USERNAME`, `AT_API_KEY`, `AT_SENDER_ID` (never hardcode).
- `SmsService.send(phone_number, message)` — thin wrapper around the SDK call, raises a typed `SmsDeliveryError` on failure.
- `NotificationDispatcher` — public interface other apps call (e.g. `dispatcher.appointment_confirmed(appointment)`), which builds the message text and enqueues a Celery task.
- Celery task `send_sms_task(phone_number, message, notification_log_id)`:
  - Retries with exponential backoff (max 3 attempts) on transient failure.
  - Updates a `NotificationLog` row (`recipient, channel, message, status: PENDING/SENT/FAILED, provider_response, sent_at`) — this is your audit trail and debugging surface.
- Trigger points: appointment `CONFIRMED` → confirmation SMS; a scheduled reminder ~24h before `scheduled_at` (Celery beat); appointment `CANCELLED` → cancellation SMS.
- Phone number normalization: validate/format to `+255XXXXXXXXX` before sending; reject and log rather than silently failing on a malformed number.
- ✅ Checklist: mock the Africa's Talking client in tests (do not hit the real API in CI); confirm a `NotificationLog` row is created for every send attempt, success or failure; confirm a forced SDK failure retries then lands in `FAILED` with the provider error captured.

### PHASE 8 — Reports (`apps/reports`) — Super Admin only
- Endpoints: `GET /api/reports/overview/` (hospital counts by status, specialist counts, search volume, top specializations), `GET /api/reports/searches/` (from `NearbySearchLog`).
- Keep all aggregation in `services/`, using `annotate`/`aggregate` — no N+1 queries in a loop.
- ✅ Checklist: run `django-debug-toolbar` or `nplusone` locally on the report endpoints and confirm no N+1 warnings.

### PHASE 9 — Hardening & Docs (final phase)
- Full `pytest` run across all apps, target meaningful coverage on `services/` (business logic), not just views.
- `drf-spectacular` schema fully annotated (tags per app, example responses using the standard envelope).
- Rate limiting / throttling on public endpoints (`search`, `register`).
- Structured logging (JSON) for request/response and Celery task outcomes.
- `.env.example` documenting every required variable (DB, Redis, JWT secrets, Africa's Talking creds, Maps API key).
- ✅ Checklist: fresh clone + `.env.example` → app boots, migrates, and passes the full test suite with zero manual fixes.

---

## 5. Cross-Cutting Rules (apply in every phase)

1. **Every response uses the standard envelope** — no exceptions, no "just this once" bare DRF response.
2. **Ownership/RBAC checks live in `services/` or `permissions.py`, never duplicated inline in a view.**
3. **No business logic in serializers beyond field-level validation.** Cross-field or cross-model rules belong in a service.
4. **All money/none here, but all dates/times are timezone-aware**, stored UTC, rendered in `Africa/Dar_es_Salaam` where shown to the user.
5. **Every external call (SMS, geocoding) goes through a service wrapper**, never called directly from a view or another app's internals.
6. **Migrations are reviewed, not just auto-generated** — check for accidental nullable/default surprises before committing.
7. **Write tests alongside the phase, not after.** A phase is not "done" until its checklist and its tests both pass.

---

## 6. What to Report Back After Each Phase

At the end of every phase, output:
- Files created/changed
- Endpoints added (method, path, required role)
- Test results (pass/fail count)
- Any deviation from this prompt and why
- Explicit confirmation the phase checklist passed before you move on

Do not begin the next phase in the same turn without this summary — it's the checkpoint that keeps errors from compounding across phases.
