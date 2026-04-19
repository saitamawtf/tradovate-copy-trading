from ..schemas import ProjectXCredentials, TradovateCredentials
from .base import BrokerAdapter
from .projectx import ProjectXAdapter
from .tradovate import TradovateAdapter


def build_adapter(broker: str, env: str, credentials: dict) -> BrokerAdapter:
    if broker == "tradovate":
        # OAuth path: credentials contain access_token instead of password
        if credentials.get("_auth_type") == "oauth" or credentials.get("access_token"):
            return TradovateAdapter(
                access_token=credentials["access_token"], env=env
            )
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
