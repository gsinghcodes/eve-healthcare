# EVE Healthcare API

Backend API for a diagnostic healthcare booking platform built with FastAPI, PostgreSQL, Redis, Celery, SQLAlchemy, and Alembic.

## Features

- OTP-based authentication
- JWT access tokens and HTTP-only refresh-token rotation
- Proper logging per service
- Diagnostic test discovery
- Radius-based diagnostic centre search
- Centre details with available test offerings
- Appointment date and slot availability
- Booking creation, rescheduling, cancellation, and history
- Payment creation and webhook handling
- Idempotent payment webhook events
- Pending-booking expiration with Celery
- Redis-backed rate limiting
- Role-based access control
- Database-level protection against concurrent slot booking
- Alembic database migrations

## Tech Stack

- Python 3.12
- FastAPI
- SQLAlchemy
- PostgreSQL
- Psycopg
- Alembic
- Redis
- Celery
- PyJWT
- Pydantic Settings
- Uvicorn

## Run with Docker Compose

Docker Compose runs the complete backend stack:

- FastAPI
- PostgreSQL
- Redis
- Celery Worker
- Celery Beat

### Requirements

- Docker Desktop, or Docker Engine with the Docker Compose plugin

### 1. Create the Docker environment file

PowerShell:

```powershell
Copy-Item .env.docker.example .env
```

macOS/Linux:

```bash
cp .env.docker.example .env
```

### 2. Build and start the stack

```bash
docker compose up --build
```

The API container runs the database migrations before starting FastAPI.

### 3. API

```text
http://localhost:8000
```

Swagger UI:

```text
http://localhost:8000/docs
```

OpenAPI:

```text
http://localhost:8000/openapi.json
```

### 4. Stop the stack

```bash
docker compose down
```


### 5. View logs

All services:

```bash
docker compose logs -f
```

API:

```bash
docker compose logs -f app
```

Worker:

```bash
docker compose logs -f worker
```

Beat:

```bash
docker compose logs -f beat
```

## Docker Services

| Service | Purpose | Port |
|---|---|---:|
| `app` | FastAPI application | `8000` |
| `worker` | Celery background worker | internal |
| `beat` | Celery periodic scheduler | internal |
| `db` | PostgreSQL database | `5432` |
| `redis` | Celery broker and rate limiting | `6379` |

The `app`, worker, and Beat services use the same backend image with different commands.

## Running Scripts

Utility scripts are located in the `scripts/` directory.

Run a script inside the API container with:

```bash
docker compose exec app python -m scripts.<script_name>
```

For example:

```bash
docker compose exec app python -m scripts.seed_data
```

Use the Python module name without the `.py` extension.


## Environment Variables

The application requires:

```env

DATABASE_URL=...
JWT_SECRET_KEY=...
POSTGRES_USER=...
POSTGRES_PASSWORD=...
POSTGRES_DB=...
POSTGRES_HOST=...
POSTGRES_PORT=...

```

## Database / Schema Design

The database is structured around the diagnostic booking flow.

```text
User
 │
 ├── Authentication / Refresh Tokens
 │
 └── Bookings
       │
       ├── Payment
       │
       └── Schedule
             │
             └── Centre Test
                    │
                    ├── Diagnostic Centre
                    └── Diagnostic Test
```

A diagnostic test represents the public test being searched for, while a centre test represents that test as an offering at a specific diagnostic centre.

Schedules represent available appointment slots. Bookings reference the selected schedule and centre test.

Bookings initially enter `PENDING` and receive an `expires_at` timestamp. An unexpired pending booking occupies the slot. Once the expiration time passes, the slot is logically available even if the Celery cleanup task has not yet run.

Payment records are associated with bookings, while webhook events are stored separately using the provider event ID. Webhook event IDs have a database-level unique constraint to prevent duplicate event records.

Database constraints and row-level locking provide protection against concurrent slot booking.

## Authentication

Authentication uses OTP verification followed by JWT authentication.

Main endpoints:

```text
POST /api/v1/auth/request-otp
POST /api/v1/auth/verify-otp
POST /api/v1/auth/refresh
```

Refresh tokens are stored in HTTP-only cookies and rotated during refresh.

For local HTTP development:

```env
REFRESH_TOKEN_COOKIE_SECURE=false
```

For HTTPS production deployments, it should be enabled.

## Diagnostic Tests

