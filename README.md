# Safe Remote File Management Demo

This project implements a safety-constrained remote management demo in Python.

Components:

- `service`: central coordinator for client registration, heartbeats, task queue, and result collection
- `client`: endpoint agent that connects to the service, reports status, lists files under allowed directories, and transfers files under policy
- `admin`: operator CLI that queries online clients and submits approved tasks

Safety boundaries:

- no arbitrary shell command execution
- file access is limited to configured allowlisted directories
- uploads and downloads are limited by file size
- all client actions are logged and tied to a task id

## Quick start

1. Start the service:

```bash
python -m app.service
```

2. Start one or more clients:

```bash
python -m app.client --client-id demo-client --allow-dir ./shared
```

3. Use the admin CLI:

```bash
python -m app.admin list-clients
python -m app.admin list-dir --client-id demo-client --path .
python -m app.admin download --client-id demo-client --remote-path example.txt --local-path ./downloads/example.txt
python -m app.admin upload --client-id demo-client --local-path ./upload.txt --remote-path inbound/upload.txt
```

Defaults:

- service URL: `http://127.0.0.1:8765`
- max file size: 5 MiB

## Layout

```text
app/
  admin.py
  client.py
  config.py
  models.py
  service.py
```
