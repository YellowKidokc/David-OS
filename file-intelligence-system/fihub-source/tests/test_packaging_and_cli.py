import json
import tomllib

from file_intelligence_hub.cli import health_main


def test_pyproject_constrains_package_discovery_and_scripts():
    with open("pyproject.toml", "rb") as handle:
        project = tomllib.load(handle)

    assert project["tool"]["setuptools"]["packages"]["find"]["include"] == ["file_intelligence_hub*"]
    scripts = project["project"]["scripts"]
    assert scripts["fihub-api"] == "file_intelligence_hub.cli:api_main"
    assert scripts["fihub-health"] == "file_intelligence_hub.cli:health_main"


def test_health_cli_prints_json(tmp_path, capsys):
    rc = health_main(["--db", str(tmp_path / "hub.sqlite3"), "--repo-root", "."])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert rc == 0
    assert payload["node_id"] == "local"
    assert payload["status"] in {"healthy", "degraded_local", "repairable_local", "needs_peer_assist", "isolated_but_running", "critical"}
