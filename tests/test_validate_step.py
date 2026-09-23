"""The `validate` job's package-request step (#22), run against a fixture connector.

Needs `analitiq-validator` installed at the release under test; the test workflow
installs it with the workflow's own `Install validator` step.
"""
from __future__ import annotations

import os
import pathlib
import shutil

import pytest

from workflow_steps import run_step, step_script

FIXTURE = pathlib.Path(__file__).parent / "fixtures" / "connector-package"
CONNECTOR = "definition/connector.json"
ENDPOINT = "definition/endpoints/tag.json"
EXTRA = "definition/endpoints/extra.json"
SCRIPT = step_script("validate", name="Validate definitions")


@pytest.fixture
def package(tmp_path: pathlib.Path) -> pathlib.Path:
    root = tmp_path / "repo"
    shutil.copytree(FIXTURE, root)
    return root


def validate(root: pathlib.Path, **env: str):
    result = run_step(SCRIPT, root, {**os.environ, **env})
    return result.returncode, result.stdout


def sent(out: str) -> set[str]:
    return {line.strip().removeprefix("sent: ") for line in out.splitlines() if line.strip().startswith("sent: ")}


def test_valid_package_passes_and_lists_every_key_sent(package):
    code, out = validate(package)
    assert code == 0, out
    assert sent(out) == {CONNECTOR, "definition/type-map.json", ENDPOINT}


def test_unresolved_endpoint_native_type_fails_in_one_package_verdict(package):
    endpoint = package / ENDPOINT
    endpoint.write_text(endpoint.read_text().replace('"native_type": "string"', '"native_type": "no_such_native"', 1))
    code, out = validate(package)
    assert code == 1, out
    assert "native-type-unresolved" in out and "no_such_native" in out
    assert out.count("Validated package:") == 1


def test_symlinked_endpoint_file_fails_and_is_not_sent(package, tmp_path):
    # Beside a package that passes on its own, so only the left-out entry can fail the job.
    outside = tmp_path / "outside.json"
    shutil.copy(package / ENDPOINT, outside)
    (package / EXTRA).symlink_to(outside)
    code, out = validate(package)
    assert code == 1, out
    assert f"::error::{EXTRA} is a link" in out
    assert EXTRA not in sent(out)
    assert "passed=True" in out


def test_symlinked_endpoints_directory_fails_and_is_not_descended(package, tmp_path):
    shutil.move(package / "definition/endpoints", tmp_path / "endpoints")
    (package / "definition/endpoints").symlink_to(tmp_path / "endpoints")
    code, out = validate(package)
    assert code == 1, out
    assert "::error::definition/endpoints is a symlinked directory" in out
    assert ENDPOINT not in sent(out)


def test_non_utf8_endpoint_fails_is_not_sent_and_the_validator_still_runs(package):
    (package / EXTRA).write_bytes(b'{"x": "\xff"}')
    code, out = validate(package)
    assert code == 1, out
    assert f"::error::{EXTRA} cannot be read as UTF-8 text" in out
    assert EXTRA not in sent(out)
    assert "passed=True" in out


def test_missing_connector_fails_through_the_validator(package):
    (package / CONNECTOR).unlink()
    code, out = validate(package)
    assert code == 1, out
    assert "package-root-missing" in out


def test_a_secret_location_is_never_opened(package, tmp_path):
    # The endpoint location is made secret. The pattern must be a member location:
    # the validator maps each secret pattern back to its kind.
    site = tmp_path / "site"
    site.mkdir()
    (site / "sitecustomize.py").write_text(
        "from analitiq.contracts.connector_package import ConnectorPackage\n"
        "ConnectorPackage.SECRET_LOCATIONS = frozenset({r'^definition/endpoints/[^/]+\\.json$'})\n")
    # Unreadable, so opening it would surface as a read error.
    (package / ENDPOINT).chmod(0)
    assert not os.access(package / ENDPOINT, os.R_OK), "running as root: an unreadable file cannot prove it was not opened"
    try:
        code, out = validate(package, PYTHONPATH=str(site))
    finally:
        (package / ENDPOINT).chmod(0o644)
    assert code == 0, out
    assert ENDPOINT not in out
    assert sent(out) == {CONNECTOR, "definition/type-map.json"}
