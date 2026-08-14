"""Negatif mypy fixture: bir IssueServices alanı sessizce unutulamaz.

Çalıştırma:
    mypy --no-incremental --exclude '$^' --show-error-codes \
        src/veri_kalitesi/api/service_groups.py \
        tests/typing/faz8_missing_issue_service.py
"""

from veri_kalitesi.api.service_groups import IssueServices


IssueServices(
    query=None,
    investigation=None,
    investigation_evidence=None,
    assignment=None,
    assignee_options=None,
    resolution=None,
    verification=None,
    creation=None,
)
