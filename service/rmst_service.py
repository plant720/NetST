"""Adapter for the bundled native ``netst-rmst`` executable."""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
import subprocess
import sys
from typing import Callable, Optional, Sequence, Tuple

from service.resource_path import application_root


CancelCallback = Optional[Callable[[], bool]]


class RMSTError(ValueError):
    """Raised when RMST inputs, options, or native execution are invalid."""


class RMSTCancelled(RuntimeError):
    """Raised when the caller cancels an RMST calculation."""


@dataclass(frozen=True)
class RMSTOptions:
    method: str = "exact"
    iterations: int = 100
    seed: int = 42
    exclude_ambiguous_sites: bool = True


@dataclass(frozen=True)
class RMSTNode:
    node_id: int
    haplotypes: Tuple[str, ...]
    samples: Tuple[str, ...]
    sequence: str


@dataclass(frozen=True)
class RMSTEdge:
    source: int
    target: int
    distance: int
    edge_type: str
    count: Optional[int] = None
    frequency: Optional[float] = None


@dataclass(frozen=True)
class RMSTResult:
    method: str
    alignment_length: int
    included_site_count: int
    excluded_site_count: int
    nodes: Tuple[RMSTNode, ...]
    edges: Tuple[RMSTEdge, ...]
    completed_iterations: Optional[int] = None
    seed: Optional[int] = None
    warnings: Tuple[str, ...] = ()


def parse_rmst_options(args: Sequence[str]) -> RMSTOptions:
    """Parse the small allow-listed option set emitted by NetST's dialog."""
    method = "exact"
    iterations = 100
    seed = 42
    exclude_ambiguous = True
    seen = set()
    index = 0
    while index < len(args):
        option = args[index]
        if option in seen:
            raise RMSTError(f"Duplicate RMST option: {option}")
        seen.add(option)
        if option == "--netst-include-ambiguous":
            exclude_ambiguous = False
            index += 1
            continue
        if option not in {"--method", "--iterations", "--seed"}:
            raise RMSTError(f"Unsupported RMST option: {option}")
        if index + 1 >= len(args):
            raise RMSTError(f"RMST option requires a value: {option}")
        value = args[index + 1]
        if option == "--method":
            method = value.lower()
            if method not in {"exact", "randomized"}:
                raise RMSTError("RMST method must be 'exact' or 'randomized'")
        elif option == "--iterations":
            iterations = _bounded_integer(value, "iterations", 1, 1_000)
        else:
            seed = _bounded_integer(
                value, "seed", -2_147_483_648, 2_147_483_647
            )
        index += 2
    return RMSTOptions(method, iterations, seed, exclude_ambiguous)


def build_rmst_network(
    haplotype_fasta: str,
    metadata_csv: str,
    output_prefix: str,
    options: RMSTOptions = RMSTOptions(),
    cancel_requested: CancelCallback = None,
) -> RMSTResult:
    """Run the native RMST executable and load its structured result."""
    _check_cancelled(cancel_requested)
    executable = _rmst_executable_path()
    if not os.path.isfile(executable):
        raise RMSTError(
            "Native RMST executable not found: " + executable
            + ". Restore the platform binary under lib or set "
            "NETST_RMST_EXECUTABLE."
        )

    command = [
        executable,
        "--input", os.path.abspath(haplotype_fasta),
        "--metadata", os.path.abspath(metadata_csv),
        "--output", os.path.abspath(output_prefix),
        "--method", options.method,
        "--iterations", str(options.iterations),
        "--seed", str(options.seed),
    ]
    if not options.exclude_ambiguous_sites:
        command.append("--include-ambiguous")

    creationflags = 0
    if sys.platform.startswith("win"):
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    try:
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=creationflags,
        )
    except (OSError, ValueError) as exc:
        raise RMSTError(f"Cannot start native RMST executable: {exc}") from exc

    while True:
        try:
            stdout, stderr = process.communicate(timeout=0.1)
            break
        except subprocess.TimeoutExpired:
            if cancel_requested is not None and cancel_requested():
                process.terminate()
                try:
                    process.wait(timeout=2.0)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
                raise RMSTCancelled("RMST analysis cancelled")

    if process.returncode != 0:
        detail = (stderr or stdout or "unknown native RMST error").strip()
        if detail.startswith("RMST error: "):
            detail = detail[len("RMST error: "):]
        raise RMSTError(detail)

    json_path = os.path.abspath(output_prefix) + "_rmst.json"
    try:
        with open(json_path, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
        return _result_from_payload(payload)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise RMSTError(f"Cannot read native RMST result: {exc}") from exc


def _rmst_executable_path() -> str:
    override = os.environ.get("NETST_RMST_EXECUTABLE", "").strip()
    if override:
        return os.path.abspath(os.path.expanduser(override))

    root = application_root()
    if sys.platform.startswith("win"):
        relative = os.path.join("lib", "win", "netst-rmst.exe")
    elif sys.platform == "darwin":
        relative = os.path.join("lib", "mac_arm64", "netst-rmst")
    else:
        relative = os.path.join("lib", "netst-rmst")
    return os.path.join(root, relative)


def _result_from_payload(payload: dict) -> RMSTResult:
    if payload.get("schema") != "netst.rmst.v1":
        raise RMSTError("Native RMST result has an unsupported schema")
    nodes = tuple(
        RMSTNode(
            node_id=int(node["node_id"]),
            haplotypes=tuple(str(value) for value in node["haplotypes"]),
            samples=tuple(str(value) for value in node["samples"]),
            sequence=str(node["sequence"]),
        )
        for node in payload["nodes"]
    )
    edges = tuple(
        RMSTEdge(
            source=int(edge["source"]),
            target=int(edge["target"]),
            distance=int(edge["distance"]),
            edge_type=str(edge["edge_type"]),
            count=None if edge.get("count") is None else int(edge["count"]),
            frequency=(
                None if edge.get("frequency") is None
                else float(edge["frequency"])
            ),
        )
        for edge in payload["edges"]
    )
    return RMSTResult(
        method=str(payload["options"]["method"]),
        alignment_length=int(payload["alignment_length"]),
        included_site_count=int(payload["included_site_count"]),
        excluded_site_count=int(payload["excluded_site_count"]),
        nodes=nodes,
        edges=edges,
        completed_iterations=(
            None if payload.get("completed_iterations") is None
            else int(payload["completed_iterations"])
        ),
        seed=None if payload.get("seed") is None else int(payload["seed"]),
        warnings=tuple(str(value) for value in payload.get("warnings", ())),
    )


def _bounded_integer(value: str, name: str, minimum: int, maximum: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise RMSTError(f"RMST {name} must be an integer") from exc
    if parsed < minimum or parsed > maximum:
        raise RMSTError(f"RMST {name} must be between {minimum} and {maximum}")
    return parsed


def _check_cancelled(cancel_requested: CancelCallback) -> None:
    if cancel_requested is not None and cancel_requested():
        raise RMSTCancelled("RMST analysis cancelled")
