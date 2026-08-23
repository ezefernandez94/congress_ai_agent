"""Every router the web UI contributes, in mount order."""

from fastapi import APIRouter

from app.web.routes.actions import router as actions_router
from app.web.routes.auth import router as auth_router
from app.web.routes.chat import router as chat_router
from app.web.routes.dashboard import router as dashboard_router
from app.web.routes.entities import entity_routers
from app.web.routes.users import router as users_router

# actions_router first: POST /tasks/{id}/complete must be matched before the
# generic POST /tasks/{obj_id} update route the CRUD factory registers.
web_routers: list[APIRouter] = [
    auth_router,
    dashboard_router,
    actions_router,
    users_router,
    chat_router,
    *entity_routers,
]

__all__ = ["web_routers"]
