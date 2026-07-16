# Kindamba API — Smart Medical Specialist Directory

Django REST Framework backend for a multi-hospital medical specialist directory covering Dar es Salaam. Hospitals register and manage their own specialists and availability; patients search nearby specialists by location and book appointments; a Super Admin verifies hospitals and views platform reports.

Companion frontend: [`kindamba-ui`](../kindamba-ui) (TanStack Start + React) — see its README for how the client consumes everything documented here.

## Table of contents

- [Domain model](#domain-model-read-this-first)
- [Tech stack](#tech-stack)
- [Project layout](#project-layout)
- [Getting started](#getting-started)
- [Authentication & authorization](#authentication--authorization)
- [Response envelope & errors](#response-envelope--errors)
- [API reference](#api-reference) — every endpoint, request/response shapes, side effects
- [Data models](#data-models)
- [SMS notifications reference](#sms-notifications-reference)
- [Pagination & throttling](#pagination--throttling)
- [Testing](#testing)
- [Pushing changes (git, explained simply)](#pushing-changes-git-explained-simply)
- [Deployment (production)](#deployment-production)

## Domain model (read this first)

- **Hospital is the account-owning actor.** A hospital registers itself; a Hospital Admin user manages that hospital's specialists and availability. Specialists do not log in and do not self-update.
- **A specialist belongs to exactly one hospital.** Every specialist-scoped write is restricted to the hospital that owns the specialist — enforced in the service layer, never trusted from client input.
- **Only verified hospitals appear in patient-facing search.** A hospital starts `PENDING`; only a Super Admin can move it to `VERIFIED` or `SUSPENDED`.
- **Patients search by location.** Nearby search ranks hospitals by straight-line (haversine) distance from patient-supplied coordinates.
- **Accounts are identified by phone number, not username/email.** Login and registration use `phone_number` + password. A new account gets a 6-digit SMS OTP to verify the number; `username`/`email` are optional, cosmetic fields.
- **Notifications go out by SMS** (via SendAfrica) for OTP verification, appointment lifecycle events, and hospital approval — sent asynchronously through Celery, never inline in the request/response cycle.

Roles (`apps/common/models.py: User.Role`): `PATIENT`, `HOSPITAL_ADMIN`, `SUPER_ADMIN`. There is no self-registration endpoint for `SUPER_ADMIN` — that role is created manually (Django admin or `manage.py shell`).

See [`docs/DRF_Backend_Build_Prompt.md`](docs/DRF_Backend_Build_Prompt.md) for the full original build spec and [`docs/Smart_Medical_Directory_SRS.docx`](docs/Smart_Medical_Directory_SRS.docx) for the requirements document.

## Tech stack

| Layer | Choice |
|---|---|
| Framework | Django 5.x (running on Django 6 in this environment) + Django REST Framework |
| Auth | JWT (`djangorestframework-simplejwt`) |
| Database | PostgreSQL in prod; SQLite fallback for local dev (`db.sqlite3`) |
| Async tasks | Celery + Redis (broker and result backend) |
| SMS gateway | SendAfrica (`SENDAFRICA_API_KEY` / `SENDAFRICA_BASE_URL`) |
| API docs | drf-spectacular (OpenAPI 3 / Swagger UI) |
| Testing | pytest + pytest-django + factory_boy |
| Timezone | `Africa/Dar_es_Salaam` (Django `TIME_ZONE`; DB stores UTC via `USE_TZ=True`) |

## Project layout

```
backend/
├── manage.py                    # DJANGO_SETTINGS_MODULE defaults to config.settings.dev
├── config/
│   ├── settings/{base,dev,prod}.py
│   ├── urls.py                  # all route mounting happens here
│   ├── celery.py / celery_app.py
│   ├── wsgi.py / asgi.py
├── apps/
│   ├── common/          # User model, response envelope, permissions, pagination, enums, exception handler
│   ├── accounts/        # registration, login, /me, OTP verify/resend (apps.accounts.models.PhoneOTP)
│   ├── hospitals/       # hospital registration, verification, listing
│   ├── specialists/     # specialist CRUD (hospital-scoped) + public detail
│   ├── availability/    # daily availability + weekly schedule templates
│   ├── search/          # nearby search (haversine distance) + search logging
│   ├── appointments/    # booking + status transitions + reference number generation
│   ├── notifications/   # SmsService (SendAfrica client) + NotificationDispatcher + Celery task (no public API)
│   └── reports/         # admin overview + search analytics (read-only, Super Admin)
└── requirements/{base,dev,prod}.txt
```

Each domain app (other than `notifications`) generally follows: `models.py` → `serializers.py` → `services.py` (business logic, the only place that touches models for writes) → `views.py` (thin — validates via serializer, calls a service, wraps the result in `success_response`/`error_response`) → `urls.py`.

## Getting started

### Prerequisites

- Python 3.12
- PostgreSQL (optional locally — defaults to SQLite if `DATABASE_URL` is unset)
- Redis (for Celery; the app runs without it, but every SMS silently no-ops if the broker isn't reachable)

### Setup — Windows, step by step (no programming experience needed)

This walks through everything from "empty Windows machine" to "server running," typing each command exactly as shown into **PowerShell** (search "PowerShell" in the Start menu, click to open — you don't need to run it as Administrator).

**1. Install Python.**
Go to [python.org/downloads](https://www.python.org/downloads/) and download the latest Python 3.12.x installer. Run it. **On the very first install screen, tick the checkbox "Add python.exe to PATH" at the bottom before clicking Install** — this is the single most common thing people forget, and without it Windows won't know what `python` means when you type it. If you already installed Python without ticking that box, re-run the installer and choose "Modify" → make sure "Add to PATH" is on.

Confirm it worked — close and reopen PowerShell, then run:
```powershell
python --version
```
It should print something like `Python 3.12.x`. If you instead get "python is not recognized," the PATH step above didn't take — reinstall and tick the box.

**2. Get the project folder onto your machine.**
If you were given the project as a `.zip` file, right-click it → "Extract All..." and pick a simple location like `C:\Kindamba`. If you're using Git, install it from [git-scm.com](https://git-scm.com/download/win) (defaults are fine) and run `git clone <repo-url>` from PowerShell.

**3. Move into the folder.**
```powershell
cd C:\Kindamba          # adjust this path to wherever you extracted/cloned it
```

**4. Create a virtual environment.**
This is a private, isolated copy of Python just for this project, so it doesn't clash with anything else on your machine.
```powershell
python -m venv venv
```
This creates a `venv` folder — you'll see it appear in File Explorer. You only do this step once.

**5. Activate the virtual environment.**
You need to do this **every time** you open a new PowerShell window to work on this project:
```powershell
venv\Scripts\Activate.ps1
```
Your prompt should now start with `(venv)`. If instead you see a red error like *"running scripts is disabled on this system"* — this is Windows' default security setting blocking the activation script, not a real problem. Fix it once, in the same PowerShell window, by running:
```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```
Type `Y` and press Enter if it asks for confirmation, then retry `venv\Scripts\Activate.ps1`.

**6. Move into the `backend` folder and install the project's dependencies.**
```powershell
cd backend
pip install -r requirements\dev.txt
```
This downloads everything the project needs (Django, etc.) — it can take a minute or two and will print a lot of text; that's normal.

**7. Create your `.env` file.**
This is the private configuration file with settings and secrets. See the dedicated **[Setting up your `.env` file](#setting-up-your-env-file-explained-simply)** section below for a full, plain-English walkthrough — come back here once it's created.

**8. Set up the database and start the server.**
```powershell
python manage.py migrate
python manage.py runserver
```
Leave this window open — this *is* the server running. You should see `Starting development server at http://127.0.0.1:8000/`.

**9. Confirm it's working.**
Open a web browser and go to `http://localhost:8000/api/health/`. You should see:
```json
{"success":true,"message":"Service is healthy.","data":{"status":"healthy"},"errors":null,"meta":null}
```
That means the API is up. To stop the server later, click into that PowerShell window and press `Ctrl+C`.

Next time you want to run it again, you only need steps 3, 5, and 8 (no need to recreate the virtual environment or reinstall dependencies).

### Setup — macOS / Linux

```bash
cd Kindamba
python3 -m venv venv
source venv/bin/activate

cd backend
pip install -r requirements/dev.txt

cp .env.example .env                # then see the .env section below and fill in real values

python manage.py migrate
python manage.py runserver           # http://localhost:8000
```

### Setting up your `.env` file (explained simply)

A `.env` file holds settings and secret keys that are specific to your machine and should **never** be committed to git or shared publicly (it's already listed in `.gitignore`, so git will ignore it automatically). The project ships a `.env.example` template with placeholder values — you copy it to a real `.env` file and fill in the parts that matter.

**Creating the file on Windows** (a common trap: Notepad likes to save files as `something.env.txt`, which Django won't recognize):

1. In PowerShell, inside the `backend` folder, run:
   ```powershell
   Copy-Item .env.example .env
   ```
   This makes a real copy named exactly `.env`, sidestepping the Notepad trap entirely.
2. To edit it, right-click `.env` in File Explorer → "Open with" → Notepad (if `.env` doesn't show up in File Explorer, turn on "Show hidden files" in the View menu — dotfiles are hidden by default on Windows).

On macOS/Linux, the same idea:
```bash
cp .env.example .env
nano .env        # or: open .env in any text editor
```

**What to put in it.** For running locally on your own machine (not a real deployment), this is a good starting `.env` — copy this in, replacing only the `DJANGO_SECRET_KEY` value (explained below):

```env
# Django
DJANGO_SECRET_KEY=paste-a-random-string-here-see-below
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1

# Database — leave this out entirely for local dev; it falls back to a local
# SQLite file (db.sqlite3) automatically, which is the easiest option and
# needs no separate database software installed.
# DATABASE_URL=postgres://user:password@localhost:5432/kindamba_db

# Redis / Celery — only needed if you're running the Celery worker for SMS.
# These are the standard defaults for a locally installed Redis; leave as-is.
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# SendAfrica SMS — leave blank if you don't have a key yet (see below).
SENDAFRICA_API_KEY=
SENDAFRICA_BASE_URL=https://api.sendafrica.online
```

**Field by field, in plain English:**

| Variable | What it means | What to do |
|---|---|---|
| `DJANGO_SECRET_KEY` | A random secret Django uses internally to sign sessions/tokens securely. It's not a password you need to remember — just a long random string. | **Must change from the placeholder.** Easiest way: with your virtual environment activated, run `python -c "import secrets; print(secrets.token_urlsafe(50))"` and paste the output in as the value. |
| `DJANGO_DEBUG` | Whether Django shows detailed error pages (helpful while developing) or hides them (required for anything real people will use). | `True` while testing locally on your own machine. **Always `False` for a real/public deployment** — leaving debug mode on in production leaks internal details to anyone who hits an error. |
| `DJANGO_ALLOWED_HOSTS` | Which hostnames are allowed to reach this server — a security guard against fake "Host" headers. | `localhost,127.0.0.1` for local use. If deploying to a real domain, set it to that domain instead. |
| `DATABASE_URL` | Where the app stores its data (hospitals, users, appointments, ...). | Leave this line out (or commented out, as above) to use a simple local file (`db.sqlite3`) — nothing extra to install. Only set this if you've installed PostgreSQL and want to use it instead. |
| `CELERY_BROKER_URL` / `CELERY_RESULT_BACKEND` | Address of Redis, used to queue and track background SMS-sending jobs. | Leave as the default shown above **if** you have Redis installed and running locally. If you don't, that's fine — the app still runs, it just can't send SMS (see below). |
| `SENDAFRICA_API_KEY` | Your secret key for the SendAfrica SMS service, so the app can actually send text messages (OTP codes, booking confirmations, etc.). | Leave blank if you don't have one yet — the rest of the app works fine; any SMS just gets logged as failed instead of sent (nothing crashes). Fill in a real key (from whoever manages the SendAfrica account) once you want real SMS to go out. |
| `SENDAFRICA_BASE_URL` | The web address of the SendAfrica service itself. | Leave as the default shown above — there's no reason to change this. |

You don't need Redis or a SendAfrica key just to get the server running and explore the API — they only matter once you're testing the SMS/notification features specifically.

### Run migrations and start the server

```bash
python manage.py migrate
python manage.py createsuperuser     # optional, for /admin/ — note: Django's own createsuperuser flow doesn't set role/phone_number; set those via shell afterward if you need a working SUPER_ADMIN for the API (not just /admin/)
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

There is **no Celery Beat schedule configured** in this project — nothing runs periodically. `NotificationDispatcher.appointment_reminder(...)` exists in the code but nothing currently calls it; it's available for a future beat task or manual trigger, not wired to anything today.

### Run tests

```bash
pytest
```

Configured via [`pytest.ini`](backend/pytest.ini) to use `config.settings.dev` and discover `tests.py` / `test_*.py` / `*_tests.py`. Tests run against pytest-django's own ephemeral test database, so they never reach your real `db.sqlite3` or trigger real SMS sends even if a Celery worker is running against the dev broker (a task enqueued from a test references a `NotificationLog` id that doesn't exist outside the test transaction, so the worker just no-ops on `DoesNotExist`).

## Authentication & authorization

### Identity: phone number, not username

Every account is identified by `phone_number`, not `username` or `email`. `phone_number` is a **unique** field on `User` (`apps/common/models.py`), normalized to `+255XXXXXXXXX` format before being stored or looked up (see `SmsService.normalize_phone` in `apps/notifications/services.py`, reused by `apps/accounts/services.py`).

Accepted input formats, all normalized to the same canonical value:

| Input | Normalized |
|---|---|
| `0712345678` | `+255712345678` |
| `255712345678` | `+255712345678` |
| `+255712345678` | `+255712345678` |
| `071-234-5678` / `071 234 5678` | `+255712345678` |

The local number must be 9 digits starting with `6` or `7` after the country code (covers all current Tanzania mobile carriers, not a hardcoded per-carrier prefix list). Anything else raises a 400 with `"Enter a valid Tanzania phone number (e.g. 0712345678)."`.

`username` still exists on the model (Django's `AbstractUser` requires it, unique) but is **optional in every registration payload** — if omitted, it's auto-derived from the phone number (`+255712345678` → `255712345678`). `email` is also optional everywhere and unused for login.

### JWT tokens

`POST /api/auth/login/` and `POST /api/auth/register/patient/` both return an access/refresh pair (`rest_framework_simplejwt`):

| Token | Lifetime | Notes |
|---|---|---|
| `access` | 60 minutes | Sent as `Authorization: Bearer <access>`. Carries custom claims `role` and (if applicable) `hospital_id`. |
| `refresh` | 7 days | `ROTATE_REFRESH_TOKENS = True` — a successful refresh issues a new access token; `BLACKLIST_AFTER_ROTATION = False` (old refresh tokens are **not** invalidated on rotation — there's no blacklist app installed). |

Refreshing: `POST /api/auth/refresh/` — **this is the one endpoint that does not use the standard response envelope.** It's DRF-simplejwt's stock `TokenRefreshView` mounted directly, so a successful call returns the raw body `{"access": "...", "refresh": "..."}`, not `{"success": true, "data": {...}}`. A failed/expired refresh token *does* go through the shared exception handler and comes back enveloped as an error. Client code must special-case this endpoint — see `kindamba-ui/src/lib/api-client.ts`'s `refreshAccessToken()`.

### Phone verification (OTP)

Registering a patient or a hospital admin creates the account and issues tokens immediately (the account is usable right away) **and** fires a 6-digit SMS OTP in the background (`apps.accounts.models.PhoneOTP`, 10-minute expiry). The account is **not blocked** from making authenticated requests before verifying — `phone_verified` is informational, surfaced on `/api/auth/me/` and enforced only by the frontend's routing (redirects to a verification screen). There is no server-side permission class gating on `phone_verified` today.

- `POST /api/auth/verify-otp/` — `{code}` → marks `phone_verified = True` on success.
- `POST /api/auth/resend-otp/` — issues a new code (old unconsumed codes are simply superseded; verifying against any *unconsumed, unexpired* code that matches succeeds, most-recent-first).

If SMS sending fails at registration time (bad/missing `SENDAFRICA_API_KEY`, network error, etc.), registration itself still succeeds — the OTP send is wrapped in a try/except in the view so a downstream SMS failure never blocks account creation.

### Permission classes (`apps/common/permissions.py`)

| Class | Grants access when |
|---|---|
| `IsPatient` | `request.user.role == 'PATIENT'` |
| `IsHospitalAdmin` | `request.user.role == 'HOSPITAL_ADMIN'` |
| `IsSuperAdmin` | `request.user.role == 'SUPER_ADMIN'` |
| `IsOwnHospital` | object-level check: `request.user.hospital_id == obj.hospital_id` (defined but not currently applied by any view — hospital-scoping is instead enforced inside each service method, e.g. `ManageSpecialistService._get_hospital_specialist` filters by `hospital=user.hospital`) |

Global default (`REST_FRAMEWORK.DEFAULT_PERMISSION_CLASSES`) is `IsAuthenticated` — every endpoint requires a valid access token **unless** its view explicitly sets `permission_classes = [AllowAny]`.

## Response envelope & errors

Every endpoint except `/api/auth/refresh/` (see above) returns this shape (`apps/common/responses.py`):

```json
{
  "success": true,
  "message": "Human-readable summary",
  "data": { "...": "..." },
  "errors": null,
  "meta": null
}
```

On failure, `success: false`, `data: null`, and `errors` holds a dict (usually `{"detail": "..."}` for service-layer `ValueError`s, or a field-keyed dict of message lists for serializer validation errors). All exceptions are normalized by a single global handler (`apps/common/exceptions.py: custom_exception_handler`, wired via `REST_FRAMEWORK.EXCEPTION_HANDLER`):

| Exception | HTTP status | `message` |
|---|---|---|
| `ValidationError` (serializer `is_valid(raise_exception=True)`) | 400 | `"Validation failed."` |
| `PermissionDenied` (role mismatch, wrong permission class) | 403 | `"Permission denied."` |
| `NotFound` | 404 | `"Not found."` |
| `AuthenticationFailed` / expired or missing JWT | 401 | `"Authentication failed."` |
| `Throttled` (rate limit) | 429 | `"Rate limit exceeded."` — `errors.detail` includes the wait time |
| anything else DRF recognizes | passthrough status | `"Error."` |
| unhandled exception | 500 | `"Internal server error."` |

Business-rule failures raised as `ValueError` inside a service (e.g. "Cannot transition from CONFIRMED to REQUESTED", "Specialist not found in your hospital") are caught in the view and returned as `error_response(errors={'detail': str(e)}, status_code=400)` (or 404 where the view chooses that code) — **not** routed through the global exception handler, since they're a plain `Response`, not a raised DRF exception.

## API reference

Base path: `/api/`. All authenticated endpoints require `Authorization: Bearer <access_token>`.

### Health

#### `GET /api/health/` — `AllowAny`

```json
{ "success": true, "message": "Service is healthy.", "data": { "status": "healthy" }, "errors": null, "meta": null }
```

### Auth — `/api/auth/`

#### `POST /api/auth/register/patient/` — `AllowAny`

Creates a `PATIENT` user, logs them in immediately, and sends an SMS OTP in the background.

Request body:

| Field | Type | Required | Notes |
|---|---|---|---|
| `full_name` | string | yes | max 255 chars; the patient's display name — shown to the hospital in the new-booking SMS instead of the auto-derived username |
| `phone_number` | string | yes | Any accepted format; normalized before storage; must be unique |
| `password` | string | yes | min length 8 |
| `username` | string | no | max 150 chars; auto-derived from phone if omitted |
| `email` | string | no | must be a valid email if provided; must be unique if provided |

```bash
curl -X POST http://localhost:8000/api/auth/register/patient/ \
  -H "Content-Type: application/json" \
  -d '{"full_name":"Amara Kessy","phone_number":"0712345678","password":"SecurePass123"}'
```

201 response:

```json
{
  "success": true,
  "message": "Patient registered successfully. A verification code has been sent by SMS.",
  "data": {
    "access": "eyJ...",
    "refresh": "eyJ...",
    "user": {
      "id": 5, "username": "255712345678", "full_name": "Amara Kessy", "email": "", "role": "PATIENT",
      "phone_number": "+255712345678", "phone_verified": false,
      "hospital": null, "date_joined": "2026-07-16T10:50:32.235708+03:00"
    }
  },
  "errors": null, "meta": null
}
```

400 causes: missing full name, phone number already registered, invalid phone format, password under 8 chars, username already taken, email already taken.

#### `POST /api/auth/login/` — `AllowAny`

```bash
curl -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"phone_number":"0712345678","password":"SecurePass123"}'
```

200 response: same shape as registration's `data` (`access`, `refresh`, `user`). 401 on any failure — wrong password *and* unknown phone number both return the same generic `"Invalid credentials."` (no user-enumeration signal).

#### `POST /api/auth/refresh/` — `AllowAny` (simplejwt stock view — **raw response, not enveloped**, see [Authentication](#authentication--authorization))

```bash
curl -X POST http://localhost:8000/api/auth/refresh/ \
  -H "Content-Type: application/json" -d '{"refresh":"eyJ..."}'
```

200 response: `{"access": "eyJ...", "refresh": "eyJ..."}` — no `success`/`data` wrapper.

#### `GET /api/auth/me/` — `IsAuthenticated`

```json
{
  "success": true, "message": "Success",
  "data": {
    "id": 5, "username": "255712345678", "email": "", "role": "PATIENT",
    "phone_number": "+255712345678", "phone_verified": true,
    "hospital": null, "date_joined": "2026-07-16T10:50:32.235708+03:00"
  },
  "errors": null, "meta": null
}
```

`hospital` is the hospital's numeric ID for `HOSPITAL_ADMIN` users, `null` otherwise.

#### `POST /api/auth/verify-otp/` — `IsAuthenticated`

Request: `{"code": "540690"}` (exactly 6 digits).

- 200 if the code matches an unconsumed, unexpired `PhoneOTP` for the current user — response `data` is the updated `UserSerializer` (now `phone_verified: true`).
- 200 immediately with `"Phone already verified."` if already verified (no-op, doesn't require a code).
- 400 `{"detail": "Invalid verification code."}` if no match.
- 400 `{"detail": "Verification code has expired. Request a new one."}` if the most recent matching code is past its 10-minute TTL.

#### `POST /api/auth/resend-otp/` — `IsAuthenticated`

No request body. Sends a new OTP unless already verified (in which case it's a no-op with `"Phone already verified."`). SMS failures are swallowed (best-effort) — the endpoint always returns 200 `"Verification code sent."` regardless of whether the underlying send actually succeeded (check `NotificationLog` to confirm delivery).

### Hospitals — `/api/hospitals/`

#### `POST /api/hospitals/register/` — `AllowAny`

Creates a `Hospital` (`status=PENDING`) and its `HOSPITAL_ADMIN` user in one transaction. Fires two SMS to the admin: a "registration received" notice and an OTP for phone verification (same OTP mechanism as patient registration).

| Field | Type | Required | Notes |
|---|---|---|---|
| `name` | string | yes | max 255 |
| `registration_no` | string | yes | max 100, must be unique |
| `latitude` | decimal | yes | 9 digits, 6 decimal places |
| `longitude` | decimal | yes | 9 digits, 6 decimal places |
| `address` | string | yes | |
| `phone` | string | yes | max 20 — the hospital's own public contact number (used for "new booking" SMS to the hospital); independent of the admin's login phone |
| `email` | string | yes | hospital's business email; unrelated to login |
| `admin_phone_number` | string | yes | the admin's login identity; normalized like any other phone; must be globally unique across all users |
| `admin_password` | string | yes | min length 8 |
| `admin_username` | string | no | auto-derived from `admin_phone_number` if omitted |
| `admin_email` | string | no | |

```bash
curl -X POST http://localhost:8000/api/hospitals/register/ \
  -H "Content-Type: application/json" -d '{
    "name": "Muhimbili Clinic", "registration_no": "REG-100",
    "latitude": -6.7924, "longitude": 39.2083,
    "address": "Dar es Salaam", "phone": "+255712999999", "email": "clinic@example.com",
    "admin_phone_number": "0713345678", "admin_password": "SecurePass123"
  }'
```

201 response — `data` is the hospital object (`HospitalSerializer`): `id, name, registration_no, latitude, longitude, address, phone, email, status ("PENDING"), created_at, updated_at`. Note: unlike patient registration, this endpoint does **not** return tokens — the new admin must call `/api/auth/login/` separately with `admin_phone_number` + `admin_password`.

400 causes: `registration_no` already exists, admin phone already registered, invalid phone format, password too short.

#### `GET /api/hospitals/me/` — `IsHospitalAdmin`

Returns the caller's own hospital (`HospitalSerializer`).

#### `PATCH /api/hospitals/me/` — `IsHospitalAdmin`

Partial update of the caller's own hospital. Any subset of `name, registration_no, latitude, longitude, address, phone, email`. `status` is read-only here (cannot self-verify).

#### `PATCH /api/hospitals/<id>/verify/` — `IsSuperAdmin`

Request: `{"status": "VERIFIED"}` or `{"status": "SUSPENDED"}`.

Valid transitions (`VerifyHospitalService.VALID_TRANSITIONS`):

```
PENDING   → VERIFIED, SUSPENDED
VERIFIED  → SUSPENDED
SUSPENDED → VERIFIED
```

Any other transition (e.g. `VERIFIED → VERIFIED`, or transitioning a still-`PENDING` hospital directly is fine but re-verifying an already-`VERIFIED` one is not) returns 400. On success, fires an SMS to the hospital's `HOSPITAL_ADMIN` (`hospital.admins.filter(role='HOSPITAL_ADMIN').first()`) — a congratulatory "you're live" message for `VERIFIED`, a suspension notice for `SUSPENDED`.

```bash
curl -X PATCH http://localhost:8000/api/hospitals/2/verify/ \
  -H "Authorization: Bearer $SUPER_ADMIN_TOKEN" -H "Content-Type: application/json" \
  -d '{"status":"VERIFIED"}'
```

#### `GET /api/hospitals/` — `IsSuperAdmin`

Paginated list of **all** hospitals regardless of status (`HospitalListSerializer` — same fields as `HospitalSerializer` minus `updated_at`). See [Pagination](#pagination--throttling).

### Specialists — `/api/specialists/`

All write endpoints are hospital-scoped: a `HOSPITAL_ADMIN` can only create/update/delete specialists belonging to `request.user.hospital` — the hospital is never taken from the request body, always from the authenticated admin's own record.

#### `POST /api/specialists/` — `IsHospitalAdmin`

| Field | Type | Required |
|---|---|---|
| `full_name` | string | yes |
| `specialization` | string | yes |
| `license_no` | string | yes — max 100, must be globally unique |
| `photo` | image file (multipart) | no |

> **Note:** `Specialist.photo` is an `ImageField`, but `MEDIA_ROOT`/`MEDIA_URL` are **not configured** in any settings file and no media-serving route exists in `config/urls.py`. Uploads will save to disk relative to the working directory but are not served back over HTTP in this codebase as-is — treat photo upload as a stub pending media storage configuration (e.g. S3/Cloud storage + `MEDIA_URL`) before relying on it.

201 response — `data` is `SpecialistSerializer`: `id, hospital, full_name, specialization, license_no, photo, is_active, created_by, created_at, updated_at`.

#### `PATCH /api/specialists/<id>/` — `IsHospitalAdmin`

Partial update — any subset of `full_name, specialization, license_no, is_active`. 404 if the specialist doesn't exist or doesn't belong to the caller's hospital (indistinguishable from the caller's perspective, by design — no cross-hospital existence leakage).

#### `DELETE /api/specialists/<id>/delete/` — `IsHospitalAdmin`

Soft delete (`SoftDeleteModel.soft_delete()` — sets `is_deleted=True`, `deleted_at=now()`; the row is never physically removed). 204 on success, 404 if not found/not owned.

#### `GET /api/specialists/mine/` — `IsHospitalAdmin`

Lists the caller's hospital's non-deleted specialists (`SpecialistListSerializer`, unpaginated array in `data`).

#### `GET /api/specialists/public/<id>/` — `AllowAny`

Patient-facing detail view. Only returns a result if the specialist is active, not deleted, **and** belongs to a `VERIFIED` hospital — otherwise 404, even if the specialist exists. Response is `PublicSpecialistSerializer`, which nests the full hospital object.

### Availability — `/api/availability/`

All endpoints are `IsHospitalAdmin` and implicitly scoped to `request.user.hospital`.

#### `POST /api/availability/` — set a specialist's status for one date

Request: `{"specialist_id": 3, "date": "2026-07-20", "status": "AVAILABLE"}` — `status` is one of `AVAILABLE | BUSY | OFF` (`AvailabilityChoice`). Upserts (`unique_together = (specialist, hospital, date)`) — 201 if a new row was created, 200 if an existing one was updated (`{"dates_updated"}`-style discrimination via the `created` flag).

```json
{ "success": true, "message": "Availability created successfully.",
  "data": { "id": 12, "specialist_id": 3, "date": "2026-07-20", "status": "AVAILABLE" },
  "errors": null, "meta": null }
```

#### `GET /api/availability/list/` — query own hospital's availability rows

Query params (all optional): `specialist_id`, `date_from`, `date_to` (both `YYYY-MM-DD`). Returns an unpaginated array: `[{id, specialist_id, specialist_name, date, status}, ...]`.

#### `POST /api/availability/schedule-template/` — bulk-set a recurring weekly pattern

Request: `{"specialist_id": 3, "schedule": {"0": "AVAILABLE", "1": "AVAILABLE", "2": "OFF", "3": "AVAILABLE", "4": "AVAILABLE", "5": "OFF", "6": "OFF"}}` — keys are weekday offsets (`0`=Monday … `6`=Sunday) for the **current** week only. Only dates `>= today` are written (already-past days in the current week are skipped silently). Response: `{"dates_updated": <count>}`.

### Search — `/api/search/`

#### `GET /api/search/nearby/` — `AllowAny`, throttled to **30 requests/minute per IP** (separate from the global anon rate)

Query params: `lat` (float, -90..90, required), `lng` (float, -180..180, required), `specialization` (string, optional, case-insensitive substring match), `radius` (float, 0.1–100 km, optional — omit for unlimited radius).

Algorithm (`GeoSearchService.nearby`, `apps/search/services.py`): iterates every `VERIFIED` hospital, computes haversine distance from the given point, filters by `radius` if given, then for each hospital filters active/non-deleted specialists (optionally by `specialization`), attaches each specialist's **today's** availability status if one exists (`null` if unset for today), skips hospitals with zero matching specialists, and sorts the whole result by distance ascending. Every call is logged to `NearbySearchLog` (feeds the reports below) with the client's IP (`X-Forwarded-For` first, falling back to `REMOTE_ADDR`).

```bash
curl "http://localhost:8000/api/search/nearby/?lat=-6.7924&lng=39.2083&specialization=cardio&radius=10"
```

```json
{
  "success": true, "message": "Success",
  "data": [
    {
      "hospital_id": 1, "hospital_name": "Test Hospital", "address": "123 Test Street",
      "latitude": -6.7924, "longitude": 39.2083, "distance_km": 0.0,
      "specialists": [
        { "id": 3, "full_name": "Dr. Amina Juma", "specialization": "Cardiology", "availability": "AVAILABLE" }
      ]
    }
  ],
  "errors": null, "meta": null
}
```

### Appointments — `/api/appointments/`

#### `POST /api/appointments/` — `IsPatient`

Request: `{"specialist_id": 3, "hospital_id": 1, "scheduled_at": "2026-07-20T10:00:00Z"}`. The specialist must exist, be active/non-deleted, and belong to the given `hospital_id`, or 400. A globally unique `reference_number` is generated per year (`APT-2026-00001`, `APT-2026-00002`, ...; `ReferenceNumberGenerator` uses a thread lock + `select_for_update()` to avoid collisions under concurrency). New appointments start `REQUESTED`.

**Side effects (both fire-and-forget, wrapped so a notification failure never fails the booking):**
1. SMS to the **patient**: booking-received confirmation (`NotificationDispatcher.appointment_requested`).
2. SMS to the **hospital's own contact number** (`Hospital.phone`, not the admin's login phone): new-booking alert asking them to confirm or cancel.

201 response — `data` is `AppointmentSerializer`: `id, reference_number, patient, patient_name, specialist, specialist_name, hospital, hospital_name, status, scheduled_at, created_at, updated_at`.

#### `GET /api/appointments/mine/` — `IsPatient`

All of the caller's own appointments (unpaginated array, `AppointmentSerializer`).

#### `GET /api/appointments/hospital/` — `IsHospitalAdmin`

All appointments for the caller's hospital (unpaginated array).

#### `PATCH /api/appointments/<id>/status/` — `IsHospitalAdmin`

Request: `{"status": "CONFIRMED"}` — one of `CONFIRMED | CANCELLED | COMPLETED` (a hospital admin can never set `REQUESTED`, that's only the initial state). 404 if the appointment doesn't belong to the caller's hospital.

Valid transitions (`AppointmentService.VALID_TRANSITIONS`):

```
REQUESTED → CONFIRMED, CANCELLED
CONFIRMED → COMPLETED, CANCELLED
CANCELLED → (terminal, no further transitions)
COMPLETED → (terminal, no further transitions)
```

**Side effect:** SMS to the **patient** — only for `CONFIRMED` (with date/specialist/hospital + "arrive 15 minutes early") and `CANCELLED` (cancellation notice). Transitioning to `COMPLETED` sends nothing.

### Reports — `/api/reports/` (both `IsSuperAdmin`, read-only)

#### `GET /api/reports/overview/`

```json
{
  "success": true, "message": "Success",
  "data": {
    "hospitals": { "total": 5, "pending": 1, "verified": 3, "suspended": 1 },
    "specialists": { "total": 12, "active": 10 },
    "appointments": { "total": 40, "requested": 5, "confirmed": 10, "completed": 20, "cancelled": 5 },
    "total_searches": 230,
    "top_specializations": [ { "specialization": "Cardiology", "count": 4 }, ... ]
  },
  "errors": null, "meta": null
}
```

`top_specializations` counts **specialists per specialization** (not search volume), top 10, from `apps/specialists/models.py: Specialist`. `specialists.total/active` both exclude soft-deleted rows.

#### `GET /api/reports/searches/`

```json
{
  "success": true, "message": "Success",
  "data": {
    "total_searches": 230,
    "top_searched_specializations": [ { "specialization": "Cardiology", "count": 40 }, ... ],
    "recent_searches": [
      { "latitude": -6.7924, "longitude": 39.2083, "specialization": "Cardiology", "results_count": 3, "created_at": "2026-07-16T10:00:00+03:00" },
      ...
    ]
  },
  "errors": null, "meta": null
}
```

`top_searched_specializations` here counts **search queries** per specialization (top 10, excluding blank), distinct from the overview report's per-specialist count above. `recent_searches` is the most recent 25 `NearbySearchLog` rows.

### API docs (auto-generated)

- `GET /api/schema/` — raw OpenAPI 3 schema (drf-spectacular).
- `GET /api/docs/` — Swagger UI browsing that schema. Useful for exploring exact field-level validation drf-spectacular infers from the serializers, though the hand-written examples above are more reliable for the response envelope shape (drf-spectacular doesn't know about the custom envelope wrapping).

### Admin

- `GET /admin/` — Django's built-in admin site. Registered models per app's `admin.py` (`hospitals`, `specialists`, `availability`, `common`, `notifications`). Uses Django's own session auth, entirely separate from the JWT API.

## Data models

### `common.User` (`db_table = 'users'`, extends Django's `AbstractUser`)

| Field | Type | Notes |
|---|---|---|
| `role` | choice | `PATIENT` (default) \| `HOSPITAL_ADMIN` \| `SUPER_ADMIN` |
| `hospital` | FK → `Hospital`, nullable | set only for `HOSPITAL_ADMIN`; `on_delete=SET_NULL` |
| `phone_number` | string, unique, nullable | canonical `+255XXXXXXXXX` |
| `phone_verified` | boolean, default `False` | |
| `full_name` | string, blank-default | required at patient registration; blank for accounts created before this field existed or via other paths (hospital admin, super admin) that don't collect it |
| plus all of Django's `AbstractUser` fields | | `username`, `email`, `password` (hashed), `is_active`, `is_staff`, `date_joined`, etc. |

### `accounts.PhoneOTP` (`db_table = 'phone_otps'`)

| Field | Type |
|---|---|
| `user` | FK → `User`, `related_name='phone_otps'` |
| `code` | string, 6 chars |
| `expires_at` | datetime — created at `now() + 10 minutes` |
| `consumed_at` | datetime, nullable — set when successfully verified |
| `created_at` / `updated_at` | auto |

### `hospitals.Hospital` (`db_table = 'hospitals'`)

| Field | Type |
|---|---|
| `name` | string |
| `registration_no` | string, unique |
| `latitude` / `longitude` | decimal(9,6) |
| `address` | text |
| `phone` | string — public contact number, used for booking-alert SMS |
| `email` | email |
| `status` | choice — `PENDING` (default) \| `VERIFIED` \| `SUSPENDED` |

### `specialists.Specialist` (`db_table = 'specialists'`, soft-deletable)

| Field | Type |
|---|---|
| `hospital` | FK → `Hospital`, `related_name='specialists'` |
| `full_name` / `specialization` | string |
| `license_no` | string, unique |
| `photo` | image (see media-serving caveat above) |
| `is_active` | boolean, default `True` |
| `created_by` | FK → `User`, `SET_NULL` |
| `is_deleted` / `deleted_at` | soft-delete fields from `SoftDeleteModel` |

### `availability.AvailabilityStatus` (`db_table = 'availability_statuses'`)

| Field | Type |
|---|---|
| `specialist` | FK → `Specialist` |
| `hospital` | FK → `Hospital` |
| `date` | date |
| `status` | choice — `AVAILABLE` (default) \| `BUSY` \| `OFF` |
| `updated_by` | FK → `User`, `SET_NULL` |

`unique_together = (specialist, hospital, date)` — one row per specialist per day.

### `appointments.Appointment` (`db_table = 'appointments'`)

| Field | Type |
|---|---|
| `patient` | FK → `User` |
| `specialist` | FK → `Specialist` |
| `hospital` | FK → `Hospital` |
| `reference_number` | string, unique, indexed — `APT-<year>-<5-digit-seq>` |
| `status` | choice — `REQUESTED` (default) \| `CONFIRMED` \| `CANCELLED` \| `COMPLETED` |
| `scheduled_at` | datetime |

### `notifications.NotificationLog` (`db_table = 'notification_logs'`)

| Field | Type |
|---|---|
| `recipient` | string — phone number (or `'unknown'` if none was available) |
| `channel` | choice — `SMS` (default) \| `EMAIL` (email is not implemented, enum-only) |
| `message` | text |
| `status` | choice — `PENDING` (default) \| `SENT` \| `FAILED` |
| `provider_response` | JSON — SendAfrica's response body, or `{"error": "..."}` on failure |
| `sent_at` | datetime, nullable |
| `appointment` | FK → `Appointment`, nullable, `SET_NULL` — absent for OTP/hospital-approval notifications |

### `search.NearbySearchLog` (`db_table = 'nearby_search_logs'`)

| Field | Type |
|---|---|
| `latitude` / `longitude` | decimal(9,6) |
| `specialization` | string, blank-default |
| `radius_km` | decimal(5,2), nullable |
| `results_count` | positive int |
| `ip_address` | IP, nullable |

## SMS notifications reference

All SMS flow through `NotificationDispatcher` (`apps/notifications/services.py`) → `NotificationDispatcher._send` → creates a `NotificationLog` (`status=PENDING`) → enqueues `send_sms_task.delay(log.id)` on Celery → the worker calls `SmsService.send()` against SendAfrica and updates the log to `SENT`/`FAILED`. If no phone number is available at all, `_send` skips Celery entirely and logs straight to `FAILED` with `recipient='unknown'`.

| Trigger | Method | Recipient | When |
|---|---|---|---|
| Patient/hospital-admin registration | `otp_verification` | the new user | immediately after account creation |
| OTP resend | `otp_verification` | the requesting user | on `POST /api/auth/resend-otp/` |
| Hospital registration submitted | `hospital_registration_received` | new hospital's admin phone | immediately after `POST /api/hospitals/register/` succeeds |
| Hospital verified | `hospital_verified` | hospital's `HOSPITAL_ADMIN` phone | `PATCH /api/hospitals/<id>/verify/` with `status: VERIFIED` |
| Hospital suspended | `hospital_suspended` | hospital's `HOSPITAL_ADMIN` phone | `PATCH /api/hospitals/<id>/verify/` with `status: SUSPENDED` |
| Appointment requested | `appointment_requested` | patient | immediately after `POST /api/appointments/` succeeds |
| New booking | `new_booking_for_hospital` | hospital's own `phone` field | immediately after `POST /api/appointments/` succeeds |
| Appointment confirmed | `appointment_confirmed` | patient | `PATCH /api/appointments/<id>/status/` with `status: CONFIRMED` |
| Appointment cancelled | `appointment_cancelled` | patient | `PATCH /api/appointments/<id>/status/` with `status: CANCELLED` |
| Appointment reminder | `appointment_reminder` | patient | **not currently triggered anywhere** — no Celery Beat schedule exists; available for future use |

Phone number formatting for SMS uses the same `SmsService.normalize_phone` as login/registration, so any of the accepted input formats work as a `recipient`.

## Pagination & throttling

**Pagination** (`apps/common/pagination.py: StandardPagination`, `PAGE_SIZE = 25`, `max_page_size = 200`) applies only to endpoints using DRF's generic `ListAPIView` — in this codebase, only `GET /api/hospitals/`. Its envelope differs slightly from a plain success response by populating `meta.pagination`:

```json
{ "success": true, "message": "Success", "data": [...],
  "errors": null, "meta": { "pagination": { "count": 42, "next": "http://.../api/hospitals/?page=2", "previous": null, "page_size": 25 } } }
```

Every other "list" endpoint (`/specialists/mine/`, `/availability/list/`, `/appointments/mine/`, `/appointments/hospital/`, `/search/nearby/`) returns a **plain unpaginated array** in `data` — there is no `page`/`page_size` query param support on those.

**Throttling** (`REST_FRAMEWORK.DEFAULT_THROTTLE_RATES`): `anon: 100/hour`, `user: 1000/hour`, applied globally. `GET /api/search/nearby/` additionally applies its own `AnonRateThrottle` at **30/minute**, which is the binding limit for that endpoint since it's stricter than the global anon rate.

## Testing

```bash
pytest                          # full suite
pytest apps/accounts/tests.py   # one app
pytest -k test_login_success    # one test
```

71 tests across all apps as of this writing. Notification-triggering code paths (registration, booking, hospital verification) are tested by asserting on the `NotificationLog` row's `status`/`recipient`/`message` content — not by mocking the SendAfrica HTTP call for every path, since `_send()`'s Celery dispatch never reaches a live worker inside the test process (see the note in [Getting started](#run-tests)). `apps/notifications/tests.py: TestSmsServiceSend` does mock `requests.post` directly to test `SmsService.send()`'s own success/failure parsing in isolation.

## Pushing changes (git, explained simply)

This repo is separate from the frontend (`kindamba-ui`) — it has its own history and its own remote on GitHub, and you commit/push it independently from the UI repo. "Pushing" just means: upload your saved changes from your computer to GitHub, where everyone else on the project can see and pull them.

This repo's remote is set up over **SSH** (`git@github.com:...`, visible via `git remote -v`), not a plain web link — so before you can push for the first time, two things need to be true:

1. **You've been added as a collaborator** on the GitHub repository (ask whoever owns it — currently `troubleman96` — to add your GitHub account under the repo's Settings → Collaborators).
2. **Your computer has proven its identity to GitHub via an SSH key.** This is a one-time setup:
   ```bash
   ssh-keygen -t ed25519 -C "your-email@example.com"    # press Enter three times to accept the defaults
   ```
   This creates a public/private key pair (on Windows, in `C:\Users\<you>\.ssh\`). Print the **public** key and copy it:
   ```bash
   cat ~/.ssh/id_ed25519.pub          # macOS/Linux
   type $env:USERPROFILE\.ssh\id_ed25519.pub    # Windows PowerShell
   ```
   Paste that into GitHub: **Settings → SSH and GPG keys → New SSH key**. Then test it worked:
   ```bash
   ssh -T git@github.com
   ```
   It should greet you by username ("Hi `<your-username>`! You've successfully authenticated..."). If you'd rather avoid SSH keys entirely, GitHub's own [Desktop app](https://desktop.github.com/) handles authentication for you with a browser login instead — a good alternative if the above feels like too much.

### The everyday workflow

Every time you've made changes you want to save to GitHub, from inside the `Kindamba` folder:

```bash
git status                    # 1. see what you changed — nothing is sent anywhere yet, this is just a look
git add <file1> <file2>       # 2. "stage" the specific files you want to include (or `git add .` for everything shown)
git commit -m "what changed"  # 3. save a snapshot locally, with a short message describing it
git push origin master        # 4. upload that snapshot (and any earlier unpushed ones) to GitHub
```

Nothing leaves your computer until step 4 — steps 1–3 are entirely local, so it's safe to `git status` and `git add` as often as you like while figuring things out. **Never `git add .env`** — it holds real secrets and is already excluded via `.gitignore`, but always double-check `git status` doesn't list it before committing.

### Common errors, and what they actually mean

| Message | What it means | Fix |
|---|---|---|
| `Permission denied (publickey)` | GitHub doesn't recognize your machine yet | Finish the SSH key setup above, or use GitHub Desktop instead |
| `remote: Repository not found` | Either the URL is wrong, or you haven't been added as a collaborator yet | Confirm `git remote -v` matches the repo, and confirm your GitHub account has been invited |
| `! [rejected] ... (fetch first)` / `failed to push some refs` | Someone else pushed changes since you last pulled — git refuses to silently overwrite them | Run `git pull origin master` first (this merges their changes into yours), resolve anything it flags as conflicting, then `git push origin master` again |
| `Please tell me who you are` | Git needs a name/email for commit history (once per machine) | `git config --global user.name "Your Name"` and `git config --global user.email "you@example.com"` |

## Deployment (production)

For production, set `DJANGO_SETTINGS_MODULE=config.settings.prod`, provide a real `DATABASE_URL` (PostgreSQL), set `DJANGO_ALLOWED_HOSTS` and `CORS_ALLOWED_ORIGINS`, and serve behind gunicorn with a reverse proxy. Run `python manage.py collectstatic` before deploying. Before relying on specialist photo uploads in production, add proper `MEDIA_ROOT`/`MEDIA_URL` (or cloud storage) configuration — see the caveat under [Specialists](#specialists--apispecialists).
