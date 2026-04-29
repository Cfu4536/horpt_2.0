from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from urllib import parse, request

from .config import DEFAULT_SERVICE_URL, TASK_TIMEOUT_SECONDS
from .models import encode_file_bytes, from_json_bytes, to_json_bytes


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


def wait_for_task(service_url: str, task_id: str, timeout_seconds: int) -> dict:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        query = parse.urlencode({"task_id": task_id})
        task_response = get_json(f"{service_url}/tasks?{query}")
        task = task_response["task"]
        if task["status"] in {"completed", "failed"}:
            return task
        time.sleep(1)
    raise TimeoutError(f"task timed out: {task_id}")


def print_json(payload: dict) -> None:
    print(json.dumps(payload, indent=2, ensure_ascii=False))


def main() -> None:
    parser = argparse.ArgumentParser(description="Admin CLI for safe remote management")
    parser.add_argument("--service-url", default=DEFAULT_SERVICE_URL)
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("list-clients")

    list_dir = subparsers.add_parser("list-dir")
    list_dir.add_argument("--client-id", required=True)
    list_dir.add_argument("--path", default=".")

    download = subparsers.add_parser("download")
    download.add_argument("--client-id", required=True)
    download.add_argument("--remote-path", required=True)
    download.add_argument("--local-path", required=True)

    upload = subparsers.add_parser("upload")
    upload.add_argument("--client-id", required=True)
    upload.add_argument("--local-path", required=True)
    upload.add_argument("--remote-path", required=True)

    args = parser.parse_args()

    if args.command == "list-clients":
        print_json(get_json(f"{args.service_url}/clients"))
        return

    if args.command == "list-dir":
        task_response = post_json(
            args.service_url,
            "/tasks",
            {"client_id": args.client_id, "action": "list_dir", "payload": {"path": args.path}},
        )
        task = wait_for_task(args.service_url, task_response["task"]["task_id"], TASK_TIMEOUT_SECONDS)
        print_json(task["result"])
        return

    if args.command == "download":
        task_response = post_json(
            args.service_url,
            "/tasks",
            {
                "client_id": args.client_id,
                "action": "download_file",
                "payload": {"path": args.remote_path},
            },
        )
        task = wait_for_task(args.service_url, task_response["task"]["task_id"], TASK_TIMEOUT_SECONDS)
        result = task["result"]
        if not result.get("ok"):
            print_json(result)
            return
        output_path = Path(args.local_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        from .models import decode_file_bytes

        output_path.write_bytes(decode_file_bytes(result["content_b64"]))
        print_json({"ok": True, "saved_to": str(output_path), "size": result["size"]})
        return

    if args.command == "upload":
        local_path = Path(args.local_path)
        task_response = post_json(
            args.service_url,
            "/tasks",
            {
                "client_id": args.client_id,
                "action": "upload_file",
                "payload": {
                    "path": args.remote_path,
                    "content_b64": encode_file_bytes(local_path.read_bytes()),
                },
            },
        )
        task = wait_for_task(args.service_url, task_response["task"]["task_id"], TASK_TIMEOUT_SECONDS)
        print_json(task["result"])
        return


if __name__ == "__main__":
    main()
