# EVE Healthcare API

Backend API for a diagnostic healthcare booking platform built with FastAPI, PostgreSQL, Redis, Celery, SQLAlchemy, and Alembic.

## Features

- OTP-based authentication

- JWT access tokens and HTTP-only refresh-token rotation

- Diagnostic test discovery

- Radius-based diagnostic centre search

- Centre detail with available test offerings

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

Docker Compose is the recommended way to run the complete local backend because the application uses FastAPI, PostgreSQL, Redis, a Celery worker, and Celery Beat.

### Requirements

Install:

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

Set a strong value for `JWT_SECRET_KEY` in `.env`.

### 2. Build and start the stack

```bash

docker compose up --build

```

The first startup performs the following sequence:

```text

PostgreSQL becomes healthy

        ↓

Alembic migrations run

        ↓

FastAPI starts

        ↓

Celery Worker starts

        ↓

Celery Beat starts

```

### 3. API endpoints

FastAPI:

```text

http://localhost:8000

```

Swagger UI:

```text

http://localhost:8000/docs

```

OpenAPI schema:

```text

http://localhost:8000/openapi.json

```

### 4. Stop the application

```bash

docker compose down

```

To remove the PostgreSQL and Redis Docker volumes as well:


### 5. View service logs

All services:

```bash

docker compose logs -f

```

API only:

```bash

docker compose logs -f app

```

Celery worker:

```bash

docker compose logs -f worker

```

Celery Beat:

```bash

docker compose logs -f beat

```

## Docker Services

The Compose stack contains five application/infrastructure services:

| Service | Purpose | Port |

|---------|---------|------|

| `api` | FastAPI application | `8000` |

| `worker` | Celery background worker | internal |

| `beat` | Celery periodic scheduler | internal |

| `postgres` | PostgreSQL database | `5432` |

| `redis` | Celery broker and rate limiting | `6379` |

There is also a short-lived `migrate` service that runs `alembic upgrade head` before the API, worker, and Beat services start.

The API, worker, and Beat all use the same backend Docker image. Their commands differ according to their responsibility.

## Local Non-Docker Development

Docker is recommended, but the backend can also be run directly with Python.

Create a virtual environment:

```bash

python -m venv .venv

```

Activate it on Windows PowerShell:

```powershell

.venv\Scripts\Activate.ps1

```

Activate it on macOS/Linux:

```bash

source .venv/bin/activate

```

Install dependencies:

```bash

pip install -r requirements.txt

```

Configure `.env` using `.env.example`, then run:

```bash

alembic upgrade head

```

Start FastAPI:

```bash

uvicorn main\:app --reload

```

Start the Celery worker in another terminal:

```bash

celery -A core.celery_app.celery_app worker --loglevel=info

```

Start Celery Beat in another terminal:

```bash

celery -A core.celery_app.celery_app beat --loglevel=info

```

## Environment Variables

The application requires at least:

```env

DATABASE_URL=...
JWT_SECRET_KEY=...
POSTGRES_USER=...
POSTGRES_PASSWORD=...
POSTGRES_DB=...
POSTGRES_HOST=...
POSTGRES_PORT=...

```

### Docker-specific database and Redis URLs

Inside Docker Compose, service names are used for communication:

```text

postgresql+psycopg://postgres:postgres@postgres:5432/eve_healthcare

redis://redis:6379/0

```

Do not use `localhost` for these internal connections from a container. `localhost` inside a container refers to that same container.

## Database Migrations

Run migrations directly:

```bash

alembic upgrade head

```

Create a migration after changing SQLAlchemy models:

```bash

alembic revision --autogenerate -m "describe the change"

```

Review generated migrations before applying them.


## Running Scripts

Project utility scripts are located in the `scripts/` directory.

After the Docker stack is running, execute a script inside the API container using:

```bash
docker compose exec app python -m scripts.<script_name>
```

For example:

```bash
docker compose exec app python -m scripts.seed_data
```

Replace `<script_name>` with the Python module you want to run.

The script should be referenced as a Python module, without the `.py` extension.

For example:

```text
scripts/
├── seed_data.py
├── create_admin.py
└── ...
```

Run them as:

```bash
docker compose exec app python -m scripts.seed_data
docker compose exec app python -m scripts.create_admin
```

