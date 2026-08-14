#!/usr/bin/env python3
"""Run all opt-in PostgreSQL integration tests against development Compose."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
from urllib.parse import quote

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
COMPOSE_FILE = PROJECT_ROOT / "infra" / "development" / "compose.yaml"
POSTGRES_PORT = "15432"
TEST_SCHEMA = "dq_test"


def _run(command: list[str], *, environment: dict[str, str]) -> int:
    return subprocess.run(command, cwd=PROJECT_ROOT, env=environment, check=False).returncode


def main() -> int:
    load_dotenv(PROJECT_ROOT / ".env")
    password = os.environ.get("DQ_POSTGRES_PASSWORD")
    if not password:
        print(
            "DQ_POSTGRES_PASSWORD must be set in the environment or the local .env file.",
            file=sys.stderr,
        )
        return 2

    environment = os.environ.copy()
    compose = ["docker", "compose", "-f", str(COMPOSE_FILE)]
    if _run([*compose, "up", "-d", "--wait", "postgres"], environment=environment):
        return 1

    encoded_password = quote(password, safe="")
    environment.update(
        {
            "DATA_QUALITY_POSTGRES_TEST_URL": (
                "postgresql+psycopg://dq_app:"
                f"{encoded_password}@127.0.0.1:{POSTGRES_PORT}/data_quality"
            ),
            "DATA_QUALITY_DATABASE_SCHEMA": TEST_SCHEMA,
            "SYNTHETIC_POSTGRES_TEST": "1",
            "PGHOST": "127.0.0.1",
            "PGPORT": POSTGRES_PORT,
            "PGDATABASE": "data_quality",
            "PGUSER": "dq_app",
            "PGPASSWORD": password,
        }
    )
    pytest_args = sys.argv[1:]
    if not any(
        argument.startswith("tests/") or "::" in argument
        for argument in pytest_args
    ):
        pytest_args.append("tests/integration")
    return _run([sys.executable, "-m", "pytest", *pytest_args], environment=environment)


if __name__ == "__main__":
    raise SystemExit(main())
