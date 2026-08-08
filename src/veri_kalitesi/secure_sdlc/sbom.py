"""Deterministic CycloneDX inventory for declared Python dependencies."""

from __future__ import annotations

import argparse
import json
import stat
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, TextIO, cast

import tomli

from packaging.requirements import InvalidRequirement, Requirement
from packaging.specifiers import InvalidSpecifier, SpecifierSet
from packaging.utils import InvalidName, canonicalize_name
from packaging.version import InvalidVersion, Version

from veri_kalitesi.secure_sdlc.errors import (
    DependencyInventoryTechnicalError,
    DependencyInventoryValidationError,
)
from veri_kalitesi.secure_sdlc.models import DeclaredDependency, PythonProjectInventory

_MAX_MANIFEST_SIZE_BYTES = 1_048_576
_CYCLONEDX_SCHEMA = "http://cyclonedx.org/schema/bom-1.5.schema.json"
_INVENTORY_POLICY_VERSION = "28B-v1"


class PythonDependencyInventoryBuilder:
    """Read PEP 621 direct dependencies without resolving packages or using a network."""

    def read(self, manifest: Path | str) -> PythonProjectInventory:
        manifest_path = Path(manifest)
        if manifest_path.is_symlink():
            raise DependencyInventoryValidationError("MANIFEST_SYMLINK_REJECTED")
        try:
            manifest_stat = manifest_path.stat()
        except FileNotFoundError as exc:
            raise DependencyInventoryValidationError("MANIFEST_NOT_FOUND") from exc
        except OSError as exc:
            raise DependencyInventoryTechnicalError("MANIFEST_STAT_FAILED") from exc
        if not stat.S_ISREG(manifest_stat.st_mode):
            raise DependencyInventoryValidationError("MANIFEST_NOT_REGULAR_FILE")
        if manifest_stat.st_size > _MAX_MANIFEST_SIZE_BYTES:
            raise DependencyInventoryValidationError("MANIFEST_TOO_LARGE")

        try:
            content = manifest_path.read_bytes()
        except OSError as exc:
            raise DependencyInventoryTechnicalError("MANIFEST_READ_FAILED") from exc
        try:
            document = tomli.loads(content.decode("utf-8"))
        except (UnicodeDecodeError, tomli.TOMLDecodeError) as exc:
            raise DependencyInventoryValidationError("MANIFEST_PARSE_FAILED") from exc

        project = document.get("project")
        if not isinstance(project, Mapping):
            raise DependencyInventoryValidationError("PROJECT_METADATA_REQUIRED")
        return self._build_inventory(cast(Mapping[str, Any], project))

    def to_cyclonedx(self, inventory: PythonProjectInventory) -> dict[str, object]:
        project_ref = f"pkg:generic/{inventory.name}@{inventory.version}"
        components: list[dict[str, object]] = []
        dependency_refs: list[str] = []
        dependency_graph: list[dict[str, object]] = []
        for dependency in inventory.dependencies:
            component_ref = f"pkg:pypi/{dependency.canonical_name}@{dependency.version}"
            component: dict[str, object] = {
                "type": "library",
                "bom-ref": component_ref,
                "name": dependency.canonical_name,
                "version": dependency.version,
                "purl": component_ref,
                "scope": "required",
            }
            if dependency.environment_marker is not None:
                component["properties"] = [
                    {
                        "name": "veri-kalitesi:environment-marker",
                        "value": dependency.environment_marker,
                    }
                ]
            components.append(component)
            dependency_refs.append(component_ref)
            dependency_graph.append({"ref": component_ref, "dependsOn": []})

        dependency_graph.insert(0, {"ref": project_ref, "dependsOn": dependency_refs})
        return {
            "$schema": _CYCLONEDX_SCHEMA,
            "bomFormat": "CycloneDX",
            "specVersion": "1.5",
            "version": 1,
            "metadata": {
                "component": {
                    "type": "application",
                    "bom-ref": project_ref,
                    "name": inventory.name,
                    "version": inventory.version,
                    "purl": project_ref,
                    "properties": [
                        {
                            "name": "veri-kalitesi:inventory-scope",
                            "value": "declared-direct-dependencies",
                        },
                        {
                            "name": "veri-kalitesi:inventory-policy-version",
                            "value": _INVENTORY_POLICY_VERSION,
                        },
                        {
                            "name": "veri-kalitesi:requires-python",
                            "value": inventory.requires_python,
                        },
                    ],
                }
            },
            "components": components,
            "dependencies": dependency_graph,
        }

    @classmethod
    def serialize(cls, inventory: PythonProjectInventory) -> bytes:
        content = json.dumps(
            cls().to_cyclonedx(inventory),
            ensure_ascii=True,
            indent=2,
            sort_keys=True,
        )
        return f"{content}\n".encode("utf-8")

    @staticmethod
    def _build_inventory(project: Mapping[str, Any]) -> PythonProjectInventory:
        dynamic = project.get("dynamic", [])
        if not isinstance(dynamic, list) or any(not isinstance(item, str) for item in dynamic):
            raise DependencyInventoryValidationError("PROJECT_DYNAMIC_INVALID")
        if {item.lower() for item in dynamic} & {"version", "dependencies"}:
            raise DependencyInventoryValidationError("DYNAMIC_INVENTORY_REJECTED")

        name = _required_string(project, "name", "PROJECT_NAME_REQUIRED")
        try:
            canonical_name = canonicalize_name(name, validate=True)
        except InvalidName as exc:
            raise DependencyInventoryValidationError("PROJECT_NAME_INVALID") from exc
        version = _normalize_version(
            _required_string(project, "version", "PROJECT_VERSION_REQUIRED"),
            "PROJECT_VERSION_INVALID",
        )
        requires_python = _required_string(project, "requires-python", "REQUIRES_PYTHON_REQUIRED")
        try:
            SpecifierSet(requires_python)
        except InvalidSpecifier as exc:
            raise DependencyInventoryValidationError("REQUIRES_PYTHON_INVALID") from exc

        declared_dependencies = project.get("dependencies")
        if not isinstance(declared_dependencies, list) or any(
            not isinstance(item, str) for item in declared_dependencies
        ):
            raise DependencyInventoryValidationError("PROJECT_DEPENDENCIES_REQUIRED")

        dependencies: list[DeclaredDependency] = []
        seen_names: set[str] = set()
        for declaration in declared_dependencies:
            dependency = _parse_dependency(declaration)
            if dependency.canonical_name in seen_names:
                raise DependencyInventoryValidationError("DUPLICATE_DEPENDENCY")
            seen_names.add(dependency.canonical_name)
            dependencies.append(dependency)

        return PythonProjectInventory(
            name=canonical_name,
            version=version,
            requires_python=str(SpecifierSet(requires_python)),
            dependencies=tuple(sorted(dependencies)),
        )


