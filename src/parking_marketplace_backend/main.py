from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from parking_marketplace_backend.api.routes.admin_reservations import router as admin_reservations_router
from parking_marketplace_backend.api.routes.admin_spots import router as admin_spots_router
from parking_marketplace_backend.api.routes.auth import router as auth_router
from parking_marketplace_backend.api.routes.cars import router as cars_router
from parking_marketplace_backend.api.routes.overrides import router as overrides_router
from parking_marketplace_backend.api.routes.reservations import router as reservations_router
from parking_marketplace_backend.api.routes.schedules import router as schedules_router
from parking_marketplace_backend.api.routes.spot_reservations import router as spot_reservations_router
from parking_marketplace_backend.api.routes.users import router as users_router
from parking_marketplace_backend.api.routes.spots import router as spots_router

app = FastAPI()

# Local dev origins for the React frontend (Vite's default port, plus common alternates).
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root():
    return {"message": "Hello, World!"}


@app.get("/health")
def health_check():
    return {"status": "ok"}


app.include_router(admin_reservations_router, prefix="/api/v1")
app.include_router(admin_spots_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")
app.include_router(cars_router, prefix="/api/v1")
app.include_router(overrides_router, prefix="/api/v1")
app.include_router(reservations_router, prefix="/api/v1")
app.include_router(schedules_router, prefix="/api/v1")
app.include_router(spot_reservations_router, prefix="/api/v1")
app.include_router(spots_router, prefix="/api/v1")
app.include_router(users_router, prefix="/api/v1")