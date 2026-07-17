"""Secret manager sınır arayüzü."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol

from veri_kalitesi.data_sources.errors import SecretResolutionError


class SecretResolver(Protocol):
    def resolve(self, secret_reference: str) -> Mapping[str, Any]:
        """Secret referansını çözer; ham secret kalıcı depoya yazılmaz."""


class EmptySecretResolver:
    """Secret gerektirmeyen yerel bağlayıcılar için varsayılan çözücü."""

    def resolve(self, secret_reference: str) -> Mapping[str, Any]:
        return {}


class InMemorySecretResolver:
    """Birim testleri ve yerel prototip için bellek içi secret çözücü."""

    def __init__(self, secrets: Mapping[str, Mapping[str, Any]]) -> None:
        self._secrets = {key: dict(value) for key, value in secrets.items()}

    def resolve(self, secret_reference: str) -> Mapping[str, Any]:
        try:
            return dict(self._secrets[secret_reference])
        except KeyError as exc:
            raise SecretResolutionError("Secret reference could not be resolved.") from exc
