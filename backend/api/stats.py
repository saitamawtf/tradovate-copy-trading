from datetime import date, datetime, time, timezone

from fastapi import APIRouter, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import BrokerAccount, CopyGroup, TradeLog
from .deps import SessionDep, UserDep

router = APIRouter(prefix="/api/stats", tags=["stats"])


@router.get("")
async def dashboard_stats(
    request: Request,
    session: AsyncSession = SessionDep,
    user_id: int = UserDep,
):
    engine = request.app.state.engine

    accounts_total = (
        await session.execute(
            select(func.count(BrokerAccount.id)).where(BrokerAccount.user_id == user_id)
        )
    ).scalar_one()

    followers_by_status: dict[str, int] = {}
    rows = (
        await session.execute(
            select(BrokerAccount.status, func.count(BrokerAccount.id))
            .where(BrokerAccount.user_id == user_id)
            .group_by(BrokerAccount.status)
        )
    ).all()
    for status, count in rows:
        followers_by_status[status] = count

    groups_total = (
        await session.execute(
            select(func.count(CopyGroup.id)).where(CopyGroup.user_id == user_id)
        )
    ).scalar_one()
    groups_active = (
        await session.execute(
            select(func.count(CopyGroup.id)).where(
                CopyGroup.user_id == user_id, CopyGroup.is_active.is_(True)
            )
        )
    ).scalar_one()

    start_of_day = datetime.combine(date.today(), time.min, tzinfo=timezone.utc)
    copies_today = (
        await session.execute(
            select(func.count(TradeLog.id)).where(TradeLog.ts >= start_of_day)
        )
    ).scalar_one()
    fails_today = (
        await session.execute(
            select(func.count(TradeLog.id)).where(
                TradeLog.ts >= start_of_day, TradeLog.event_type.like("%:fail")
            )
        )
    ).scalar_one()

    running_group_ids = [
        gid for gid in range(1, groups_total + 1) if engine.is_running(gid)
    ]

    return {
        "accounts_total": accounts_total,
        "accounts_by_status": followers_by_status,
        "groups_total": groups_total,
        "groups_active": groups_active,
        "running_group_ids": running_group_ids,
        "copies_today": copies_today,
        "fails_today": fails_today,
        "fill_rate": round(
            100 * (copies_today - fails_today) / copies_today, 2
        )
        if copies_today
        else 100.0,
    }
