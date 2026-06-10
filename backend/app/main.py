from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from app.api.ai import router as ai_router
from app.api.auth import router as auth_router
from app.api.classification import router as classification_router
from app.api.emails import router as emails_router
from app.api.followups import router as followups_router
from app.api.processing import router as processing_router
from app.api.replies import router as replies_router
from app.api.health import router as health_router
from app.api.task_extraction import router as task_extraction_router
from app.api.tasks import router as tasks_router
from app.api.users import router as users_router
from app.core.config import get_settings

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    debug=settings.debug,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.session_secret_key,
    same_site="lax",
    https_only=settings.app_env != "development",
)

app.include_router(health_router, prefix="/api")
app.include_router(ai_router, prefix="/api")
app.include_router(auth_router, prefix="/api")
app.include_router(users_router, prefix="/api")
app.include_router(processing_router, prefix="/api")
app.include_router(classification_router, prefix="/api")
app.include_router(task_extraction_router, prefix="/api")
app.include_router(replies_router, prefix="/api")
app.include_router(emails_router, prefix="/api")
app.include_router(tasks_router, prefix="/api")
app.include_router(followups_router, prefix="/api")
