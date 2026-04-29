from __future__ import annotations

import argparse
import threading
import time
from dataclasses import asdict
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from .config import DEFAULT_HOST, DEFAULT_PORT, TASK_TIMEOUT_SECONDS
from .models import ClientInfo, Task, from_json_bytes, new_id, to_json_bytes, utc_now


class ServiceState:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.clients: dict[str, ClientInfo] = {}
        self.tasks: dict[str, Task] = {}
        self.pending_by_client: dict[str, list[str]] = {}

    def register_client(self, payload: dict) -> dict:
        client = ClientInfo(
            client_id=payload["client_id"],
            hostname=payload["hostname"],
            username=payload["username"],
            platform=payload["platform"],
            version=payload.get("version", "1.0"),
            allow_dirs=payload.get("allow_dirs", []),
        )
        with self._lock:
            self.clients[client.client_id] = client
            self.pending_by_client.setdefault(client.client_id, [])
        return {"ok": True, "client": asdict(client)}

    def heartbeat(self, payload: dict) -> dict:
        client_id = payload["client_id"]
        with self._lock:
            client = self.clients.get(client_id)
            if client is None:
                return {"ok": False, "error": "client_not_registered"}
            client.last_seen = utc_now()
            client.status = "online"
        return {"ok": True, "server_time": utc_now()}

    def list_clients(self) -> dict:
        now = datetime.now(timezone.utc)
        with self._lock:
            clients = []
            for client in self.clients.values():
                last_seen = datetime.fromisoformat(client.last_seen)
                if (now - last_seen).total_seconds() > TASK_TIMEOUT_SECONDS * 2:
                    client.status = "stale"
                clients.append(asdict(client))
        return {"ok": True, "clients": clients}

    def submit_task(self, payload: dict) -> dict:
        client_id = payload["client_id"]
        with self._lock:
            if client_id not in self.clients:
                return {"ok": False, "error": "unknown_client"}
            task = Task(
                task_id=new_id("task"),
                client_id=client_id,
                action=payload["action"],
                payload=payload.get("payload", {}),
            )
            self.tasks[task.task_id] = task
            self.pending_by_client.setdefault(client_id, []).append(task.task_id)
        return {"ok": True, "task": asdict(task)}

    def next_task(self, client_id: str) -> dict:
        with self._lock:
            queue = self.pending_by_client.get(client_id, [])
            if not queue:
                return {"ok": True, "task": None}
            task_id = queue.pop(0)
            task = self.tasks[task_id]
            task.status = "dispatched"
        return {"ok": True, "task": asdict(task)}

    def complete_task(self, payload: dict) -> dict:
        task_id = payload["task_id"]
        with self._lock:
            task = self.tasks.get(task_id)
            if task is None:
                return {"ok": False, "error": "unknown_task"}
            task.status = payload.get("status", "completed")
            task.result = payload.get("result", {})
        return {"ok": True}

    def get_task(self, task_id: str) -> dict:
        with self._lock:
            task = self.tasks.get(task_id)
            if task is None:
                return {"ok": False, "error": "unknown_task"}
            return {"ok": True, "task": asdict(task)}


STATE = ServiceState()


class ServiceHandler(BaseHTTPRequestHandler):
    server_version = "SafeRemoteService/1.0"

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/clients":
            self._send_json(HTTPStatus.OK, STATE.list_clients())
            return
        if parsed.path == "/tasks":
            task_id = parse_qs(parsed.query).get("task_id", [None])[0]
            if not task_id:
                self._send_json(HTTPStatus.BAD_REQUEST, {"ok": False, "error": "missing_task_id"})
                return
            result = STATE.get_task(task_id)
            self._send_json(HTTPStatus.OK if result["ok"] else HTTPStatus.NOT_FOUND, result)
            return
        if parsed.path == "/client/task":
            client_id = parse_qs(parsed.query).get("client_id", [None])[0]
            if not client_id:
                self._send_json(HTTPStatus.BAD_REQUEST, {"ok": False, "error": "missing_client_id"})
                return
            self._send_json(HTTPStatus.OK, STATE.next_task(client_id))
            return
        self._send_json(HTTPStatus.NOT_FOUND, {"ok": False, "error": "not_found"})

    def do_POST(self) -> None:
        payload = from_json_bytes(self.rfile.read(int(self.headers.get("Content-Length", "0"))))
        if self.path == "/register":
            self._send_json(HTTPStatus.OK, STATE.register_client(payload))
            return
        if self.path == "/heartbeat":
            result = STATE.heartbeat(payload)
            self._send_json(HTTPStatus.OK if result["ok"] else HTTPStatus.BAD_REQUEST, result)
            return
        if self.path == "/tasks":
            result = STATE.submit_task(payload)
            self._send_json(HTTPStatus.OK if result["ok"] else HTTPStatus.BAD_REQUEST, result)
            return
        if self.path == "/client/task-result":
            result = STATE.complete_task(payload)
            self._send_json(HTTPStatus.OK if result["ok"] else HTTPStatus.BAD_REQUEST, result)
            return
        self._send_json(HTTPStatus.NOT_FOUND, {"ok": False, "error": "not_found"})

    def log_message(self, format: str, *args) -> None:
        return

    def _send_json(self, status: HTTPStatus, payload: dict) -> None:
        body = to_json_bytes(payload)
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main() -> None:
    parser = argparse.ArgumentParser(description="Safe remote service")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    args = parser.parse_args()

    server = ThreadingHTTPServer((args.host, args.port), ServiceHandler)
    print(f"service listening on http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
