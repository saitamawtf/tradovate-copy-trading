from ..schemas import ProjectXCredentials, TradovateCredentials
from .base import BrokerAdapter
from .projectx import ProjectXAdapter
from .tradovate import TradovateAdapter


def build_adapter(broker: str, env: str, credentials: dict) -> BrokerAdapter:
    if broker == "tradovate":
        c = TradovateCredentials.model_validate(credentials)
        return TradovateAdapter(
            name=c.name, password=c.password, cid=c.cid, sec=c.sec, env=env
        )
    if broker == "projectx":
        c = ProjectXCredentials.model_validate(credentials)
        return ProjectXAdapter(
            username=c.username, api_key=c.api_key, base_url=c.base_url
        )
    raise ValueError(f"unknown broker: {broker}")
