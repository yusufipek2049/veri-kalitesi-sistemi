"""Adlandırılmış SQL şablonu servisi ve API testleri."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from veri_kalitesi.api import DevelopmentActorContextResolver, create_dashboard_api
from veri_kalitesi.api.bff import CSRF_HEADER_NAME
from veri_kalitesi.api.errors import ApiCsrfError
from veri_kalitesi.api.identity import DevelopmentUser, DevelopmentUserRegistry
from veri_kalitesi.api.service_groups import (
    ActorResolverIdentity,
    ApiOptions,
    SqlTemplateServices,
)
from veri_kalitesi.identity import ActorContext, ActorContextIssuer, ActorType
from veri_kalitesi.sql_templates import (
    InMemorySqlTemplateRepository,
    SqlTemplateAuthorizationError,
    SqlTemplateConflictError,
    SqlTemplateService,
    SqlTemplateValidationError,
)

NOW = datetime(2026, 8, 17, 9, 0, tzinfo=timezone.utc)
ACTOR_POLICY_VERSION = "SQL_TEMPLATE_TEST_POLICY_V1"
CSRF_PROOF = "test-csrf-proof"


def _actor(actor_id: str = "owner-user", *, can_view_enterprise: bool = False) -> ActorContext:
    return ActorContextIssuer().issue(
        actor_id=actor_id,
        actor_type=ActorType.USER,
        authentication_source="synthetic-identity-adapter",
        session_id=f"session-{actor_id}",
        roles=frozenset({"DATA_STEWARD"}),
        permitted_source_ids=frozenset({"source-1"}),
        permitted_dataset_ids=frozenset({"dataset-1"}),
        can_view_enterprise=can_view_enterprise,
        privileged=False,
        issued_at=NOW - timedelta(minutes=5),
        expires_at=NOW + timedelta(hours=1),
        policy_version=ACTOR_POLICY_VERSION,
        correlation_id=f"correlation-{actor_id}",
    )


def _service(repository: InMemorySqlTemplateRepository | None = None) -> SqlTemplateService:
    return SqlTemplateService(
        repository if repository is not None else InMemorySqlTemplateRepository(),
        clock=lambda: NOW,
    )


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


def test_create_template_stores_named_read_only_sql() -> None:
    service = _service()
    actor = _actor()

    template = service.create_template(
        actor,
        name="  Günlük müşteri sayımı  ",
        sql_text="SELECT count(*) FROM musteri",
        description="  Gün sonu kontrolü  ",
        default_timeout_seconds=45,
        default_row_limit=500,
    )

    assert template.name == "Günlük müşteri sayımı"
    assert template.description == "Gün sonu kontrolü"
    assert template.owner_user_id == "owner-user"
    assert template.version == 1
    assert service.list_templates(actor) == (template,)


def test_untrusted_actor_context_cannot_read_or_write_templates() -> None:
    service = _service()

    with pytest.raises(SqlTemplateAuthorizationError):
        service.list_templates(None)
    with pytest.raises(SqlTemplateAuthorizationError):
        service.create_template(
            None,
            name="Şablon",
            sql_text="SELECT 1",
            default_timeout_seconds=30,
            default_row_limit=100,
        )


@pytest.mark.parametrize(
    "sql_text",
    [
        "DELETE FROM musteri",
        "SELECT 1; DROP TABLE musteri",
        "UPDATE musteri SET ad = 'x'",
        "   ",
    ],
)
def test_non_read_only_sql_is_rejected(sql_text: str) -> None:
    service = _service()

    with pytest.raises(SqlTemplateValidationError):
        service.create_template(
            _actor(),
            name="Şablon",
            sql_text=sql_text,
            default_timeout_seconds=30,
            default_row_limit=100,
        )


@pytest.mark.parametrize(
    ("timeout_seconds", "row_limit"),
    [(0, 100), (301, 100), (30, 0), (30, 100_001)],
)
def test_execution_limits_outside_policy_range_are_rejected(
    timeout_seconds: int, row_limit: int
) -> None:
    service = _service()

    with pytest.raises(SqlTemplateValidationError):
        service.create_template(
            _actor(),
            name="Şablon",
            sql_text="SELECT 1",
            default_timeout_seconds=timeout_seconds,
            default_row_limit=row_limit,
        )


def test_duplicate_name_is_rejected_case_insensitively() -> None:
    service = _service()
    actor = _actor()
    service.create_template(
        actor,
        name="Sipariş kontrolü",
        sql_text="SELECT 1",
        default_timeout_seconds=30,
        default_row_limit=100,
    )

    with pytest.raises(SqlTemplateConflictError):
        service.create_template(
            actor,
            name="sipariş KONTROLÜ",
            sql_text="SELECT 2",
            default_timeout_seconds=30,
            default_row_limit=100,
        )


def test_update_preserves_unspecified_fields_and_bumps_version() -> None:
    service = _service()
    actor = _actor()
    created = service.create_template(
        actor,
        name="Eski ad",
        sql_text="SELECT 1",
        description="açıklama",
        default_timeout_seconds=30,
        default_row_limit=100,
    )

    updated = service.update_template(actor, created.template_id, name="Yeni ad")

    assert updated.name == "Yeni ad"
    assert updated.sql_text == "SELECT 1"
    assert updated.description == "açıklama"
    assert updated.default_row_limit == 100
    assert updated.version == 2


def test_only_owner_can_change_or_delete_a_template() -> None:
    service = _service()
    owner = _actor("owner-1")
    other = _actor("other-1")
    created = service.create_template(
        owner,
        name="Şablon",
        sql_text="SELECT 1",
        default_timeout_seconds=30,
        default_row_limit=100,
    )

    with pytest.raises(SqlTemplateAuthorizationError):
        service.update_template(other, created.template_id, name="Başka ad")
    with pytest.raises(SqlTemplateAuthorizationError):
        service.delete_template(other, created.template_id)

    service.delete_template(owner, created.template_id)
    assert service.list_templates(owner) == ()


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------


class _SqlTemplateResolver(DevelopmentActorContextResolver):
    """CSRF kanıtını basitleştirilmiş biçimde denetleyen test resolver'ı."""

    def protect_state_changing(self, request) -> ActorContext:  # type: ignore[no-untyped-def]
        if request.headers.get(CSRF_HEADER_NAME) != CSRF_PROOF:
            raise ApiCsrfError("rejected", request.state.correlation_id)
        return self.resolve(request)


