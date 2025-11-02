from fastapi import FastAPI
from .database import engine, Base
from .routers import users, auth

# Create tables on startup
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="bahyway Users Service",
    description="Manages user profiles and authentication."
)

app.include_router(auth.router)
app.include_router(users.router)
