from __future__ import annotations

import argparse
import getpass
import os
import platform
import socket
import sys
import time
from pathlib import Path
from urllib import error, parse, request

from .config import (
    CLIENT_STORAGE_DIR,
    DEFAULT_HEARTBEAT_INTERVAL,
    DEFAULT_MAX_FILE_SIZE,
    DEFAULT_POLL_INTERVAL,
    DEFAULT_SERVICE_URL,
)
from .models import decode_file_bytes, encode_file_bytes, from_json_bytes, to_json_bytes


def post_json(base_url: str, path: str, payload: dict) -> dict:
    req = request.Request(
        f"{base_url}{path}",
        data=to_json_bytes(payload),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with request.urlopen(req, timeout=15) as resp:
        return from_json_bytes(resp.read())


def get_json(url: str) -> dict:
    with request.urlopen(url, timeout=15) as resp:
        return from_json_bytes(resp.read())


class SafeFileAgent:
    def __init__(self, service_url: str, client_id: str, allow_dirs: list[Path], max_file_size: int) -> None:
        self.service_url = service_url.rstrip("/")
        self.client_id = client_id
        self.allow_dirs = [path.resolve() for path in allow_dirs]
        self.max_file_size = max_file_size
        self.storage_dir = CLIENT_STORAGE_DIR.resolve()
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def register(self) -> None:
        payload = {
            "client_id": self.client_id,
            "hostname": socket.gethostname(),
            "username": getpass.getuser(),
            "platform": platform.platform(),
            "version": "1.0",
            "allow_dirs": [str(path) for path in self.allow_dirs],
        }
        response = post_json(self.service_url, "/register", payload)
        if not response.get("ok"):
            raise RuntimeError(f"register failed: {response}")

    def heartbeat(self) -> None:
        response = post_json(self.service_url, "/heartbeat", {"client_id": self.client_id})
        if not response.get("ok"):
            raise RuntimeError(f"heartbeat failed: {response}")

    def poll_once(self) -> None:
        query = parse.urlencode({"client_id": self.client_id})
        task_response = get_json(f"{self.service_url}/client/task?{query}")
        task = task_response.get("task")
        if not task:
            return
        result = self.execute_task(task["action"], task["payload"])
        status = "completed" if result.get("ok") else "failed"
        post_json(
            self.service_url,
            "/client/task-result",
            {"task_id": task["task_id"], "status": status, "result": result},
        )

    def execute_task(self, action: str, payload: dict) -> dict:
        try:
            if action == "list_dir":
                return self.list_dir(payload["path"])
            if action == "download_file":
                return self.download_file(payload["path"])
            if action == "upload_file":
                return self.upload_file(payload["path"], payload["content_b64"])
            return {"ok": False, "error": f"unsupported_action:{action}"}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def list_dir(self, requested_path: str) -> dict:
        target = self.resolve_allowed_path(requested_path)
        entries = []
        for child in sorted(target.iterdir(), key=lambda item: (not item.is_dir(), item.name.lower())):
            stat = child.stat()
            entries.append(
                {
                    "name": child.name,
                    "is_dir": child.is_dir(),
                    "size": stat.st_size,
                }
            )
        return {"ok": True, "path": str(target), "entries": entries}

    def download_file(self, requested_path: str) -> dict:
        target = self.resolve_allowed_path(requested_path)
        if not target.is_file():
            raise FileNotFoundError(f"not a file: {target}")
        data = target.read_bytes()
        if len(data) > self.max_file_size:
            raise ValueError(f"file too large: {len(data)} bytes")
        return {
            "ok": True,
            "path": str(target),
            "size": len(data),
            "content_b64": encode_file_bytes(data),
        }

    def upload_file(self, requested_path: str, content_b64: str) -> dict:
        target = self.resolve_allowed_path(requested_path, must_exist=False)
        data = decode_file_bytes(content_b64)
        if len(data) > self.max_file_size:
            raise ValueError(f"file too large: {len(data)} bytes")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        return {"ok": True, "path": str(target), "size": len(data)}

    def resolve_allowed_path(self, requested_path: str, must_exist: bool = True) -> Path:
        normalized = requested_path or "."
        for base in self.allow_dirs:
            candidate = (base / normalized).resolve()
            if self.is_relative_to(candidate, base):
                if must_exist and not candidate.exists():
                    raise FileNotFoundError(f"path not found: {candidate}")
                return candidate
        raise PermissionError(f"path outside allowlist: {requested_path}")

    @staticmethod
    def is_relative_to(candidate: Path, base: Path) -> bool:
        try:
            candidate.relative_to(base)
            return True
        except ValueError:
            return False


def main() -> None:
    parser = argparse.ArgumentParser(description="Safe remote file client")
    parser.add_argument("--service-url", default=DEFAULT_SERVICE_URL)
    parser.add_argument("--client-id", required=True)
    parser.add_argument("--allow-dir", action="append", required=True, help="Allowlisted directory")
    parser.add_argument("--max-file-size", type=int, default=DEFAULT_MAX_FILE_SIZE)
    parser.add_argument("--poll-interval", type=int, default=DEFAULT_POLL_INTERVAL)
    parser.add_argument("--heartbeat-interval", type=int, default=DEFAULT_HEARTBEAT_INTERVAL)
    args = parser.parse_args()

    allow_dirs = [Path(path) for path in args.allow_dir]
    agent = SafeFileAgent(args.service_url, args.client_id, allow_dirs, args.max_file_size)
    agent.register()
    print(f"client {args.client_id} connected to {args.service_url}")

    last_heartbeat = 0.0
    while True:
        now = time.time()
        try:
            if now - last_heartbeat >= args.heartbeat_interval:
                agent.heartbeat()
                last_heartbeat = now
            agent.poll_once()
        except error.URLError as exc:
            print(f"network error: {exc}", file=sys.stderr)
        except Exception as exc:
            print(f"client error: {exc}", file=sys.stderr)
        time.sleep(args.poll_interval)


if __name__ == "__main__":
    main()
