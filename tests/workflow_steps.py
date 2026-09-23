"""The `run:` scripts of `validate-definitions.yml`, read from the workflow itself.

Tests and the test workflow both take a step's script from here, so what is
graded is the text callers run, never a copy of it.

    python tests/workflow_steps.py <job-id> <step-name>   # print one step's script
"""
from __future__ import annotations

import pathlib
import subprocess
import sys
from collections.abc import Mapping

import yaml

WORKFLOW = pathlib.Path(__file__).resolve().parents[1] / ".github" / "workflows" / "validate-definitions.yml"

# GitHub's command for `shell: bash`, the default for a `run:` step on Linux.
GITHUB_BASH = ["bash", "--noprofile", "--norc", "-eo", "pipefail"]


def step_script(job_id: str, *, name: str | None = None, step_id: str | None = None) -> str:
    """The `run:` text of the one step in `job_id` with that name or id."""
    if (name is None) == (step_id is None):
        raise TypeError("select a step by exactly one of name or step_id")
    jobs = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))["jobs"]
    if job_id not in jobs:
        raise LookupError(f"{WORKFLOW.name} has no job {job_id!r}")
    wanted = ("name", name) if name is not None else ("id", step_id)
    matches = [s for s in jobs[job_id]["steps"] if s.get(wanted[0]) == wanted[1]]
    if len(matches) != 1:
        raise LookupError(f"{WORKFLOW.name} job {job_id!r} has {len(matches)} steps with {wanted[0]} {wanted[1]!r}")
    return matches[0]["run"]


def run_step(script: str, workspace: pathlib.Path, env: Mapping[str, str]) -> subprocess.CompletedProcess[str]:
    """Run `script` as GitHub would, in `workspace`; stdout and stderr together."""
    return subprocess.run(
        [*GITHUB_BASH, "-c", script], cwd=workspace, env={**env, "GITHUB_WORKSPACE": str(workspace)},
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, check=False)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    print(step_script(sys.argv[1], name=sys.argv[2]))
