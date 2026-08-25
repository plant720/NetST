"""Versioned, JSON-serializable NetST project manifest models.

The project manifest is intentionally separate from the existing
``*_analysis.json`` result files. It describes how inputs were transformed and
which workflows were run, so a project can be validated and replayed.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List


PROJECT_FORMAT = "netst-project"
PROJECT_SCHEMA_VERSION = 1


class ProjectConfigError(ValueError):
    """Raised when a project manifest is malformed or unsupported."""


@dataclass
class ProjectManifest:
    """Top-level representation of a ``*.netst.json`` project file."""

    format: str = PROJECT_FORMAT
    schema_version: int = PROJECT_SCHEMA_VERSION
    project: Dict[str, Any] = field(default_factory=dict)
    environment: Dict[str, Any] = field(default_factory=dict)
    sources: List[Dict[str, Any]] = field(default_factory=list)
    data_pipeline: Dict[str, Any] = field(default_factory=dict)
    workflow: Dict[str, Any] = field(default_factory=dict)
    artifacts: List[Dict[str, Any]] = field(default_factory=list)
    visualization: Dict[str, Any] = field(default_factory=dict)
    runs: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "ProjectManifest":
        if not isinstance(payload, dict):
            raise ProjectConfigError("Project JSON root must be an object")
        file_format = payload.get("format")
        if file_format != PROJECT_FORMAT:
            raise ProjectConfigError(
                "This JSON is not a NetST project file "
                f"(expected format={PROJECT_FORMAT!r})"
            )
        version = payload.get("schema_version")
        if not isinstance(version, int):
            raise ProjectConfigError("Project schema_version must be an integer")
        if version > PROJECT_SCHEMA_VERSION:
            raise ProjectConfigError(
                f"Project schema version {version} is newer than supported "
                f"version {PROJECT_SCHEMA_VERSION}"
            )
        if version < 1:
            raise ProjectConfigError(f"Unsupported project schema version: {version}")

        def object_field(name: str) -> Dict[str, Any]:
            value = payload.get(name, {})
            if not isinstance(value, dict):
                raise ProjectConfigError(f"Project field {name!r} must be an object")
            return dict(value)

        def list_field(name: str) -> List[Dict[str, Any]]:
            value = payload.get(name, [])
            if not isinstance(value, list) or not all(
                isinstance(item, dict) for item in value
            ):
                raise ProjectConfigError(
                    f"Project field {name!r} must be an array of objects"
                )
            return [dict(item) for item in value]

        manifest = cls(
            format=file_format,
            schema_version=version,
            project=object_field("project"),
            environment=object_field("environment"),
            sources=list_field("sources"),
            data_pipeline=object_field("data_pipeline"),
            workflow=object_field("workflow"),
            artifacts=list_field("artifacts"),
            visualization=object_field("visualization"),
            runs=list_field("runs"),
        )
        manifest.validate()
        return manifest

    def validate(self) -> None:
        """Validate fields that determine replay behavior."""
        if not str(self.project.get("name", "")).strip():
            raise ProjectConfigError("Project name is missing")
        if not self.sources:
            raise ProjectConfigError("Project has no input source")
        sequence_sources = [
            source for source in self.sources if source.get("role") == "sequences"
        ]
        if len(sequence_sources) != 1:
            raise ProjectConfigError(
                "Project must contain exactly one sequence input source"
            )
        for source in self.sources:
            if not str(source.get("path", "")).strip() and not str(
                source.get("relative_path", "")
            ).strip():
                raise ProjectConfigError("An input source has no path")
            digest = source.get("sha256")
            if digest is not None and (
                not isinstance(digest, str)
                or len(digest) != 64
                or any(ch not in "0123456789abcdefABCDEF" for ch in digest)
            ):
                raise ProjectConfigError("An input source has an invalid SHA-256")

        network = self.workflow.get("network")
        if network is not None:
            if not isinstance(network, dict):
                raise ProjectConfigError("workflow.network must be an object")
            allowed = {
                "original_tcs", "modified_tcs", "msn", "mjn", "rmst", "mcan"
            }
            algorithm = network.get("algorithm")
            if algorithm not in allowed:
                raise ProjectConfigError(
                    f"Unsupported network algorithm in project: {algorithm!r}"
                )
            if not isinstance(network.get("parameters", {}), dict):
                raise ProjectConfigError("Network parameters must be an object")
        analyses = self.workflow.get("analyses", [])
        if not isinstance(analyses, list):
            raise ProjectConfigError("workflow.analyses must be an array")
        for analysis in analyses:
            if not isinstance(analysis, dict):
                raise ProjectConfigError("Each saved analysis must be an object")
            if analysis.get("kind") not in {"diversity", "distance", "topology"}:
                raise ProjectConfigError(
                    f"Unsupported saved analysis: {analysis.get('kind')!r}")
            if not isinstance(analysis.get("options", {}), dict):
                raise ProjectConfigError("Saved analysis options must be an object")
