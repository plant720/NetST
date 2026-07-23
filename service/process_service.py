"""Cancelable subprocess execution used by the analysis pipeline.

The standard :func:`subprocess.run` API cannot react to a Qt thread's
``requestInterruption()`` while it is waiting.  ``ManagedProcessRunner`` keeps
the same synchronous calling style, but polls a cancellation callback and
owns a process group so descendants can be stopped together with the tool.
"""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from dataclasses import dataclass
from typing import Callable, IO, Mapping, Optional, Sequence, Union


class ProcessCancelled(RuntimeError):
    """Raised after a managed process is cancelled and cleaned up."""


class ProcessTimedOut(RuntimeError):
    """Raised after a managed process exceeds its timeout and is cleaned up."""


@dataclass(frozen=True)
class ManagedProcessResult:
    """Small, stable subset of ``subprocess.CompletedProcess``."""

    args: Sequence[str]
    returncode: int
    stdout: Optional[Union[str, bytes]] = None
    stderr: Optional[Union[str, bytes]] = None


class ManagedProcessRunner:
    """Run a command with timeout, cancellation, and process-tree cleanup."""

    def __init__(self, poll_interval: float = 0.1, terminate_grace: float = 2.0):
        self.poll_interval = max(0.02, poll_interval)
        self.terminate_grace = max(0.1, terminate_grace)

    def run(
        self,
        args: Sequence[str],
        *,
        cwd: Optional[str] = None,
        stdout: Optional[IO] = subprocess.PIPE,
        stderr: Optional[IO] = subprocess.PIPE,
        text: bool = False,
        encoding: Optional[str] = None,
        errors: Optional[str] = None,
        timeout: Optional[float] = None,
        cancel_requested: Optional[Callable[[], bool]] = None,
        env: Optional[Mapping[str, str]] = None,
    ) -> ManagedProcessResult:
        """Run ``args`` and wait while remaining responsive to cancellation.

        A new process group/session is created for every command.  On timeout
        or cancellation the group is terminated, given a short grace period,
        and then force-killed if necessary.
        """
        command = [str(part) for part in args]
        popen_kwargs = {
            "cwd": cwd,
            "stdout": stdout,
            "stderr": stderr,
            "text": text,
            "env": env,
        }
        if encoding is not None:
            popen_kwargs["encoding"] = encoding
        if errors is not None:
            popen_kwargs["errors"] = errors

        if sys.platform.startswith("win"):
            popen_kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
        else:
            popen_kwargs["start_new_session"] = True

        process = subprocess.Popen(command, **popen_kwargs)
        started_at = time.monotonic()

        try:
            while True:
                if cancel_requested is not None and cancel_requested():
                    raise ProcessCancelled(f"Process cancelled: {command[0]}")

                if timeout is not None and time.monotonic() - started_at >= timeout:
                    raise ProcessTimedOut(
                        f"Process timed out after {timeout:g} seconds: {command[0]}"
                    )

                try:
                    captured_stdout, captured_stderr = process.communicate(
                        timeout=self.poll_interval
                    )
                    return ManagedProcessResult(
                        command, process.returncode, captured_stdout, captured_stderr
                    )
                except subprocess.TimeoutExpired:
                    # communicate() can safely be retried and continues draining
                    # PIPEs, avoiding deadlocks from verbose command output.
                    continue
        except BaseException:
            self._terminate_tree(process)
            self._collect_output(process)
            raise

    def _terminate_tree(self, process: subprocess.Popen) -> None:
        if process.poll() is not None:
            return

        if sys.platform.startswith("win"):
            # taskkill /T includes descendants; /F is required for console-less
            # binaries that do not handle CTRL_BREAK_EVENT.
            try:
                subprocess.run(
                    ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=False,
                )
            except OSError:
                process.terminate()
        else:
            try:
                os.killpg(process.pid, signal.SIGTERM)
            except ProcessLookupError:
                return
            except OSError:
                process.terminate()

        try:
            process.wait(timeout=self.terminate_grace)
            return
        except subprocess.TimeoutExpired:
            pass

        if sys.platform.startswith("win"):
            process.kill()
        else:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                return
            except OSError:
                process.kill()

        try:
            process.wait(timeout=self.terminate_grace)
        except subprocess.TimeoutExpired:
            # There is no stronger portable action after SIGKILL/TerminateProcess.
            pass

    @staticmethod
    def _collect_output(process: subprocess.Popen) -> None:
        try:
            process.communicate(timeout=0.5)
        except (subprocess.TimeoutExpired, ValueError):
            pass