Diagnostic tests are exposed under:

```text
/api/v1/tests
```

The frontend uses test discovery before searching for diagnostic centres.

## Diagnostic Centres

Centre APIs are under:

```text
/api/v1/centres
```

Search:

```text
POST /api/v1/centres/search
```

Centre details:

```text
GET /api/v1/centres/{center_id}
```

The centre detail response includes its available test offerings.

Each item in the `tests` array represents a centre-specific test offering. Its `id` is the `center_test_id` used by scheduling and booking APIs.


## Appointment Scheduling

Available slots are requested for a specific centre test and appointment date.

Dates use:

```text
YYYY-MM-DD
```

Example:

```text
2026-09-27
```

Appointment times are aligned to 30-minute slots.

## Booking Flow

```text
Select diagnostic test
        ↓
Search centres
        ↓
Open centre
        ↓
Select centre test
        ↓
Select appointment date
        ↓
Fetch available slots
        ↓
Select slot
        ↓
Create pending booking
        ↓
Complete payment
        ↓
Confirm booking
```


### Booking Expiration

New bookings start as `PENDING` and receive an `expires_at` timestamp based on:


A pending booking with an unexpired `expires_at` blocks its slot.

Celery Beat triggers the expiration task every 60 seconds. The worker marks expired pending bookings as `EXPIRED` and releases the associated schedule state.

### Concurrency Protection

Availability checks are combined with row locking and database-level constraints to prevent concurrent double booking.

## Payments

Payment APIs are exposed under:

```text
/api/v1/payments
```

The payment state machine supports:

```text
PENDING → SUCCESS
PENDING → FAILED
SUCCESS → REFUNDED
```

Repeated webhook delivery for the same event is handled idempotently using the provider event ID and payment state validation.

The webhook event ID is protected by a database-level unique constraint to prevent duplicate event records.

For production payment-provider integration, webhook signature verification should be performed before processing payment events.

## Celery

Celery uses Redis as its broker.

The booking expiration task runs every 60 seconds through Celery Beat:

```text
tasks.booking_tasks.release_expired_bookings
```

The worker and Beat processes run separately so they can be restarted and scaled independently.

## Redis Rate Limiting

Redis is used for application-level rate limiting.

The configured limits cover:

- OTP requests
- OTP verification
- Refresh-token requests
- Booking creation
- Payment operations

The rate-limit values have application defaults in configuration and can be overridden through environment variables when required.

## Testing

Run the test suite:

```bash
pytest -q
```

Make sure the required environment variables and dependent services are available.

## Important Assumptions

- A booking represents one appointment slot for one centre test.
- An unexpired `PENDING` booking temporarily reserves its slot.
- Booking expiration is determined using `expires_at`, not the timing of the Celery cleanup task.
- A successful payment confirms an active pending booking.
- A successful payment received after a booking has expired does not reactivate that booking and the amount is refunded.
- Payment providers may retry webhook delivery, so webhook processing must be idempotent.
- Concurrent booking attempts can occur and must be protected at the database level.

## What I Would Improve With More Time

- Add user notifications for different user types and events such as bookings, cancellations, payments, and appointments.
- Make the RBAC system more granular with role-specific permissions and endpoints.
- Add S3 or Google Cloud Storage for centre images and other uploaded assets.
- Implement proper refund logic based on how far in advance an appointment is cancelled.
- Improve production infrastructure and observability as the system scales.

## API Documentation

After starting the API:

```text
http://localhost:8000/docs
```

Swagger UI provides interactive documentation for the API.

OpenAPI JSON:

```text
http://localhost:8000/openapi.json
```

## Health Check

```text
GET /
```

Example response:

```json
{
  "status": 200,
  "message": "EVE Healthcare API is running"
}
```

## Architecture

```text
                    ┌─────────────────┐
                    │     FastAPI     │
                    │       API       │
                    └────┬───────┬────┘
                         │       │
                         │       └──────────────┐
                         ▼                      ▼
                  ┌────────────┐         ┌───────────┐
                  │ PostgreSQL │         │   Redis   │
                  └────────────┘         └─────┬─────┘
                                               │
                                      ┌────────┴────────┐
                                      ▼                 ▼
                               ┌────────────┐    ┌────────────┐
                               │   Celery   │    │   Celery   │
                               │   Worker   │    │    Beat    │
                               └────────────┘    └────────────┘
```
