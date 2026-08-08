"""PostgreSQL-only yerel geliştirme ASGI entrypoint'i."""

from veri_kalitesi.api.development_runtime import create_development_app

app = create_development_app()
