"""The `conformance-gate` decision step, run against minimal repo layouts. Stdlib only."""
from __future__ import annotations

import json
import os
import pathlib

import pytest

from workflow_steps import run_step, step_script

SCRIPT = step_script("conformance-gate", step_id="gate")

PACKAGE = '[project]\nname = "connector-x"\nversion = "1.0.0"\n'
ENTRY_POINT = PACKAGE + '\n[project.entry-points."analitiq.source_connectors"]\nx = "x.connector:X"\n'


def gate(root: pathlib.Path, tmp_path: pathlib.Path):
    """Exit code, log, and the outputs written to GITHUB_OUTPUT."""
    output, summary = tmp_path / "output", tmp_path / "summary"
    result = run_step(SCRIPT, root, {**os.environ, "GITHUB_OUTPUT": str(output), "GITHUB_STEP_SUMMARY": str(summary)})
    lines = output.read_text().splitlines() if output.exists() else []
    return result.returncode, result.stdout, dict(line.split("=", 1) for line in lines)


@pytest.fixture
def repo(tmp_path: pathlib.Path) -> pathlib.Path:
    root = tmp_path / "repo"
    (root / "definition").mkdir(parents=True)
    return root


def connector(root: pathlib.Path, body) -> None:
    (root / "definition" / "connector.json").write_text(body if isinstance(body, str) else json.dumps(body))


def pyproject(root: pathlib.Path, text: str | bytes) -> None:
    path = root / "pyproject.toml"
    path.write_bytes(text) if isinstance(text, bytes) else path.write_text(text)


def test_no_connector_definition_is_not_assessed(repo, tmp_path):
    code, out, outputs = gate(repo, tmp_path)
    assert code == 0, out
    assert outputs == {"run": "false"}
    assert "NOT ASSESSED" in (tmp_path / "summary").read_text()


@pytest.mark.parametrize("body", ["{not json", "[]"], ids=["unparseable", "not-an-object"])
def test_unreadable_connector_definition_fails(repo, tmp_path, body):
    connector(repo, body)
    code, out, outputs = gate(repo, tmp_path)
    assert code != 0 and outputs == {}, out


@pytest.mark.parametrize("body", [{}, {"kind": ""}], ids=["missing", "empty"])
def test_connector_without_a_kind_fails(repo, tmp_path, body):
    connector(repo, body)
    code, out, _ = gate(repo, tmp_path)
    assert code != 0 and "declares no kind" in out, out


def test_unknown_kind_fails_rather_than_skipping(repo, tmp_path):
    connector(repo, {"kind": "Database"})
    code, out, outputs = gate(repo, tmp_path)
    assert code != 0 and "not a connector kind" in out and outputs == {}, out


def test_unparseable_pyproject_fails(repo, tmp_path):
    connector(repo, {"kind": "database"})
    pyproject(repo, "[project\n")
    code, out, _ = gate(repo, tmp_path)
    assert code != 0 and "does not parse" in out, out


def test_pyproject_with_a_bom_fails_with_the_bom_hint(repo, tmp_path):
    connector(repo, {"kind": "database"})
    pyproject(repo, b"\xef\xbb\xbf" + PACKAGE.encode())
    code, out, _ = gate(repo, tmp_path)
    assert code != 0 and "UTF-8 BOM" in out, out


@pytest.mark.parametrize("text, key", [
    ('project = "x"\n', "[project]"),
    (PACKAGE + 'entry-points = "x"\n', "[project.entry-points]"),
    (PACKAGE + 'dynamic = "entry-points"\n', "project.dynamic"),
], ids=["project", "entry-points", "dynamic"])
def test_wrongly_typed_packaging_key_fails(repo, tmp_path, text, key):
    connector(repo, {"kind": "database"})
    pyproject(repo, text)
    code, out, _ = gate(repo, tmp_path)
    assert code != 0 and f"pyproject.toml: {key} must be" in out, out


def test_python_without_a_package_fails(repo, tmp_path):
    connector(repo, {"kind": "api"})
    (repo / "connector.py").write_text("")
    code, out, _ = gate(repo, tmp_path)
    assert code != 0 and "there is no pyproject.toml" in out, out


def test_python_in_a_package_without_an_entry_point_fails(repo, tmp_path):
    connector(repo, {"kind": "database"})
    pyproject(repo, PACKAGE)
    (repo / "connector.py").write_text("")
    code, out, _ = gate(repo, tmp_path)
    assert code != 0 and "declares no connector entry point" in out, out


def test_kind_without_tier1_checks_is_not_assessed(repo, tmp_path):
    connector(repo, {"kind": "api"})
    code, out, outputs = gate(repo, tmp_path)
    assert code == 0, out
    assert outputs == {"run": "false"}
    assert "::warning::Tier-1 conformance NOT ASSESSED" in out


@pytest.mark.parametrize("text, expected", [
    (None, {"run": "true", "install_self": "false", "claims_class": "false"}),
    (PACKAGE, {"run": "true", "install_self": "true", "claims_class": "false"}),
    (ENTRY_POINT, {"run": "true", "install_self": "true", "claims_class": "true"}),
    (PACKAGE.replace('version = "1.0.0"\n', 'version = "1.0.0"\ndynamic = ["entry-points"]\n'),
     {"run": "true", "install_self": "true", "claims_class": "true"}),
], ids=["thin", "package-only", "entry-point", "dynamic-entry-points"])
def test_database_connector_outputs(repo, tmp_path, text, expected):
    connector(repo, {"kind": "database"})
    if text is not None:
        pyproject(repo, text)
    code, out, outputs = gate(repo, tmp_path)
    assert code == 0, out
    assert outputs == expected


def test_a_root_level_json_module_cannot_decide_the_verdict(repo, tmp_path):
    # Without -P, this shadows the stdlib json and reads the database repo as api.
    connector(repo, {"kind": "database"})
    (repo / "json.py").write_text("def loads(_):\n    return {'kind': 'api'}\n")
    pyproject(repo, ENTRY_POINT)
    code, out, outputs = gate(repo, tmp_path)
    assert code == 0, out
    assert outputs["run"] == "true"
