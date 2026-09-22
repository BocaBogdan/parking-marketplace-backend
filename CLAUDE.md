# CLAUDE.md — Parking Spot Marketplace Backend

## Project Overview

Residential parking sharing platform. Owners list their private spots with availability schedules, neighbours browse and reserve them in 30-minute slots. Admin approves spots before they go live. All spots are privately owned — there is no public or guest parking.

Full grooming doc: `docs/grooming-v1.md`

## Tech Stack

- **Python 3.11+** with **FastAPI** (async)
- **PostgreSQL 15+** with `btree_gist` extension
- **SQLAlchemy 2.x** (async, mapped_column style)
- **Alembic** for migrations
- **Pydantic v2** for request/response schemas
- **JWT** authentication (access + refresh token pair)
- **bcrypt** for password hashing
- **uvicorn** as ASGI server

## Project Structure

```
app/
├── core/           # Config, security (JWT, hashing), dependencies
├── models/         # SQLAlchemy ORM models (one file per table)
├── schemas/        # Pydantic v2 request/response schemas
├── services/       # Business logic — all logic lives here
├── routers/        # FastAPI route handlers — thin, no business logic
└── main.py         # App factory, router registration, middleware
alembic/
├── versions/       # Migration scripts
└── env.py
tests/
├── conftest.py     # Fixtures: async client, test DB, seeded data
├── test_auth.py
├── test_cars.py
├── test_spots.py
├── test_availability.py
├── test_reservations.py
└── test_admin.py
```

## Coding Conventions

### Python / General

- Use `async def` for all route handlers and service functions
- Type-hint everything: function params, return types, variables where not obvious
- Use `Annotated[T, Depends(...)]` for FastAPI dependencies (not `param: T = Depends(...)`)
- Imports: stdlib → third-party → local, separated by blank lines. Use absolute imports (`from app.models.user import User`)
- No wildcard imports
- f-strings for string formatting
- Use `Enum` (Python stdlib) for all enumerated values; mirror DB enums exactly

### FastAPI Routers

- Routers stay **thin** — validate input, call service, return response
- No raw SQL or ORM queries in routers
- Group routers by domain: `auth.py`, `users.py`, `cars.py`, `spots.py`, `reservations.py`, `admin.py`
- Use `APIRouter(prefix=..., tags=[...])` for each module
- Return Pydantic response models explicitly via `response_model=`
- Use HTTP status codes correctly: 201 for creation, 204 for deletion, 404 for not found, 409 for conflict, 422 for validation

### Services

- One service file per domain (e.g. `availability_service.py`, `reservation_service.py`)
- All business logic and DB queries live here
- Services receive an `AsyncSession` (injected via dependency)
- Raise `HTTPException` from services — routers propagate them
- Keep functions small and single-purpose

### Pydantic Schemas

- Separate schemas for Create, Update, and Response (e.g. `SpotCreate`, `SpotUpdate`, `SpotResponse`)
- Use `model_config = ConfigDict(from_attributes=True)` on response schemas
- Never expose `password_hash` in any response
- **PII rule**: `phone_number` and car `plate` appear only in owner-facing and admin response schemas, never in public/browse schemas

### SQLAlchemy Models

- Use `mapped_column()` with explicit types (SQLAlchemy 2.x declarative style)
- All tables use `uuid` primary keys (server-default `gen_random_uuid()`)
- All tables have `created_at: Mapped[datetime]` with server-default `now()`
- Soft-delete via `is_active: Mapped[bool]` flag — never hard-delete user data
- Foreign keys use `ondelete="CASCADE"` for ownership (user→cars) and `ondelete="SET NULL"` for references that must survive deletion (reservation→car)
- Use `relationship()` with `lazy="selectin"` for commonly needed joins

## Database Conventions

- **Migrations**: Always use Alembic. Never modify the DB schema by hand. One migration per logical change.
- **Naming**: snake_case for tables and columns. Table names are plural (`users`, `parking_spots`, `reservations`).
- **Enums**: Define as PostgreSQL enums. Values are UPPER_SNAKE_CASE.
  - `user_role`: `DRIVER | OWNER | ADMIN`
  - `spot_status`: `PENDING | APPROVED | REJECTED | INACTIVE`
  - `override_type`: `FREE | BUSY`
  - `reservation_status`: `CONFIRMED | CANCELLED | CANCELLED_BY_OWNER | CANCELLED_BY_ADMIN`
- **Exclusion constraint**: `reservations` table uses a `tstzrange(starts_at, ends_at)` exclusion constraint with `&&` on `spot_id` to prevent double-booking at the DB level. Requires `btree_gist` extension.
- **Indexes**: On all foreign keys, on `users.email` (unique), on `parking_spots.status`, on `reservations.starts_at`.

## Key Business Rules

1. **Roles**: `DRIVER` (default) → `OWNER` → `ADMIN`. Admin cannot be self-assigned. First admin seeded via script.
2. **Spot approval**: Owner submits → `PENDING` → admin approves (`APPROVED`) or rejects (`REJECTED` with reason). Only `APPROVED` spots appear in browse.
3. **Cascading cancellation**: When a spot is rejected or deactivated, all its future `CONFIRMED` reservations become `CANCELLED_BY_ADMIN`.
4. **Resubmission**: Owner can update a `REJECTED` spot — status resets to `PENDING`.
5. **Availability resolution** (critical logic to test exhaustively):
   - Spot must be active AND `APPROVED`
   - Recurring schedule covers the window OR a `FREE` override covers it
   - No `BUSY` override overlaps the window
   - No `CONFIRMED` reservation overlaps the window
   - Overrides always beat schedules
6. **30-minute slots**: `starts_at` must align to `:00` or `:30`. Duration is a multiple of 30 minutes.
7. **Reservation requires car**: `car_id` is mandatory on booking; must belong to the authenticated user.
8. **Owner cannot reserve own spot**.
9. **Cancellation deadline**: Driver can cancel up to 15 minutes before slot starts (configurable).

## Auth & Dependencies

FastAPI dependency chain:
```python
get_current_user      # Decodes JWT, returns User
require_owner         # get_current_user + role >= OWNER
require_admin         # get_current_user + role == ADMIN
```

- Access token: short-lived (15 min default)
- Refresh token: longer-lived (7 days default)
- Passwords: bcrypt via `passlib`

## Testing

- Use `pytest` + `pytest-asyncio` + `httpx.AsyncClient`
- Test DB: separate PostgreSQL database, created/torn down per test session
- Use factory fixtures for common entities (users, spots, cars, reservations)
- **Availability resolution** must have exhaustive unit tests covering all combinations of schedules, overrides, and reservations
- Test PII visibility: assert phone/plate never leak in public endpoints
- Test cascading cancellation on spot rejection/deactivation

## Common Commands

```bash
# Run the app
uvicorn app.main:app --reload

# Run migrations
alembic upgrade head

# Create a new migration
alembic revision --autogenerate -m "description"

# Run tests
pytest -v

# Run tests with coverage
pytest --cov=app --cov-report=term-missing
```
