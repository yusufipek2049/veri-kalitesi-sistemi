"""Phantom capability routes must stay out of the executable API schema."""

from veri_kalitesi.api import create_dashboard_api


EXPECTED_ROUTE_METHODS = {
    ("GET", "/api/v1/audit/actions"),
    ("GET", "/api/v1/audit/events"),
    ("GET", "/api/v1/audit/events/export"),
    ("GET", "/api/v1/audit/events/grouped"),
    ("GET", "/api/v1/audit/summary"),
    ("GET", "/api/v1/dashboard/overview"),
    ("GET", "/api/v1/data-sources"),
    ("GET", "/api/v1/data-sources/{data_source_id}/discovery-scope"),
    ("GET", "/api/v1/datasets"),
    ("GET", "/api/v1/datasets/{dataset_id}"),
    ("GET", "/api/v1/datasets/{dataset_id}/fields"),
    ("GET", "/api/v1/datasets/{dataset_id}/scores"),
    ("GET", "/api/v1/development/users"),
    ("GET", "/api/v1/executions"),
    ("GET", "/api/v1/executions/{execution_id}"),
    ("GET", "/api/v1/fields/{data_field_id}"),
    ("GET", "/api/v1/issues"),
    ("GET", "/api/v1/issues/{issue_id}/assignment-options"),
    ("GET", "/api/v1/issues/{issue_id}/investigation/evidence"),
    ("GET", "/api/v1/metadata-discoveries/{discovery_id}"),
    ("GET", "/api/v1/metadata-discoveries/{discovery_id}/diff"),
    ("GET", "/api/v1/openapi.json"),
    ("HEAD", "/api/v1/openapi.json"),
    ("GET", "/api/v1/rules"),
    ("GET", "/api/v1/rules/{quality_rule_id}/scores"),
    ("GET", "/api/v1/rules/{rule_id}"),
    ("GET", "/api/v1/scores"),
    ("GET", "/api/v1/scores/comparison"),
    ("GET", "/api/v1/scores/rules/{rule_version_id}"),
    ("GET", "/api/v1/scores/trend"),
    ("GET", "/api/v1/scores/{quality_score_id}"),
    ("GET", "/health"),
    ("GET", "/ready"),
    ("PATCH", "/api/v1/datasets/{dataset_id}"),
    ("PATCH", "/api/v1/fields/{field_id}"),
    ("POST", "/api/v1/data-source-activation-requests/{activation_request_id}/decision"),
    ("POST", "/api/v1/data-source-deactivation-requests/{deactivation_request_id}/decision"),
    ("POST", "/api/v1/data-sources"),
    ("POST", "/api/v1/data-sources/{data_source_id}/activation"),
    ("POST", "/api/v1/data-sources/{data_source_id}/deactivation"),
    ("POST", "/api/v1/data-sources/{data_source_id}/metadata-discoveries"),
    ("POST", "/api/v1/data-sources/{data_source_id}/passivation"),
    ("POST", "/api/v1/data-sources/{data_source_id}/test"),
    ("POST", "/api/v1/executions"),
    ("POST", "/api/v1/executions/{execution_id}/cancel"),
    ("POST", "/api/v1/issues"),
    ("POST", "/api/v1/issues/{issue_id}/assignment"),
    ("POST", "/api/v1/issues/{issue_id}/closure"),
    ("POST", "/api/v1/issues/{issue_id}/investigation"),
    ("POST", "/api/v1/issues/{issue_id}/resolution"),
    ("POST", "/api/v1/issues/{issue_id}/verification"),
    ("POST", "/api/v1/metadata-diffs/{metadata_diff_id}/application"),
    ("POST", "/api/v1/rules"),
    ("POST", "/api/v1/rules/approval/{approval_request_id}/decide"),
    ("POST", "/api/v1/rules/approval/{approval_request_id}/withdraw"),
    ("POST", "/api/v1/rules/{quality_rule_id}/activation"),
    ("POST", "/api/v1/rules/{quality_rule_id}/approval"),
    ("POST", "/api/v1/rules/{quality_rule_id}/passivation"),
    ("POST", "/api/v1/rules/{quality_rule_id}/test"),
    ("POST", "/api/v1/rules/{quality_rule_id}/versions"),
    ("PUT", "/api/v1/data-sources/{data_source_id}/discovery-scope"),
}


def test_unreachable_capability_routes_are_absent_from_openapi() -> None:
    paths = create_dashboard_api().openapi()["paths"]

    removed_paths = {
        "/api/v1/dashboard/summary",
        "/api/v1/profile-comparisons",
        "/api/v1/profile-snapshots",
        "/api/v1/profile-snapshots/{profile_id}",
        "/api/v1/profile-snapshots/{profile_id}/drift",
        "/api/v1/scores/{quality_score_id}/reproduction",
        "/api/v1/reports/summary",
        "/api/v1/reports/",
        "/api/v1/reports/{report_id}",
        "/api/v1/reports/{report_id}/download",
        "/api/v1/report-schedules",
        "/api/v1/report-schedules/{schedule_id}",
        "/api/v1/report-schedules/trigger-due",
        "/api/v1/lineage/snapshots/{snapshot_id}",
        "/api/v1/governance/{asset_ref}/projection",
        "/api/v1/session/logout",
    }

    assert removed_paths.isdisjoint(paths)


def test_dashboard_api_route_table_matches_snapshot() -> None:
    app = create_dashboard_api()
    actual = {
        (method, route.path)
        for route in app.routes
        for method in getattr(route, "methods", set())
    }

    assert actual == EXPECTED_ROUTE_METHODS
    assert len(app.routes) == 60
    assert len([route for route in app.routes if route.path not in {"/health", "/ready"}]) == 58
