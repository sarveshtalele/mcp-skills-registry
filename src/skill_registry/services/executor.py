"""Execution of skills in isolated subprocesses with a hard timeout.

Each ``python-script`` skill is run in a fresh subprocess via ``_runner.py``. This
gives process-level isolation, a clean import namespace, and a reliable timeout
(the parent kills the child if it overruns). Inputs and outputs cross the boundary
as JSON over stdin/stdout.
"""

from __future__ import annotations

import asyncio
import json
import sys
import time
import uuid
from pathlib import Path

from skill_registry.config import Settings
from skill_registry.logging_config import get_logger
from skill_registry.models import ExecutionResult, ExecutionStatus, ExecutionType
from skill_registry.services.loader import LoadedSkill

_logger = get_logger(__name__)
_RUNNER = Path(__file__).with_name("_runner.py")


class SkillExecutor:
    """Runs skills and produces :class:`ExecutionResult` objects."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def execute(self, skill: LoadedSkill, inputs: dict) -> ExecutionResult:
        """Execute a loaded skill with already-validated inputs."""
        execution_id = f"exec_{uuid.uuid4().hex[:12]}"
        started = time.perf_counter()

        if skill.manifest.execution.type is not ExecutionType.PYTHON_SCRIPT:
            return self._result(
                execution_id,
                skill,
                ExecutionStatus.FAILURE,
                started,
                error=f"execution type '{skill.manifest.execution.type.value}' "
                "is not runnable on the server",
            )

        if not skill.entrypoint_path.is_file():
            return self._result(
                execution_id,
                skill,
                ExecutionStatus.FAILURE,
                started,
                error=f"entrypoint not found: {skill.manifest.execution.script_path}",
            )

        timeout = self._settings.clamp_timeout(skill.manifest.execution.timeout_seconds)
        try:
            envelope = await self._run_subprocess(skill, inputs, timeout)
        except asyncio.TimeoutError:
            return self._result(
                execution_id,
                skill,
                ExecutionStatus.TIMEOUT,
                started,
                error=f"execution exceeded {timeout}s timeout",
            )
        except Exception as exc:  # noqa: BLE001
            _logger.exception("Executor failure for skill '%s'", skill.name)
            return self._result(
                execution_id, skill, ExecutionStatus.FAILURE, started, error=str(exc)
            )

        if "error" in envelope:
            return self._result(
                execution_id,
                skill,
                ExecutionStatus.FAILURE,
                started,
                error=envelope["error"],
            )
        return self._result(
            execution_id,
            skill,
            ExecutionStatus.SUCCESS,
            started,
            output=envelope.get("output", {}),
        )

    async def _run_subprocess(self, skill: LoadedSkill, inputs: dict, timeout: int) -> dict:
        """Spawn the runner subprocess and return its parsed JSON envelope."""
        proc = await asyncio.create_subprocess_exec(
            sys.executable,
            str(_RUNNER),
            str(skill.entrypoint_path),
            skill.manifest.execution.callable_name,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(skill.directory),
        )
        payload = json.dumps(inputs).encode("utf-8")
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(payload), timeout=timeout)
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            raise

        if len(stdout) > self._settings.max_output_bytes:
            return {"error": "skill output exceeded the maximum allowed size"}
        try:
            return json.loads(stdout.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            err = stderr.decode("utf-8", "replace").strip() or "no output from skill"
            return {"error": f"malformed skill output: {err}"}

    @staticmethod
    def _result(
        execution_id: str,
        skill: LoadedSkill,
        status: ExecutionStatus,
        started: float,
        *,
        output: dict | None = None,
        error: str | None = None,
    ) -> ExecutionResult:
        return ExecutionResult(
            execution_id=execution_id,
            skill_name=skill.name,
            status=status,
            output=output,
            error=error,
            duration_ms=round((time.perf_counter() - started) * 1000, 2),
        )
