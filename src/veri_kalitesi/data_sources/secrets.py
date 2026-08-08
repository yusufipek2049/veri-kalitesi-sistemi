"""Secret manager sınır arayüzü."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
import re
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


class MountedFileSecretResolver:
    """Yalnız development/test composition için read-only mounted secret resolver."""

    _REFERENCE = re.compile(r"secret://local/([a-zA-Z0-9][a-zA-Z0-9_-]{0,79})")

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root).resolve(strict=True)
        if not self.root.is_dir():
            raise SecretResolutionError("Mounted secret root is unavailable.")

    def resolve(self, secret_reference: str) -> Mapping[str, Any]:
        match = self._REFERENCE.fullmatch(secret_reference)
        if match is None:
            raise SecretResolutionError("Secret reference is not allowed by mounted provider.")
        directory = (self.root / match.group(1)).resolve(strict=True)
        if directory.parent != self.root or not directory.is_dir():
            raise SecretResolutionError("Secret reference is outside the mounted provider root.")
        values: dict[str, str] = {}
        for field in ("username", "password"):
            path = directory / field
            if path.is_symlink():
                raise SecretResolutionError("Mounted secret symlinks are not allowed.")
            resolved = path.resolve(strict=True)
            if resolved.parent != directory or not resolved.is_file():
                raise SecretResolutionError("Mounted secret file is unavailable.")
            value = resolved.read_text(encoding="utf-8").strip()
            if not value:
                raise SecretResolutionError("Mounted secret value is empty.")
            values[field] = value
        return values
