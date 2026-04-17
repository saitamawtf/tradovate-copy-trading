from fastapi import APIRouter, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import BrokerAccount, CopyGroup, CopyMapping
from ..schemas import GroupCreate, GroupOut, GroupStatus, MappingOut
from .deps import SessionDep, UserDep

router = APIRouter(prefix="/api/groups", tags=["groups"])


def _to_out(group: CopyGroup) -> GroupOut:
    return GroupOut(
        id=group.id,
        name=group.name,
        leader_account_id=group.leader_account_id,
        is_active=group.is_active,
        mappings=[
            MappingOut(
                id=m.id,
                follower_account_id=m.follower_account_id,
                size_mode=m.size_mode,  # type: ignore[arg-type]
                size_value=m.size_value,
                reverse=m.reverse,
            )
            for m in group.mappings
        ],
    )


@router.get("", response_model=list[GroupOut])
async def list_groups(session: AsyncSession = SessionDep, user_id: int = UserDep):
    rows = (
        (
            await session.execute(
                select(CopyGroup).where(CopyGroup.user_id == user_id)
            )
        )
        .scalars()
        .unique()
        .all()
    )
    return [_to_out(g) for g in rows]


@router.post("", response_model=GroupOut)
async def create_group(
    body: GroupCreate,
    session: AsyncSession = SessionDep,
    user_id: int = UserDep,
):
    leader = await session.get(BrokerAccount, body.leader_account_id)
    if not leader or leader.user_id != user_id:
        raise HTTPException(400, "invalid leader account")
    for m in body.mappings:
        acc = await session.get(BrokerAccount, m.follower_account_id)
        if not acc or acc.user_id != user_id:
            raise HTTPException(400, f"invalid follower account {m.follower_account_id}")
    group = CopyGroup(
        user_id=user_id, name=body.name, leader_account_id=body.leader_account_id
    )
    session.add(group)
    await session.flush()
    for m in body.mappings:
        session.add(
            CopyMapping(
                group_id=group.id,
                follower_account_id=m.follower_account_id,
                size_mode=m.size_mode,
                size_value=m.size_value,
                reverse=m.reverse,
            )
        )
    await session.commit()
    await session.refresh(group)
    return _to_out(group)


@router.delete("/{group_id}")
async def delete_group(
    group_id: int,
    request: Request,
    session: AsyncSession = SessionDep,
    user_id: int = UserDep,
):
    group = await session.get(CopyGroup, group_id)
    if not group or group.user_id != user_id:
        raise HTTPException(404)
    engine = request.app.state.engine
    if engine.is_running(group_id):
        await engine.stop_group(group_id)
    await session.delete(group)
    await session.commit()
    return {"ok": True}


@router.post("/{group_id}/start")
async def start_group(
    group_id: int,
    request: Request,
    session: AsyncSession = SessionDep,
    user_id: int = UserDep,
):
    group = await session.get(CopyGroup, group_id)
    if not group or group.user_id != user_id:
        raise HTTPException(404)
    engine = request.app.state.engine
    if engine.is_running(group_id):
        return {"ok": True, "message": "already running"}
    await engine.start_group(group_id)
    group.is_active = True
    await session.commit()
    return {"ok": True}


@router.post("/{group_id}/stop")
async def stop_group(
    group_id: int,
    request: Request,
    session: AsyncSession = SessionDep,
    user_id: int = UserDep,
):
    group = await session.get(CopyGroup, group_id)
    if not group or group.user_id != user_id:
        raise HTTPException(404)
    engine = request.app.state.engine
    await engine.stop_group(group_id)
    group.is_active = False
    await session.commit()
    return {"ok": True}


@router.get("/{group_id}/status", response_model=GroupStatus)
async def group_status(
    group_id: int,
    request: Request,
    session: AsyncSession = SessionDep,
    user_id: int = UserDep,
):
    group = await session.get(CopyGroup, group_id)
    if not group or group.user_id != user_id:
        raise HTTPException(404)
    engine = request.app.state.engine
    st = engine.status(group_id)
    return GroupStatus(
        id=group_id,
        is_active=st["is_active"],
        leader_connected=st["leader_connected"],
        followers_connected=st["followers_connected"],
        followers_total=st["followers_total"],
        last_events=st["last_events"],
    )
