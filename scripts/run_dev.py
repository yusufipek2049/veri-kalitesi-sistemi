"""PostgreSQL-only yerel geliştirme ASGI entrypoint'i."""

from veri_kalitesi.api.development_runtime import create_development_app
from veri_kalitesi.operational_logging import configure_logging

configure_logging()
app = create_development_app()
