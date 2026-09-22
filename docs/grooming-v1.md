# Parking Spot Marketplace — Grooming v1.2

**Stack:** FastAPI · PostgreSQL · SQLAlchemy 2.x (async) · Pydantic v2 · Alembic · JWT  
**Phase:** MVP / V1  
**Updated:** 2026-09-22

---

## Goal & Scope

**Problem:** All parking spots in a residential complex are privately owned. There is no guest or free parking. Owners occasionally have their spot free — neighbours have no way to discover or temporarily use it. When a car overstays, the owner has no way to contact the driver.

**V1 Goal:** A web-only platform where (1) owners register their spot(s) and define availability, (2) any resident can browse free spots and reserve one in 30-min increments choosing which of their registered cars they'll be driving, (3) an owner whose spot is still occupied can look up the car plate and call the driver, and (4) an admin approves spots before they go live.

**Out of scope for V1:** Mobile app, payments, push/email notifications, spot photos, reviews.

---

## Roles

Three roles stored as an enum on the `users` table (`role: DRIVER | OWNER | ADMIN`, default `DRIVER`).

- **DRIVER** — can browse spots and make reservations
- **OWNER** — can also register spots, define availability, see driver contact info on their reservations
- **ADMIN** — full read access to all data; can approve/reject spots and cancel reservations. Cannot self-assign; first admin seeded via DB script.

FastAPI dependency chain: `get_current_user` → `require_owner` → `require_admin`

---

## Spot Approval State Machine

```
[Owner submits] → PENDING → (Admin approves) → APPROVED
                         → (Admin rejects)  → REJECTED  ← owner can resubmit → PENDING
APPROVED → (Owner deactivates) → INACTIVE
APPROVED → (Admin deactivates) → INACTIVE
```

- Only `APPROVED` spots appear in `GET /spots/available`
- On `REJECTED` or `INACTIVE`: all future `CONFIRMED` reservations → `CANCELLED_BY_ADMIN`
- Owner can update a `REJECTED` spot (resets to `PENDING` for re-review)

---

## User Stories — V1

| ID | Title | Priority | Notes |
|----|-------|----------|-------|
| US-001 | User registration & login | must | email + password + phone_number (E.164); JWT pair |
| US-010 | Driver manages their cars | must | plate + nickname; soft-delete; default car |
| US-002 | Owner registers a parking spot | must | goes to PENDING; unique label per complex |
| US-003 | Owner sets a recurring availability schedule | must | day_of_week + time range |
| US-004 | Owner overrides availability for a specific window | must | FREE \| BUSY; always trump schedule |
| US-005 | Driver browses available spots | must | only APPROVED spots; no auth needed |
| US-006 | Driver makes a reservation with a selected car | must | requires car_id; 30-min alignment; no overlap |
| US-007 | Driver cancels a reservation | must | up to 15 min before slot |
| US-008 | Owner sees reservations incl. car plate & driver contact | must | PII only to spot owner |
| US-009 | Owner cancels a reservation on their spot | should | status → CANCELLED_BY_OWNER |
| US-011 | Admin approves or rejects a spot | must | approve → APPROVED; reject requires reason |
| US-012 | Admin views all reservations | must | read-only audit; includes PII; filterable/paginated |

---

## Data Model

### users (updated v1.1, v1.2)
| Column | Type | Notes |
|--------|------|-------|
| id | uuid PK | |
| email | varchar(255) | unique |
| password_hash | varchar | bcrypt |
| full_name | varchar(100) | |
| apartment_number | varchar(20) | |
| phone_number | varchar(20) | **NEW v1.1** E.164, required |
| role | enum | **NEW v1.2** DRIVER\|OWNER\|ADMIN, default DRIVER |
| is_active | boolean | default true |
| created_at | timestamptz | |

### user_cars (new v1.1)
| Column | Type | Notes |
|--------|------|-------|
| id | uuid PK | |
| user_id | uuid FK | → users.id, ON DELETE CASCADE |
| plate | varchar(20) | uppercase, trimmed; unique per user |
| nickname | varchar(50) | optional |
| is_default | boolean | at most one true per user |
| is_active | boolean | soft-delete; kept in reservation history |
| created_at | timestamptz | |

### parking_spots (updated v1.2)
| Column | Type | Notes |
|--------|------|-------|
| id | uuid PK | |
| owner_id | uuid FK | → users.id |
| label | varchar(50) | unique per complex |
| description | text | |
| status | enum | **NEW v1.2** PENDING\|APPROVED\|REJECTED\|INACTIVE, default PENDING |
| rejection_reason | text | **NEW v1.2** null unless REJECTED |
| approved_at | timestamptz | **NEW v1.2** null until approved |
| is_active | boolean | default true |
| created_at | timestamptz | |

### availability_schedules
| Column | Type | Notes |
|--------|------|-------|
| id | uuid PK | |
| spot_id | uuid FK | → parking_spots.id |
| day_of_week | smallint | 0=Mon…6=Sun |
| start_time | time | |
| end_time | time | must be > start_time |

### availability_overrides
| Column | Type | Notes |
|--------|------|-------|
| id | uuid PK | |
| spot_id | uuid FK | → parking_spots.id |
| override_type | enum | FREE \| BUSY |
| starts_at | timestamptz | |
| ends_at | timestamptz | |
| reason | text | optional |
| created_at | timestamptz | |

### reservations (updated v1.1, v1.2)
| Column | Type | Notes |
|--------|------|-------|
| id | uuid PK | |
| spot_id | uuid FK | → parking_spots.id |
| user_id | uuid FK | → users.id (reserver) |
| car_id | uuid FK | **NEW v1.1** → user_cars.id, SET NULL on soft-delete |
| starts_at | timestamptz | must align to :00 or :30 |
| ends_at | timestamptz | starts_at + N×30min |
| status | enum | CONFIRMED\|CANCELLED\|CANCELLED_BY_OWNER\|**CANCELLED_BY_ADMIN** (v1.2) |
| cancellation_reason | text | |
| created_at | timestamptz | |

