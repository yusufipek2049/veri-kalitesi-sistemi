"""BFR-SDLC-001/002/004 and NFR-SEC-012 dependency inventory tests."""

from __future__ import annotations

import json
from io import StringIO
from pathlib import Path

import pytest

from veri_kalitesi.secure_sdlc import (
    DependencyInventoryTechnicalError,
    DependencyInventoryValidationError,
)
from veri_kalitesi.secure_sdlc.sbom import PythonDependencyInventoryBuilder, main


def test_reads_pinned_dependencies_in_deterministic_order(tmp_path: Path) -> None:
    manifest = _write_manifest(
        tmp_path,
        dependencies=(
            'Zulu_Package==2.0; python_version < "3.12"',
            "alpha.package==1.0.0",
        ),
    )

    inventory = PythonDependencyInventoryBuilder().read(manifest)

    assert inventory.name == "synthetic-application"
    assert inventory.version == "1.2.3"
    assert inventory.requires_python == ">=3.10"
    assert [dependency.canonical_name for dependency in inventory.dependencies] == [
        "alpha-package",
        "zulu-package",
    ]
    assert inventory.dependencies[1].environment_marker == 'python_version < "3.12"'


def test_generates_deterministic_version_linked_cyclonedx_document(tmp_path: Path) -> None:
    manifest = _write_manifest(tmp_path, dependencies=("sample-lib==4.5.6",))
    builder = PythonDependencyInventoryBuilder()
    inventory = builder.read(manifest)

    first = builder.to_cyclonedx(inventory)
    second = builder.to_cyclonedx(inventory)

    assert first == second
    assert first["bomFormat"] == "CycloneDX"
    assert first["specVersion"] == "1.5"
    assert first["version"] == 1
    assert "serialNumber" not in first
    metadata = first["metadata"]
    assert isinstance(metadata, dict)
    assert metadata["component"]["version"] == "1.2.3"
    assert metadata["component"]["bom-ref"] == "pkg:generic/synthetic-application@1.2.3"
    assert {
        "name": "veri-kalitesi:inventory-policy-version",
        "value": "28B-v1",
    } in metadata["component"]["properties"]
    assert first["dependencies"] == [
        {
            "ref": "pkg:generic/synthetic-application@1.2.3",
            "dependsOn": ["pkg:pypi/sample-lib@4.5.6"],
        },
        {"ref": "pkg:pypi/sample-lib@4.5.6", "dependsOn": []},
    ]


def test_explicit_empty_dependency_inventory_is_valid(tmp_path: Path) -> None:
    manifest = _write_manifest(tmp_path, dependencies=())
    builder = PythonDependencyInventoryBuilder()

    document = builder.to_cyclonedx(builder.read(manifest))

    assert document["components"] == []
    assert document["dependencies"] == [
        {"ref": "pkg:generic/synthetic-application@1.2.3", "dependsOn": []}
    ]


@pytest.mark.parametrize(
    ("project_body", "reason_code"),
    (
        ('version = "1.0"\nrequires-python = ">=3.10"\ndependencies = []', "PROJECT_NAME_REQUIRED"),
        (
            'name = "sample"\nrequires-python = ">=3.10"\ndependencies = []',
            "PROJECT_VERSION_REQUIRED",
        ),
        ('name = "sample"\nversion = "1.0"\ndependencies = []', "REQUIRES_PYTHON_REQUIRED"),
        (
            'name = "sample"\nversion = "1.0"\nrequires-python = ">=3.10"',
            "PROJECT_DEPENDENCIES_REQUIRED",
        ),
        (
            'name = "../sample"\nversion = "1.0"\nrequires-python = ">=3.10"\ndependencies = []',
            "PROJECT_NAME_INVALID",
        ),
    ),
)
def test_rejects_missing_required_project_metadata(
    tmp_path: Path, project_body: str, reason_code: str
) -> None:
    manifest = tmp_path / "pyproject.toml"
    manifest.write_text(f"[project]\n{project_body}\n", encoding="utf-8")

    with pytest.raises(DependencyInventoryValidationError, match=reason_code):
        PythonDependencyInventoryBuilder().read(manifest)


@pytest.mark.parametrize(
    ("declaration", "reason_code"),
    (
        ("sample>=1.0", "DEPENDENCY_EXACT_PIN_REQUIRED"),
        ("sample==1.*", "DEPENDENCY_EXACT_PIN_REQUIRED"),
        ("sample[feature]==1.0", "DEPENDENCY_EXTRAS_REJECTED"),
        ("sample @ https://example.invalid/sample.whl", "DEPENDENCY_URL_REJECTED"),
        ("sample @ file:///tmp/sample.whl", "DEPENDENCY_URL_REJECTED"),
    ),
)
def test_rejects_non_reproducible_dependency_declarations(
    tmp_path: Path, declaration: str, reason_code: str
) -> None:
    manifest = _write_manifest(tmp_path, dependencies=(declaration,))

    with pytest.raises(DependencyInventoryValidationError, match=reason_code):
        PythonDependencyInventoryBuilder().read(manifest)


