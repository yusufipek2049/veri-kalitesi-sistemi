"""Yalnız yerel geliştirmede kullanılabilen sentetik dashboard API fabrikası.

Bu modül geriye dönük uyumluluk için alt modüllerdeki tüm geliştirme
bileşenlerini yeniden dışa aktarır. Yeni kod doğrudan alt modülleri
kullanmalıdır.
"""

from __future__ import annotations

from veri_kalitesi.api.development_composition import (
    DEVELOPMENT_USER_REGISTRY,
    create_synthetic_development_app,
)
from veri_kalitesi.api.development_data_source_store import (
    DevelopmentDataSourceReader,
    DevelopmentDataSourceStore,
)
from veri_kalitesi.api.development_execution_store import (
    DevelopmentExecutionReader,
    DevelopmentExecutionStore,
)
from veri_kalitesi.api.development_fixtures import (
    DEVELOPMENT_ASSIGNEE_OPTIONS,
    DEVELOPMENT_EXECUTIONS,
    DEVELOPMENT_ISSUES,
    DEVELOPMENT_RULES,
    DEVELOPMENT_SOURCES,
    DEVELOPMENT_TREND_POLICY,
    POLICY_VERSION,
)
from veri_kalitesi.api.development_issue_store import DevelopmentIssueStore
from veri_kalitesi.api.development_rule_store import (
    DevelopmentRuleReader,
    DevelopmentRuleStore,
)

__all__ = [
    "DEVELOPMENT_ASSIGNEE_OPTIONS",
    "DEVELOPMENT_EXECUTIONS",
    "DEVELOPMENT_ISSUES",
    "DEVELOPMENT_RULES",
    "DEVELOPMENT_SOURCES",
    "DEVELOPMENT_TREND_POLICY",
    "DEVELOPMENT_USER_REGISTRY",
    "POLICY_VERSION",
    "DevelopmentDataSourceReader",
    "DevelopmentDataSourceStore",
    "DevelopmentExecutionReader",
    "DevelopmentExecutionStore",
    "DevelopmentIssueStore",
    "DevelopmentRuleReader",
    "DevelopmentRuleStore",
    "create_synthetic_development_app",
]
