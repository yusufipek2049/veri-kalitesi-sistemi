"""Veri-minimum ENTERPRISE-LAB-01 fake entegrasyon servisleri."""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any


MAX_BODY_BYTES = 1024 * 1024
OBJECT_ID = re.compile(r"^[a-f0-9]{64}$")
SERVICENOW_FIELDS = frozenset({"short_description", "correlation_id", "issue_id"})
SIEM_FIELDS = frozenset({"event_id", "occurred_at_utc", "action", "result", "correlation_id"})
SERVICES = frozenset({"secret-manager", "servicenow", "siem", "evidence"})
SECRET_FILES = {
    "keycloak-admin": "/run/secrets/keycloak_admin_password",
    "postgres-app": "/run/secrets/postgres_app_password",
    "postgres-replication": "/run/secrets/postgres_replication_password",
    "rabbitmq": "/run/secrets/rabbitmq_password",
}


class LabHandler(BaseHTTPRequestHandler):
    server_version = "EnterpriseLab/1"
    protocol_version = "HTTP/1.1"
    records: dict[str, dict[str, Any]] = {}
    event_count = 0

    def log_message(self, _format: str, *args: object) -> None:
        return

    def do_GET(self) -> None:
        if self.path == "/health":
            payload = self._health_payload()
            status = (
                HTTPStatus.OK
                if payload["status"] == "UP"
                else HTTPStatus.SERVICE_UNAVAILABLE
            )
            self._json(status, payload)
            return
        if SERVICE == "evidence" and self.path.startswith("/objects/"):
            self._read_evidence(self.path.removeprefix("/objects/"))
            return
        self._json(HTTPStatus.NOT_FOUND, {"code": "NOT_FOUND"})

    def do_POST(self) -> None:
        if SERVICE == "secret-manager" and self.path == "/v1/resolve":
            self._resolve_secret()
            return
        if SERVICE == "servicenow" and self.path == "/api/now/table/incident":
            self._create_incident()
            return
        if SERVICE == "siem" and self.path == "/events":
            self._collect_event()
            return
        self._json(HTTPStatus.NOT_FOUND, {"code": "NOT_FOUND"})

    def do_PUT(self) -> None:
        if SERVICE == "evidence" and self.path.startswith("/objects/"):
            self._create_evidence(self.path.removeprefix("/objects/"))
            return
        self._json(HTTPStatus.NOT_FOUND, {"code": "NOT_FOUND"})

    def do_DELETE(self) -> None:
        self._json(HTTPStatus.METHOD_NOT_ALLOWED, {"code": "APPEND_ONLY"})

    def _health_payload(self) -> dict[str, Any]:
        if SERVICE == "secret-manager":
            try:
                ready = all(Path(path).read_text(encoding="utf-8").strip() for path in SECRET_FILES.values())
            except OSError:
                ready = False
            return {"status": "UP" if ready else "DOWN", "service": SERVICE}
        if SERVICE == "siem":
            return {"status": "UP", "service": SERVICE, "accepted_events": self.event_count}
        return {"status": "UP", "service": SERVICE}

    def _resolve_secret(self) -> None:
        if not self._authorized():
            self._json(HTTPStatus.UNAUTHORIZED, {"code": "UNAUTHORIZED"})
            return
        payload = self._read_json()
        reference = payload.get("reference") if payload else None
        path = SECRET_FILES.get(reference)
        if path is None:
            self._json(HTTPStatus.NOT_FOUND, {"code": "REFERENCE_NOT_FOUND"})
            return
        try:
            value = Path(path).read_text(encoding="utf-8").strip()
        except OSError:
            self._json(HTTPStatus.SERVICE_UNAVAILABLE, {"code": "SECRET_STORE_UNAVAILABLE"})
            return
        self._json(HTTPStatus.OK, {"reference": reference, "value": value})

    def _authorized(self) -> bool:
        try:
            expected = Path("/run/secrets/local_secret_manager_token").read_text(
                encoding="utf-8"
            ).strip()
        except OSError:
            return False
        return self.headers.get("Authorization") == f"Bearer {expected}"

    def _create_incident(self) -> None:
        key = self.headers.get("Idempotency-Key", "")
        payload = self._read_json()
        if not key or payload is None or frozenset(payload) != SERVICENOW_FIELDS:
            self._json(HTTPStatus.BAD_REQUEST, {"code": "INVALID_REQUEST"})
            return
        existing = self.records.get(key)
        if existing is None:
            digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
            existing = {"sys_id": digest[:32], "number": f"LAB{digest[:8].upper()}"}
            self.records[key] = existing
            status = HTTPStatus.CREATED
        else:
            status = HTTPStatus.OK
        self._json(status, existing)

    def _collect_event(self) -> None:
        payload = self._read_json()
        if payload is None or frozenset(payload) != SIEM_FIELDS:
            self._json(HTTPStatus.BAD_REQUEST, {"code": "INVALID_EVENT"})
            return
        type(self).event_count += 1
        self._json(HTTPStatus.ACCEPTED, {"status": "ACCEPTED"})

    def _create_evidence(self, object_id: str) -> None:
        if not OBJECT_ID.fullmatch(object_id):
            self._json(HTTPStatus.BAD_REQUEST, {"code": "OBJECT_ID_INVALID"})
            return
        body = self._read_body()
        if body is None or hashlib.sha256(body).hexdigest() != object_id:
            self._json(HTTPStatus.BAD_REQUEST, {"code": "DIGEST_MISMATCH"})
            return
        target = EVIDENCE_ROOT / object_id
        try:
            descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o440)
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(body)
                stream.flush()
                os.fsync(stream.fileno())
        except FileExistsError:
            self._json(HTTPStatus.CONFLICT, {"code": "OBJECT_ALREADY_EXISTS"})
            return
        except OSError:
            self._json(HTTPStatus.SERVICE_UNAVAILABLE, {"code": "STORE_UNAVAILABLE"})
            return
        self._json(HTTPStatus.CREATED, {"object_id": object_id})

    def _read_evidence(self, object_id: str) -> None:
        if not OBJECT_ID.fullmatch(object_id):
            self._json(HTTPStatus.BAD_REQUEST, {"code": "OBJECT_ID_INVALID"})
            return
        try:
            body = (EVIDENCE_ROOT / object_id).read_bytes()
        except FileNotFoundError:
            self._json(HTTPStatus.NOT_FOUND, {"code": "OBJECT_NOT_FOUND"})
            return
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "application/octet-stream")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> dict[str, Any] | None:
        body = self._read_body()
        if body is None:
            return None
        try:
            payload = json.loads(body)
        except (UnicodeDecodeError, json.JSONDecodeError):
            return None
        return payload if isinstance(payload, dict) else None

    def _read_body(self) -> bytes | None:
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            return None
        if length <= 0 or length > MAX_BODY_BYTES:
            return None
        return self.rfile.read(length)

    def _json(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("ascii")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if len(sys.argv) != 2 or sys.argv[1] not in SERVICES:
    raise SystemExit("usage: mock_service.py <secret-manager|servicenow|siem|evidence>")

SERVICE = sys.argv[1]
EVIDENCE_ROOT = Path("/var/lib/enterprise-lab/evidence")
if SERVICE == "evidence":
    EVIDENCE_ROOT.mkdir(parents=True, exist_ok=True)

ThreadingHTTPServer(("0.0.0.0", 8080), LabHandler).serve_forever()
