from datetime import datetime

from fastapi import APIRouter, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..brokers.factory import build_adapter
from ..models import BrokerAccount
from ..schemas import AccountCreate, AccountOut, AccountTestResult
from ..security import decrypt, encrypt
from .deps import SessionDep, UserDep

router = APIRouter(prefix="/api/accounts", tags=["accounts"])


def _to_out(acc: BrokerAccount) -> AccountOut:
    return AccountOut(
        id=acc.id,
        broker=acc.broker,  # type: ignore[arg-type]
        label=acc.label,
        env=acc.env,
        external_account_id=acc.external_account_id,
        status=acc.status,
        last_seen_at=acc.last_seen_at,
    )


@router.get("", response_model=list[AccountOut])
async def list_accounts(session: AsyncSession = SessionDep, user_id: int = UserDep):
    rows = (
        (
            await session.execute(
                select(BrokerAccount).where(BrokerAccount.user_id == user_id)
            )
        )
        .scalars()
        .all()
    )
    return [_to_out(r) for r in rows]


@router.post("", response_model=AccountOut)
async def create_account(
    body: AccountCreate,
    session: AsyncSession = SessionDep,
    user_id: int = UserDep,
):
    acc = BrokerAccount(
        user_id=user_id,
        broker=body.broker,
        label=body.label,
        env=body.env,
        credentials_encrypted=encrypt(body.credentials.model_dump()),
        status="new",
    )
    session.add(acc)
    await session.commit()
    await session.refresh(acc)
    return _to_out(acc)


@router.delete("/{account_id}")
async def delete_account(
    account_id: int,
    session: AsyncSession = SessionDep,
    user_id: int = UserDep,
):
    acc = await session.get(BrokerAccount, account_id)
    if not acc or acc.user_id != user_id:
        raise HTTPException(404)
    await session.delete(acc)
    await session.commit()
    return {"ok": True}


@router.post("/{account_id}/test", response_model=AccountTestResult)
async def test_account(
    account_id: int,
    session: AsyncSession = SessionDep,
    user_id: int = UserDep,
):
    acc = await session.get(BrokerAccount, account_id)
    if not acc or acc.user_id != user_id:
        raise HTTPException(404)
    adapter = build_adapter(acc.broker, acc.env, decrypt(acc.credentials_encrypted))
    try:
        await adapter.authenticate()
        accts = await adapter.list_accounts()
        if accts:
            acc.external_account_id = accts[0].id
            acc.status = "ok"
            acc.last_seen_at = datetime.utcnow()
        else:
            acc.status = "no_accounts"
        await session.commit()
        return AccountTestResult(
            ok=True,
            message="authenticated",
            accounts=[
                {"id": a.id, "name": a.name, "balance": a.balance} for a in accts
            ],
        )
    except Exception as e:  # noqa: BLE001
        acc.status = "auth_failed"
        await session.commit()
        return AccountTestResult(ok=False, message=str(e))
    finally:
        await adapter.close()
