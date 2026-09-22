# Parking Marketplace Backend

Backend API for a parking spot marketplace that allows users to share, discover, and reserve parking spaces.

## About the Project

Parking Marketplace is a web platform designed to connect parking spot owners with people looking for available parking spaces.

The platform will allow users to:

* List and manage their parking spots.
* Define when their parking spots are available.
* Discover parking spots available for booking.
* Reserve parking spaces for specific time periods.
* Manage their reservations.
* Manage their profile and account.

The project is being developed with a React frontend and a Python backend. The backend is the primary focus of the initial development phase.


## Tech Stack

### Backend

| Technology        | Purpose                              |
| ----------------- | ------------------------------------ |
| Python            | Backend programming language         |
| FastAPI           | Web framework for building REST APIs |
| PostgreSQL        | Relational database                  |
| SQLAlchemy 2.x    | ORM and database interaction         |
| Pydantic          | Data validation and serialization    |
| pydantic-settings | Application configuration            |
| Alembic           | Database migrations                  |
| pytest            | Automated testing                    |
| HTTPX             | API testing                          |
| Ruff              | Linting and code quality             |
| Docker            | Containerization                     |

### Frontend

The frontend will be developed separately using:

* React
* Modern frontend architecture
* REST API integration

The frontend implementation will follow the backend API development.

## Architecture

The backend is designed with a separation of concerns between API routes, business logic, and database access.

The main layers are:

```text
parking_marketplace_backend/
│
├── app/
│   ├── api/
│   │   └── routes/
│   │
│   ├── core/
│   │   └── configuration.py
│   │
│   ├── db/
│   │   ├── session.py
│   │   └── base.py
│   │
│   ├── models/
│   │
│   ├── schemas/
│   │
│   ├── services/
│   │
│   └── main.py
│
├── tests/
│
├── alembic/
│
├── .env.example
├── .gitignore
├── pyproject.toml
├── requirements.txt
└── README.md
```

The structure may evolve as the project grows.

### Architectural Principles

* Keep API routes focused on handling HTTP requests and responses.
* Keep business logic in dedicated services.
* Separate database models from API schemas.
* Use database migrations to manage schema changes.
* Keep configuration separate from application logic.
* Write testable and maintainable code.

## Core Domain Models

The initial domain model includes the following entities:

### User

Represents a platform user.

Potential responsibilities:

* Account management.
* Authentication.
* Managing owned parking spots.
* Creating reservations.

### ParkingSpot

Represents a parking space available on the platform.

Potential attributes:

* Owner.
* Location.
* Description.
* Pricing.
* Status.
* Availability configuration.

### AvailabilityRule

Represents the recurring availability of a parking spot.

The availability system is intended to support:

* Recurring weekly schedules.
* Specific availability periods.
* Exceptions to recurring rules.
* Timezone-aware availability.

### Reservation

Represents a booking made for a parking spot.

Potential responsibilities:

* Connecting a user with a parking spot.
* Defining the reservation time range.
* Tracking reservation status.
* Preventing conflicting reservations.

## Key Business Logic

### Parking Availability

Parking spots may have recurring availability rules, with the possibility of defining exceptions.

For example, a parking spot could be available:

```text
Monday - Friday
18:00 - 08:00
```

Specific dates may override the recurring schedule.

The availability logic should take into account:

* Recurring rules.
* Exceptions.
* Requested reservation period.
* Timezone.
* Existing reservations.

### Reservation Conflicts

The system must prevent overlapping reservations for the same parking spot.

Reservation validation should be handled through:

* Application-level business logic.
* Database transactions.
* PostgreSQL constraints where appropriate.

The goal is to ensure that two users cannot successfully reserve the same parking spot for overlapping periods, including concurrent requests.

## API Development

The API will follow REST principles and expose endpoints for the main platform resources.

Planned endpoint groups include:

```text
/api/v1/users
/api/v1/parking-spots
/api/v1/availability
/api/v1/reservations
```

The exact endpoints and request/response schemas will evolve during development.


## Getting Started

### Prerequisites

Make sure you have the following installed:

* Python 3.12+
* PostgreSQL
* Git
* Docker (optional during initial development)

### Clone the Repository

```bash
git clone <repository-url>
cd parking_marketplace_backend
```

### Create a Virtual Environment

#### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
```

#### Windows

```bash
python -m venv .venv
.venv\Scripts\activate
```

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Configure Environment Variables

Create a `.env` file based on `.env.example`.

Example:

```env
APP_NAME=Parking Marketplace API
ENVIRONMENT=development

DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/parking_marketplace

SECRET_KEY=change-me
```

Do not commit secrets or environment-specific credentials to the repository.

### Run the Development Server

```bash
uvicorn app.main:app --reload
```

The API will be available at:

```text
http://127.0.0.1:8000
```

### API Documentation

FastAPI provides interactive API documentation.

Swagger UI:

```text
http://127.0.0.1:8000/docs
```

ReDoc:

```text
http://127.0.0.1:8000/redoc
```

## Running Tests

Run the test suite with:

```bash
pytest
```

For more detailed output:

```bash
pytest -v
```

## Database Migrations

Create a migration after changing database models:

```bash
alembic revision --autogenerate -m "describe your change"
```

Apply migrations:

```bash
alembic upgrade head
```

## Future Improvements

Potential future features include:

* Advanced parking spot search and filtering.
* Location-based discovery.
* Improved availability management.
* Notifications.
* Reviews and ratings.
* Payment integration.
* Administrative tools.
* Analytics.
* Mobile-friendly frontend experience.

## License

This project is currently intended for learning and personal development purposes.

License information will be added when the project is ready for broader distribution.
