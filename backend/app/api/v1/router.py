from fastapi import APIRouter

from app.api.v1.endpoints.applications import router as applications_router
from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.endpoints.jobs import router as jobs_router
from app.api.v1.endpoints.resumes import router as resumes_router
from app.api.v1.endpoints.users import router as users_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(users_router)
api_router.include_router(jobs_router)
api_router.include_router(resumes_router)
api_router.include_router(applications_router)
