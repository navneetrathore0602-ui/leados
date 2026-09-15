from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.v1.api import api_router
from app.core.database import engine, SessionLocal
from app.models.base import Base
from app.models.domain import User
from app.core.auth import get_password_hash

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# Initialize DB tables
Base.metadata.create_all(bind=engine)

@app.on_event("startup")
def startup_event():
    db = SessionLocal()
    try:
        admin_email = (settings.LEADOS_ADMIN_EMAIL or "").strip().lower()
        admin_password = (settings.LEADOS_ADMIN_PASSWORD or "").strip()

        if admin_email and admin_password:
            admin_user = db.query(User).filter(User.email == admin_email).first()
            if not admin_user:
                new_admin = User(
                    email=admin_email,
                    hashed_password=get_password_hash(admin_password),
                    role="admin"
                )
                db.add(new_admin)
                db.commit()
    finally:
        db.close()


# Set up CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://zippy-ganache-aee27c.netlify.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API v1 router under /api/v1
app.include_router(api_router, prefix=settings.API_V1_STR)

# Also mount under /api directly for /api/leads and /api/stats
app.include_router(api_router, prefix="/api")

@app.get("/")
def read_root():
    return {"message": "Welcome to LeadOS API"}

@app.get("/health")
def health_check():
    return {"status": "ok"}

