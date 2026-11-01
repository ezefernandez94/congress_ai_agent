from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.dashboard import collect_dashboard
from app.web.auth import get_scoped_db, require_web_user
from app.web.rendering import render

router = APIRouter(tags=["web-dashboard"], dependencies=[Depends(require_web_user)])


@router.get("/")
async def dashboard(request: Request, db: AsyncSession = Depends(get_scoped_db)):
    return render(request, "dashboard.html", {"d": await collect_dashboard(db)})
