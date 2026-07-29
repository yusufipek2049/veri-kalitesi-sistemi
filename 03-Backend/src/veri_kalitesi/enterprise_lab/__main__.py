"""ENTERPRISE-LAB-01 baslangic kapisi CLI."""

from __future__ import annotations

import argparse
from pathlib import Path

from veri_kalitesi.enterprise_lab.gate import (
    EnterpriseLabConfigurationError,
    evidence_as_json,
    verify_enterprise_lab_configuration,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("configuration", type=Path)
    args = parser.parse_args()
    try:
        evidence = verify_enterprise_lab_configuration(args.configuration)
    except EnterpriseLabConfigurationError as exc:
        print(f"BLOCKED:{exc.reason_code}")
        return 1
    print(evidence_as_json(evidence))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
