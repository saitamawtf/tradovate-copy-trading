import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from .api import accounts, groups, oauth, stats, ws
from .config import get_settings
from .copy.engine import CopyEngine
from .db import SessionLocal, init_db
from .models import CopyGroup, User

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
)
log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    async with SessionLocal() as session:
        existing = (
            await session.execute(select(User).where(User.id == 1))
        ).scalar_one_or_none()
        if existing is None:
            session.add(User(id=1, email="owner@local"))
            await session.commit()

    async def on_event(group_id: int, payload: dict) -> None:
        await ws.hub.broadcast(payload)

    engine = CopyEngine(SessionLocal, event_callback=on_event)
    app.state.engine = engine

    async with SessionLocal() as session:
        active_groups = (
            (await session.execute(select(CopyGroup).where(CopyGroup.is_active == True)))  # noqa: E712
            .scalars()
            .all()
        )
    for g in active_groups:
        try:
            await engine.start_group(g.id)
        except Exception as e:  # noqa: BLE001
            log.warning("could not resume group %s: %s", g.id, e)

    try:
        yield
    finally:
        await engine.shutdown()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(accounts.router)
    app.include_router(groups.router)
    app.include_router(stats.router)
    app.include_router(ws.router)
    app.include_router(oauth.router)

    @app.get("/api/health")
    async def health():
        return {"ok": True, "app": settings.app_name}

    return app


app = create_app()