def _resolver() -> _SqlTemplateResolver:
    registry = DevelopmentUserRegistry(
        [
            DevelopmentUser(
                user_id="owner-user",
                display_name="Şablon Sahibi",
                roles=frozenset({"DATA_STEWARD"}),
                permitted_source_ids=frozenset({"source-1"}),
                permitted_dataset_ids=frozenset({"dataset-1"}),
            ),
            DevelopmentUser(
                user_id="other-user",
                display_name="Başka Kullanıcı",
                roles=frozenset({"DATA_STEWARD"}),
                permitted_source_ids=frozenset({"source-1"}),
                permitted_dataset_ids=frozenset({"dataset-1"}),
            ),
        ]
    )
    return _SqlTemplateResolver(
        runtime_environment="development",
        policy_version=ACTOR_POLICY_VERSION,
        permitted_source_ids=frozenset({"source-1"}),
        permitted_dataset_ids=frozenset({"dataset-1"}),
        can_view_enterprise=False,
        user_registry=registry,
        clock=lambda: NOW,
    )


def _client() -> TestClient:
    app = create_dashboard_api(
        identity=ActorResolverIdentity(_resolver()),
        options=ApiOptions(data_origin="synthetic-test"),
        sql_templates=SqlTemplateServices(service=_service()),
    )
    return TestClient(app)


def _headers(user_id: str = "owner-user") -> dict[str, str]:
    return {CSRF_HEADER_NAME: CSRF_PROOF, "X-Development-User-Id": user_id}


def test_api_round_trip_create_list_update_delete() -> None:
    client = _client()

    created = client.post(
        "/api/v1/sql-templates",
        json={
            "name": "Boş e-posta oranı",
            "sql_text": "SELECT count(*) FROM musteri WHERE eposta IS NULL",
            "description": "Zorunlu alan kontrolü",
            "default_timeout_seconds": 60,
            "default_row_limit": 1000,
        },
        headers=_headers(),
    )
    assert created.status_code == 201, created.text
    assert created.headers["cache-control"] == "no-store"
    template_id = created.json()["item"]["template_id"]
    assert created.json()["item"]["owner_user_id"] == "owner-user"

    listed = client.get("/api/v1/sql-templates", headers={"X-Development-User-Id": "other-user"})
    assert listed.status_code == 200
    assert [item["name"] for item in listed.json()["items"]] == ["Boş e-posta oranı"]

    updated = client.patch(
        f"/api/v1/sql-templates/{template_id}",
        json={"name": "Boş e-posta oranı (v2)", "default_row_limit": 250},
        headers=_headers(),
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["item"]["name"] == "Boş e-posta oranı (v2)"
    assert updated.json()["item"]["default_row_limit"] == 250
    assert updated.json()["item"]["version"] == 2

    deleted = client.delete(f"/api/v1/sql-templates/{template_id}", headers=_headers())
    assert deleted.status_code == 204
    assert client.get("/api/v1/sql-templates").json()["items"] == []


def test_api_denies_template_change_by_non_owner() -> None:
    client = _client()
    created = client.post(
        "/api/v1/sql-templates",
        json={
            "name": "Sahiplik kontrolü",
            "sql_text": "SELECT 1",
            "default_timeout_seconds": 30,
            "default_row_limit": 100,
        },
        headers=_headers(),
    )
    template_id = created.json()["item"]["template_id"]

    response = client.delete(f"/api/v1/sql-templates/{template_id}", headers=_headers("other-user"))

    assert response.status_code == 403


def test_api_rejects_write_only_sql_with_422() -> None:
    response = _client().post(
        "/api/v1/sql-templates",
        json={
            "name": "Tehlikeli",
            "sql_text": "DROP TABLE musteri",
            "default_timeout_seconds": 30,
            "default_row_limit": 100,
        },
        headers=_headers(),
    )

    assert response.status_code == 422


def test_api_returns_404_for_unknown_template() -> None:
    response = _client().patch(
        "/api/v1/sql-templates/missing", json={"name": "x"}, headers=_headers()
    )

    assert response.status_code == 404


def test_api_is_unavailable_when_service_is_not_composed() -> None:
    app = create_dashboard_api(
        identity=ActorResolverIdentity(_resolver()),
        options=ApiOptions(data_origin="synthetic-test"),
    )

    response = TestClient(app).get("/api/v1/sql-templates")

    assert response.status_code == 503
