"""Phantom capability routes must stay out of the executable API schema."""

from veri_kalitesi.api import create_dashboard_api


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