These scripts run inside the same Docker environment as the API, so they use the configured application environment and can connect to the Docker PostgreSQL and Redis services.


With Docker Compose, migrations are run automatically by the `migrate` service during startup.

## Authentication

Authentication uses OTP verification followed by JWT authentication.

Main endpoints include:

```text

POST /api/v1/auth/request-otp

POST /api/v1/auth/verify-otp

POST /api/v1/auth/refresh

```

The refresh token is stored in an HTTP-only cookie and rotated during refresh.

For local HTTP development, the Docker example sets:

```env

REFRESH_TOKEN_COOKIE_SECURE=false

```

For HTTPS production deployments it should be enabled.

## Diagnostic Tests

Diagnostic tests are exposed under:

```text

/api/v1/tests

```

The public test-discovery flow is used by the frontend to select a diagnostic test before searching for centres.

## Diagnostic Centres

Centre APIs are under:

```text

/api/v1/centres

```

### Search

```text

POST /api/v1/centres/search

```

The search supports radius-based centre discovery and optional filtering by diagnostic test.

### Centre Details

```text

GET /api/v1/centres/{center_id}

```

The response includes the centre's available test offerings.

Each item in the `tests` array represents a centre-specific test offering. Its `id` is the `center_test_id` used by the scheduling and booking APIs.

## Appointment Scheduling

Available appointment slots are requested for a specific centre test and date.

Appointment dates use the date-only format:

```text

YYYY-MM-DD

```

Example:

```text

2026-09-27

```

Appointment times are aligned to 30-minute slots.

## Booking Flow

The booking flow is:

```text

Select diagnostic test

        ↓

Search centres

        ↓

Open centre

        ↓

Select centre's test offering

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

A booking request contains:

```json

{

  "center_test_id": "uuid",

  "appointment_date": "2026-09-27",

  "time_slot": "16:00:00"

}

```

### Booking expiration

New bookings initially have `PENDING` status and an `expires_at` timestamp controlled by:

```env

BOOKING_PAYMENT_TIMEOUT_MINUTES=10

```

A pending booking with an unexpired `expires_at` blocks its slot. Once the expiration time passes, the slot is logically available even before the periodic cleanup task runs.

Celery Beat triggers the expiration task every 60 seconds. The Celery worker marks expired pending bookings as `EXPIRED` and releases the associated schedule state.

### Concurrency protection

Application-level availability checks are combined with row locking and a database-level active-slot uniqueness constraint to protect against concurrent double booking.

## Payments

Payment APIs are exposed under:

```text

/api/v1/payments

```

The payment flow supports payment creation and webhook processing.

The payment state machine allows the following transitions:

```text

PENDING → SUCCESS

PENDING → FAILED

SUCCESS → REFUNDED

```

Repeated webhook delivery for the same event is handled idempotently.

For a production payment-provider integration, provider-specific webhook signature verification should be configured before processing real payment events.

## Celery

Celery uses Redis as its broker.

The configured periodic task is:

```text

tasks.booking_tasks.release_expired_bookings

```

It runs every 60 seconds through Celery Beat.

The worker and Beat processes are deliberately separate containers in Docker Compose so each process has one responsibility and can be restarted or scaled independently.

## Redis Rate Limiting

Redis is also used for application-level rate limiting.

The configured limits cover operations including:

- OTP requests

- OTP verification

- Refresh-token requests

- Booking creation

- Payment operations

Limits are configurable through environment variables.

## Testing

Run the test suite locally with:

```bash

pytest -q

```

Make sure the required environment variables are configured before running tests.

For integration tests that use PostgreSQL or Redis, make sure those services are running.

With Docker Compose, the application services are available through the same local infrastructure used by the backend.


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

## End-to-End Architecture

```text

                    ┌─────────────────┐

                    │     FastAPI     │

                    │       API       │

                    └────┬───────┬────┘

                         │       │

                         │       └──────────────┐

                         ▼                      ▼

                  ┌────────────┐         ┌───────────┐

                  │ PostgreSQL │         │   Redis   │

                  └────────────┘         └─────┬─────┘

                                               │

                                  ┌────────────┴────────────┐

                                  ▼                         ▼

                           ┌────────────┐            ┌────────────┐

                           │   Celery   │            │   Celery   │

                           │   Worker   │            │    Beat    │

                           └────────────┘            └────────────┘

```