**Key DB constraint:** PostgreSQL exclusion constraint on `tstzrange(starts_at, ends_at)` with `&&` operator (`btree_gist` extension required) — prevents overlapping CONFIRMED reservations for the same spot_id at the DB level.

**Privacy rule:** `phone_number` and car `plate` are PII — only exposed in owner-facing `GET /spots/{id}/reservations` and admin `GET /admin/reservations`. Never in public browse endpoints.

---

## API Surface

### Auth
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | /auth/register | — | Create account (includes phone_number) |
| POST | /auth/login | — | Get JWT pair |
| POST | /auth/refresh | Refresh token | Rotate access token |

### Profile & Cars
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| PUT | /users/me | ✓ | Update profile (phone, name, apartment) |
| GET | /users/me/cars | ✓ | List own cars |
| POST | /users/me/cars | ✓ | Add a car |
| PUT | /users/me/cars/{id} | ✓ | Update nickname / set default |
| DELETE | /users/me/cars/{id} | ✓ | Soft-delete car |

### Spots — Public
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | /spots/available | — | Browse free APPROVED spots for a window |

### Spots — Owner
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | /spots/mine | ✓ Owner | Owner's spots |
| POST | /spots | ✓ | Register spot (→ PENDING) |
| PUT | /spots/{id} | ✓ Owner | Update spot (REJECTED → resets to PENDING) |
| DELETE | /spots/{id} | ✓ Owner | Deactivate spot (→ INACTIVE, cascade cancel) |
| GET | /spots/{id}/schedules | ✓ Owner | List recurring schedules |
| POST | /spots/{id}/schedules | ✓ Owner | Add schedule entry |
| DELETE | /spots/{id}/schedules/{sid} | ✓ Owner | Remove schedule |
| GET | /spots/{id}/overrides | ✓ Owner | List overrides |
| POST | /spots/{id}/overrides | ✓ Owner | Add FREE/BUSY override |
| DELETE | /spots/{id}/overrides/{oid} | ✓ Owner | Remove override |
| GET | /spots/{id}/reservations | ✓ Owner | Reservations incl. driver phone + plate |

### Reservations
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | /reservations/mine | ✓ | Driver's own reservations |
| POST | /reservations | ✓ | Book a slot (requires car_id) |
| DELETE | /reservations/{id} | ✓ Driver | Driver cancels |
| DELETE | /reservations/{id}/owner-cancel | ✓ Owner | Owner cancels |

### Admin
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | /admin/spots | ✓ Admin | All spots, filterable by ?status= |
| PATCH | /admin/spots/{id}/approve | ✓ Admin | Approve spot → APPROVED, sets approved_at |
| PATCH | /admin/spots/{id}/reject | ✓ Admin | Reject spot → REJECTED, requires rejection_reason, cascades cancel |
| GET | /admin/reservations | ✓ Admin | All reservations with PII, filters (?spot_id=, ?from=, ?to=, ?status=), paginated |

---

## Availability Resolution Logic

A spot is available in window [T₁, T₂] when:
1. Spot is **active** AND status is **APPROVED**
2. A recurring schedule covers the window OR a **FREE override** covers it
3. No **BUSY override** overlaps [T₁, T₂]
4. No **CONFIRMED reservation** overlaps [T₁, T₂]

Overrides always win over schedules. This logic lives in a single service function and is the most critical piece of business logic to unit-test exhaustively.

---

## Architecture

```
Browser (SPA or SSR)
  ↕  HTTP/JSON · CORS
FastAPI  · Pydantic v2 · JWT middleware · SQLAlchemy 2.x (async)
  ↕  asyncpg / psycopg3
PostgreSQL  · tstzrange exclusion constraint · btree_gist · Alembic
```

Project layout: `app/routers/` · `app/models/` · `app/schemas/` · `app/services/` · `app/core/`

Business logic stays in **services**. Routers stay thin. Schemas never leak phone numbers or plates to the wrong caller. Admin router protected by `require_admin` dependency.

---

## Open Questions

1. **Who can sign up?** Open registration, invite-link only, or admin approval per user?
2. **Max reservation length?** A cap prevents spot hoarding — e.g. 4 hours.
3. **Multiple simultaneous reservations per driver?** Almost certainly no, but define it.
4. **BUSY override over an existing reservation?** Auto-cancel or block the override?
5. **Timezone:** All Europe/Bucharest assumed. Store UTC in DB, display in local time on frontend?
6. **Frontend stack?** Plain HTML/JS, Vue, React? Affects CORS config.
7. **No-show policy?** Any consequence for reserving and not showing up?
8. **Plate format validation?** Strict Romanian format or accept any string?
9. **Can an admin also be an owner/driver?** Or is admin a pure admin-only role?

---

## Suggested Build Order (5 Sprints)

**Sprint 1 — Foundation:** DB schema (users + user_cars), auth endpoints, profile update, cars CRUD

**Sprint 2 — Admin & Spot Approval:** Role enum, spot submission flow (PENDING), admin approval/rejection endpoints, cascading cancellation on rejection

**Sprint 3 — Availability:** availability_schedules, availability_overrides, resolution service + exhaustive tests, `GET /spots/available` (APPROVED only)

**Sprint 4 — Reservations:** reservations table + tstzrange exclusion constraint, booking (with car_id), owner view with PII, cancellation endpoints, admin reservation audit

**Sprint 5 — Frontend & Polish:** Login/register, cars management, owner dashboard, driver browse+book flow, my reservations, CORS/error handling, OpenAPI docs review