def test_rejects_dynamic_and_duplicate_dependency_metadata(tmp_path: Path) -> None:
    dynamic = _write_manifest(tmp_path, dependencies=(), dynamic=("dependencies",))
    with pytest.raises(DependencyInventoryValidationError, match="DYNAMIC_INVENTORY_REJECTED"):
        PythonDependencyInventoryBuilder().read(dynamic)

    duplicate = _write_manifest(
        tmp_path,
        dependencies=("sample_lib==1.0", "sample-lib==2.0"),
    )
    with pytest.raises(DependencyInventoryValidationError, match="DUPLICATE_DEPENDENCY"):
        PythonDependencyInventoryBuilder().read(duplicate)


def test_rejects_missing_malformed_large_and_linked_manifests(tmp_path: Path) -> None:
    builder = PythonDependencyInventoryBuilder()
    with pytest.raises(DependencyInventoryValidationError, match="MANIFEST_NOT_FOUND"):
        builder.read(tmp_path / "missing.toml")

    malformed = tmp_path / "malformed.toml"
    malformed.write_text("[project\n", encoding="utf-8")
    with pytest.raises(DependencyInventoryValidationError, match="MANIFEST_PARSE_FAILED"):
        builder.read(malformed)

    large = tmp_path / "large.toml"
    large.write_bytes(b"x" * 1_048_577)
    with pytest.raises(DependencyInventoryValidationError, match="MANIFEST_TOO_LARGE"):
        builder.read(large)

    valid = _write_manifest(tmp_path, dependencies=())
    linked = tmp_path / "linked.toml"
    try:
        linked.symlink_to(valid)
    except OSError:
        pytest.skip("Symlinks are not available on this platform")
    with pytest.raises(DependencyInventoryValidationError, match="MANIFEST_SYMLINK_REJECTED"):
        builder.read(linked)


def test_read_failure_is_safe_and_does_not_expose_local_details(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    manifest = _write_manifest(tmp_path, dependencies=())
    original_read_bytes = Path.read_bytes

    def fail_selected_file(path: Path) -> bytes:
        if path == manifest:
            raise OSError("local user path and operating system detail")
        return original_read_bytes(path)

    monkeypatch.setattr(Path, "read_bytes", fail_selected_file)

    with pytest.raises(DependencyInventoryTechnicalError) as exc_info:
        PythonDependencyInventoryBuilder().read(manifest)

    assert exc_info.value.operation_code == "MANIFEST_READ_FAILED"
    assert "local user path" not in str(exc_info.value)


def test_cli_emits_only_sbom_json_and_safe_errors(tmp_path: Path) -> None:
    manifest = _write_manifest(tmp_path, dependencies=("sample==1.0",))
    stdout = StringIO()
    stderr = StringIO()

    assert main([str(manifest)], stdout=stdout, stderr=stderr) == 0
    payload = json.loads(stdout.getvalue())
    assert payload["metadata"]["component"]["name"] == "synthetic-application"
    assert str(tmp_path) not in stdout.getvalue()
    assert stderr.getvalue() == ""

    error_output = StringIO()
    assert main([str(tmp_path / "missing.toml")], stdout=StringIO(), stderr=error_output) == 2
    assert json.loads(error_output.getvalue()) == {
        "reason_code": "MANIFEST_NOT_FOUND",
        "status": "VALIDATION_ERROR",
    }
    assert str(tmp_path) not in error_output.getvalue()


def test_repository_manifest_generates_expected_direct_inventory() -> None:
    stdout = StringIO()

    assert main(["pyproject.toml"], stdout=stdout, stderr=StringIO()) == 0
    payload = json.loads(stdout.getvalue())

    assert payload["metadata"]["component"]["version"] == "0.1.0"
    assert [component["name"] for component in payload["components"]] == [
        "packaging",
        "psycopg",
        "psycopg-binary",
        "sqlalchemy",
        "tomli",
    ]
    assert all("hashes" not in component for component in payload["components"])


def test_inventory_read_is_read_only(tmp_path: Path) -> None:
    manifest = _write_manifest(tmp_path, dependencies=("sample==1.0",))
    before = (manifest.read_bytes(), manifest.stat().st_mtime_ns, manifest.stat().st_mode)

    PythonDependencyInventoryBuilder().read(manifest)

    after = (manifest.read_bytes(), manifest.stat().st_mtime_ns, manifest.stat().st_mode)
    assert after == before


def _write_manifest(
    root: Path,
    *,
    dependencies: tuple[str, ...],
    dynamic: tuple[str, ...] = (),
) -> Path:
    dependency_lines = ",\n".join(f"    {json.dumps(item)}" for item in dependencies)
    dynamic_line = f"dynamic = {json.dumps(list(dynamic))}\n" if dynamic else ""
    manifest = root / "pyproject.toml"
    manifest.write_text(
        "[project]\n"
        'name = "Synthetic_Application"\n'
        'version = "1.2.3"\n'
        'requires-python = ">=3.10"\n'
        f"{dynamic_line}"
        "dependencies = [\n"
        f"{dependency_lines}\n"
        "]\n",
        encoding="utf-8",
    )
    return manifest
