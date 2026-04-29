from __future__ import annotations

import base64
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_id(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:12]}"


@dataclass
class ClientInfo:
    client_id: str
    hostname: str
    username: str
    platform: str
    version: str
    allow_dirs: list[str]
    last_seen: str = field(default_factory=utc_now)
    status: str = "online"


@dataclass
class Task:
    task_id: str
    client_id: str
    action: str
    payload: dict[str, Any]
    created_at: str = field(default_factory=utc_now)
    status: str = "queued"
    result: dict[str, Any] | None = None


def to_json_bytes(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, ensure_ascii=True).encode("utf-8")


def from_json_bytes(payload: bytes) -> dict[str, Any]:
    if not payload:
        return {}
    return json.loads(payload.decode("utf-8"))


def encode_file_bytes(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def decode_file_bytes(data: str) -> bytes:
    return base64.b64decode(data.encode("ascii"))


def dataclass_dict(instance: Any) -> dict[str, Any]:
    return asdict(instance)
