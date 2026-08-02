"""Yerel geliştirme sunucusu — PostgreSQL kalıcılığıyla."""

from sqlalchemy import create_engine, text

from veri_kalitesi.api.development import create_development_app
from veri_kalitesi.audit import AuditRedactor, build_default_redaction_policy
from veri_kalitesi.audit.postgresql_outbox import PostgreSQLTransactionalAudit
from veri_kalitesi.persistence import DatabaseSettings, create_session_factory

DATABASE_URL = "postgresql+psycopg://dqtest:dqtest@127.0.0.1:55432/data_quality"
SCHEMA = "data_quality"


class _FakePreparedRepo:
    """Audit prepared event deposu — yerel geliştirmede no-op."""

    def store(self, event):
        pass


settings = DatabaseSettings.from_url(DATABASE_URL, schema=SCHEMA)
session_factory = create_session_factory(settings)

engine = create_engine(settings.url)
with engine.begin() as conn:
    conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{SCHEMA}"'))

transactional_audit = PostgreSQLTransactionalAudit(
    session_factory,
    AuditRedactor(build_default_redaction_policy()),
    _FakePreparedRepo(),
    policy_version="DEV_AUDIT_V1",
    schema=SCHEMA,
)

app = create_development_app(
    session_factory=session_factory,
    transactional_audit=transactional_audit,
)
