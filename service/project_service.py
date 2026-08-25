"""Read, write, validate and fingerprint NetST project manifests."""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
import platform
import re
import shutil
import sys
import tempfile
from typing import Any, Dict, Iterable, Optional, Tuple

from model.project_config import ProjectConfigError, ProjectManifest
from model.taxon_data import TaxonData
from model.trait_schema import TraitDefinition, TraitSchema


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def sha256_file(path: str, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        while True:
            chunk = handle.read(chunk_size)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def sequence_sha256(sequence: str) -> str:
    return hashlib.sha256(str(sequence).encode("utf-8")).hexdigest()


def source_reference(
    path: str,
    *,
    role: str,
    file_format: str,
    project_directory: Optional[str] = None,
    options: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    absolute = os.path.abspath(path)
    if not os.path.isfile(absolute):
        raise ProjectConfigError(f"Input file does not exist: {absolute}")
    reference: Dict[str, Any] = {}
    if project_directory:
        project_root = os.path.abspath(project_directory)
        try:
            if os.path.commonpath((
                os.path.realpath(project_root), os.path.realpath(absolute)
            )) != os.path.realpath(project_root):
                raise ProjectConfigError(
                    f"Project input is outside the project directory: {absolute}")
            relative = os.path.relpath(absolute, project_root)
        except ValueError as exc:
            raise ProjectConfigError(
                f"Unable to create a project-relative input path: {absolute}"
            ) from exc
        # JSON paths always use forward slashes, including on Windows.
        reference["relative_path"] = relative.replace(os.sep, "/")
    else:
        # Kept for loading and migrating schema-v1 projects created before
        # project-local source copies were introduced. New application code
        # always supplies project_directory and therefore writes no absolute
        # source path to the JSON manifest.
        reference["path"] = absolute
    stat = os.stat(absolute)
    reference.update({
        "role": str(role),
        "format": str(file_format).lower(),
        "sha256": sha256_file(absolute),
        "size": stat.st_size,
        "modified_ns": stat.st_mtime_ns,
        "options": json_compatible(options or {}),
    })
    return reference


def copy_source_to_project(path: str, project_directory: str, role: str) -> str:
    """Copy an imported source into ``inputs/<role>`` inside a project.

    Existing byte-identical files are reused. A short content hash is added to
    the filename only when a different file already occupies the same target,
    so repeated imports are stable while basename collisions remain safe.
    """
    source = os.path.abspath(path)
    if not os.path.isfile(source):
        raise ProjectConfigError(f"Input file does not exist: {source}")
    project_root = os.path.abspath(project_directory)
    role_directory = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(role)).strip("._")
    if not role_directory:
        role_directory = "source"
    target_directory = os.path.join(project_root, "inputs", role_directory)
    os.makedirs(target_directory, exist_ok=True)

    basename = os.path.basename(source) or "source.dat"
    destination = os.path.join(target_directory, basename)
    source_digest = sha256_file(source)

    try:
        if os.path.exists(destination) and os.path.samefile(source, destination):
            return destination
    except OSError:
        pass

    if os.path.isfile(destination):
        if sha256_file(destination) == source_digest:
            return destination
        stem, extension = os.path.splitext(basename)
        destination = os.path.join(
            target_directory, f"{stem}-{source_digest[:12]}{extension}")
        if os.path.isfile(destination) and sha256_file(destination) == source_digest:
            return destination

    descriptor, temporary = tempfile.mkstemp(
        prefix=".netst-source-", suffix=".tmp", dir=target_directory)
    os.close(descriptor)
    try:
        shutil.copy2(source, temporary)
        os.replace(temporary, destination)
    except Exception:
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise
    return destination


def managed_source_reference(
    path: str,
    *,
    role: str,
    file_format: str,
    project_directory: str,
    options: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Copy a source into the project and return a portable reference."""
    managed_path = copy_source_to_project(path, project_directory, role)
    return source_reference(
        managed_path,
        role=role,
        file_format=file_format,
        project_directory=project_directory,
        options=options,
    )


def resolve_source_path(source: Dict[str, Any], manifest_path: str) -> str:
    """Resolve a source using manifest-relative path first, then absolute path."""
    manifest_dir = os.path.dirname(os.path.abspath(manifest_path))
    relative = str(source.get("relative_path", "")).strip()
    if relative:
        # A portable project source must stay inside the directory being
        # transferred. Reject absolute paths and ``..`` traversal from an
        # untrusted manifest rather than reading arbitrary local files.
        normalized = relative.replace("\\", os.sep).replace("/", os.sep)
        if not os.path.isabs(normalized):
            candidate = os.path.abspath(os.path.join(manifest_dir, normalized))
            try:
                contained = os.path.commonpath((
                    os.path.realpath(manifest_dir), os.path.realpath(candidate)
                )) == os.path.realpath(manifest_dir)
            except ValueError:
                contained = False
            if contained and os.path.isfile(candidate):
                return candidate
    raw_path = str(source.get("path", "")).strip()
    if raw_path:
        absolute = os.path.abspath(raw_path)
        if os.path.isfile(absolute):
            return absolute
    return ""


def verify_source(
    source: Dict[str, Any], manifest_path: str
) -> Tuple[str, Optional[str]]:
    path = resolve_source_path(source, manifest_path)
    if not path:
        return "", "missing"
    expected = str(source.get("sha256", "")).lower()
    if expected and sha256_file(path).lower() != expected:
        return path, "hash_mismatch"
    return path, None


def serialize_trait_schema(schema: TraitSchema) -> Dict[str, Any]:
    return {
        "definitions": [asdict(definition) for definition in schema.ordered()],
        "group": schema.group().name if schema.group() is not None else None,
    }


def deserialize_trait_schema(payload: Dict[str, Any]) -> TraitSchema:
    if not isinstance(payload, dict):
        raise ProjectConfigError("Trait schema must be an object")
    definitions_payload = payload.get("definitions", [])
    if not isinstance(definitions_payload, list):
        raise ProjectConfigError("Trait schema definitions must be an array")
    definitions = []
    allowed = set(TraitDefinition.__dataclass_fields__)
    for entry in definitions_payload:
        if not isinstance(entry, dict):
            raise ProjectConfigError("Trait schema definition must be an object")
        try:
            definitions.append(TraitDefinition(**{
                key: value for key, value in entry.items() if key in allowed
            }))
        except (TypeError, ValueError) as exc:
            raise ProjectConfigError(f"Invalid trait definition: {exc}") from exc
    schema = TraitSchema(definitions)
    group = payload.get("group")
    if group:
        try:
            schema.set_group(str(group))
        except ValueError as exc:
            raise ProjectConfigError(str(exc)) from exc
    return schema


def snapshot_taxons(taxons: Iterable[TaxonData]) -> list:
    """Store editable row state without embedding potentially huge sequences."""
    result = []
    for index, taxon in enumerate(taxons):
        result.append({
            "row": index,
            "id": taxon.id,
            "name": taxon.name,
            "sequence_sha256": sequence_sha256(taxon.sequence),
            "selected": bool(taxon.selected),
            "quantity": taxon.quantity,
            "organism": taxon.organism,
            "discrete_traits": taxon.discrete_traits,
            "continuous_traits": taxon.continuous_traits,
            "traits": dict(taxon.traits),
        })
    return result


def apply_taxon_snapshot(taxons: list, snapshot: list) -> None:
    """Apply saved editable fields after verifying row count and sequences."""
    if not isinstance(snapshot, list) or len(taxons) != len(snapshot):
        raise ProjectConfigError(
            "Imported sequence count does not match the saved project snapshot"
        )
    for index, (taxon, saved) in enumerate(zip(taxons, snapshot)):
        if not isinstance(saved, dict):
            raise ProjectConfigError(f"Saved sample row {index + 1} is invalid")
        expected = str(saved.get("sequence_sha256", ""))
        if expected and sequence_sha256(taxon.sequence) != expected:
            raise ProjectConfigError(
                f"Sequence content differs from the saved project at row {index + 1}"
            )
        taxon.id = int(saved.get("id", taxon.id))
        taxon.name = str(saved.get("name", taxon.name))
        taxon.selected = bool(saved.get("selected", True))
        taxon.quantity = int(saved.get("quantity", taxon.quantity))
        taxon.organism = str(saved.get("organism", taxon.organism))
        taxon.discrete_traits = str(saved.get("discrete_traits", ""))
        taxon.continuous_traits = str(saved.get("continuous_traits", "0"))
        traits = saved.get("traits", {})
        if not isinstance(traits, dict):
            raise ProjectConfigError(f"Saved traits at row {index + 1} are invalid")
        taxon.traits = {str(key): str(value) for key, value in traits.items()}


def runtime_environment() -> Dict[str, Any]:
    return {
        "netst_version": os.environ.get("NETST_VERSION", "development"),
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "frozen": bool(getattr(sys, "frozen", False)),
    }


def json_compatible(value: Any) -> Any:
    if is_dataclass(value):
        return json_compatible(asdict(value))
    if isinstance(value, dict):
        return {str(key): json_compatible(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [json_compatible(item) for item in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def save_project(manifest: ProjectManifest, destination: str) -> None:
    manifest.validate()
    destination = os.path.abspath(destination)
    directory = os.path.dirname(destination)
    os.makedirs(directory, exist_ok=True)
    payload = manifest.to_dict()

    # Defensive portability for callers outside MainForm: absolute-only source
    # references are copied into this project before serialization. If a
    # relative path already exists, the legacy absolute fallback is omitted.
    portable_sources = []
    for source in payload.get("sources", []):
        entry = dict(source)
        relative = str(entry.get("relative_path", "")).strip()
        absolute = str(entry.get("path", "")).strip()
        if relative:
            entry["relative_path"] = relative.replace("\\", "/")
            entry.pop("path", None)
        elif absolute:
            portable = managed_source_reference(
                absolute,
                role=str(entry.get("role", "source")),
                file_format=str(entry.get("format", "file")),
                project_directory=directory,
                options=(entry.get("options")
                         if isinstance(entry.get("options"), dict) else {}),
            )
            for key in ("path", "relative_path", "sha256", "size", "modified_ns",
                        "role", "format", "options"):
                entry.pop(key, None)
            entry.update(portable)
        portable_sources.append(entry)
    payload["sources"] = portable_sources

    project = payload.get("project", {})
    output_path = str(project.get("output_path", "")).strip()
    if output_path and os.path.isabs(output_path):
        project["output_path"] = os.path.relpath(
            output_path, directory).replace(os.sep, "/")

    def make_record_path_relative(record: Dict[str, Any]) -> None:
        relative_path = str(record.get("relative_path", "")).strip()
        absolute_path = str(record.get("path", "")).strip()
        if relative_path:
            record["relative_path"] = relative_path.replace("\\", "/")
            record.pop("path", None)
        elif absolute_path:
            record["relative_path"] = os.path.relpath(
                os.path.abspath(absolute_path), directory).replace(os.sep, "/")
            record.pop("path", None)

    for artifact in payload.get("artifacts", []):
        make_record_path_relative(artifact)
    visualization = payload.get("visualization", {})
    for image_export in visualization.get("image_exports", []):
        if isinstance(image_export, dict):
            make_record_path_relative(image_export)

    file_descriptor, temporary = tempfile.mkstemp(
        prefix=".netst-project-", suffix=".tmp", dir=directory
    )
    try:
        with os.fdopen(file_descriptor, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(
                payload, handle, ensure_ascii=False, indent=2,
                allow_nan=False,
            )
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, destination)
    except Exception:
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise


def load_project(path: str) -> ProjectManifest:
    try:
        with open(path, "r", encoding="utf-8-sig") as handle:
            payload = json.load(handle)
    except json.JSONDecodeError as exc:
        raise ProjectConfigError(f"Invalid project JSON: {exc}") from exc
    except OSError as exc:
        raise ProjectConfigError(f"Unable to read project file: {exc}") from exc
    return ProjectManifest.from_dict(payload)