def main(
    argv: Sequence[str] | None = None,
    *,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
) -> int:
    output = stdout or sys.stdout
    error_output = stderr or sys.stderr
    parser = argparse.ArgumentParser(
        description="Generate a deterministic CycloneDX inventory from PEP 621 metadata."
    )
    parser.add_argument("manifest", nargs="?", default="pyproject.toml", type=Path)
    arguments = parser.parse_args(argv)
    builder = PythonDependencyInventoryBuilder()

    try:
        inventory = builder.read(arguments.manifest)
    except DependencyInventoryValidationError as exc:
        _write_error(error_output, "VALIDATION_ERROR", exc.reason_code)
        return 2
    except DependencyInventoryTechnicalError as exc:
        _write_error(error_output, "TECHNICAL_ERROR", exc.operation_code)
        return 2

    output.write(builder.serialize(inventory).decode("utf-8"))
    return 0


def _required_string(project: Mapping[str, Any], key: str, reason_code: str) -> str:
    value = project.get(key)
    if not isinstance(value, str) or not value.strip():
        raise DependencyInventoryValidationError(reason_code)
    return value.strip()


def _normalize_version(value: str, reason_code: str) -> str:
    try:
        return str(Version(value))
    except InvalidVersion as exc:
        raise DependencyInventoryValidationError(reason_code) from exc


def _parse_dependency(declaration: str) -> DeclaredDependency:
    try:
        requirement = Requirement(declaration)
    except InvalidRequirement as exc:
        raise DependencyInventoryValidationError("DEPENDENCY_DECLARATION_INVALID") from exc
    if requirement.url is not None:
        raise DependencyInventoryValidationError("DEPENDENCY_URL_REJECTED")
    if requirement.extras:
        raise DependencyInventoryValidationError("DEPENDENCY_EXTRAS_REJECTED")
    specifiers = list(requirement.specifier)
    if len(specifiers) != 1 or specifiers[0].operator != "==" or "*" in specifiers[0].version:
        raise DependencyInventoryValidationError("DEPENDENCY_EXACT_PIN_REQUIRED")
    version = _normalize_version(specifiers[0].version, "DEPENDENCY_VERSION_INVALID")
    marker = str(requirement.marker) if requirement.marker is not None else None
    return DeclaredDependency(
        canonical_name=canonicalize_name(requirement.name),
        version=version,
        environment_marker=marker,
    )


def _write_error(stream: TextIO, status: str, reason_code: str) -> None:
    stream.write(json.dumps({"status": status, "reason_code": reason_code}, sort_keys=True))
    stream.write("\n")


if __name__ == "__main__":
    raise SystemExit(main())
