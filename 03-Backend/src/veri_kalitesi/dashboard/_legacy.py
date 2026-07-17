"""Internal compatibility adapter for pre-ActorContext dashboard callers."""

from veri_kalitesi.dashboard.errors import (
    DashboardAuthorizationError,
    DashboardNotFoundError,
    DashboardValidationError,
)
from veri_kalitesi.dashboard.models import (
    DashboardAccessScope,
    DashboardScoreNode,
    DashboardScoreTree,
)
from veri_kalitesi.dashboard.service import ScoreReader, _read_score_tree


class LegacyDashboardQueryAdapter:
    """Deprecated: remove after trusted identity adapters are integrated."""

    __deprecated__ = True

    def __init__(self, score_reader: ScoreReader) -> None:
        self.score_reader = score_reader

    def get_score_tree(
        self,
        execution_id: str,
        access_scope: DashboardAccessScope,
        *,
        correlation_id: str,
    ) -> DashboardScoreTree:
        return _read_score_tree(
            self.score_reader,
            execution_id,
            access_scope,
            correlation_id,
        )

    def get_source_detail(
        self,
        execution_id: str,
        data_source_id: str,
        access_scope: DashboardAccessScope,
        *,
        correlation_id: str,
    ) -> DashboardScoreNode:
        if not data_source_id.strip():
            raise DashboardValidationError("data_source_id is required.")
        if data_source_id not in access_scope.allowed_source_ids:
            raise DashboardAuthorizationError(
                "Data source is outside the authorized dashboard scope.",
                correlation_id,
            )
        tree = self.get_score_tree(
            execution_id,
            access_scope,
            correlation_id=correlation_id,
        )
        for source in tree.sources:
            if source.scope_id == data_source_id:
                return source
        raise DashboardNotFoundError("Dashboard source score not found.")
