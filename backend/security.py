import json
from typing import Any

from cryptography.fernet import Fernet

from .config import get_settings


def _cipher() -> Fernet:
    return Fernet(get_settings().fernet_key.encode())


def encrypt(payload: dict[str, Any]) -> bytes:
    return _cipher().encrypt(json.dumps(payload).encode())


def decrypt(blob: bytes) -> dict[str, Any]:
    return json.loads(_cipher().decrypt(blob).decode())


def generate_key() -> str:
    return Fernet.generate_key().decode()
