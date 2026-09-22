from fastapi import FastAPI

from parking_marketplace_backend.api.routes.auth import router as auth_router
from parking_marketplace_backend.api.routes.users import router as users_router

app = FastAPI()


@app.get("/")
def read_root():
    return {"message": "Hello, World!"}


@app.get("/health")
def health_check():
    return {"status": "ok"}


app.include_router(auth_router, prefix="/api/v1")
app.include_router(users_router, prefix="/api/v1")