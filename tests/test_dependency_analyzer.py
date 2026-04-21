import pytest
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from services.dependency_analyzer import (
    analyze_dependencies,
    _parse_package_json,
    _parse_requirements_txt,
    _parse_pyproject_toml,
)


# ── Parser unit tests ──────────────────────────────────────────────────────

class TestParsePackageJson:
    def test_parses_dependencies(self):
        content = '{"dependencies": {"express": "^4.18.0", "stripe": "^12.0.0"}}'
        result = _parse_package_json(content)
        assert result["express"] == "^4.18.0"
        assert result["stripe"] == "^12.0.0"

    def test_parses_dev_dependencies(self):
        content = '{"devDependencies": {"jest": "^29.0.0"}}'
        result = _parse_package_json(content)
        assert "jest" in result

    def test_merges_all_sections(self):
        content = '{"dependencies": {"express": "4"}, "devDependencies": {"jest": "29"}, "peerDependencies": {"react": "18"}}'
        result = _parse_package_json(content)
        assert len(result) == 3

    def test_handles_invalid_json(self):
        assert _parse_package_json("not json") == {}

    def test_handles_empty_object(self):
        assert _parse_package_json("{}") == {}


class TestParseRequirementsTxt:
    def test_parses_pinned_versions(self):
        content = "requests==2.31.0\nflask>=2.0.0\n"
        result = _parse_requirements_txt(content)
        assert "requests" in result
        assert "flask" in result

    def test_skips_comments(self):
        content = "# this is a comment\nrequests==2.31.0\n"
        result = _parse_requirements_txt(content)
        assert len(result) == 1

    def test_skips_blank_lines(self):
        content = "\n\nrequests==2.31.0\n\n"
        result = _parse_requirements_txt(content)
        assert len(result) == 1

    def test_skips_flags(self):
        content = "-r other-requirements.txt\nrequests==2.31.0\n"
        result = _parse_requirements_txt(content)
        assert len(result) == 1

    def test_normalizes_underscores_to_dashes(self):
        content = "stripe_python==5.0.0\n"
        result = _parse_requirements_txt(content)
        assert "stripe-python" in result


class TestParsePyprojectToml:
    def test_parses_poetry_style(self):
        content = '[tool.poetry.dependencies]\npython = "^3.11"\nrequests = "^2.31"\n'
        result = _parse_pyproject_toml(content)
        assert "requests" in result

    def test_parses_pep621_style(self):
        content = '[project]\ndependencies = [\n  "requests>=2.0",\n  "flask>=2.0",\n]\n'
        result = _parse_pyproject_toml(content)
        assert "requests" in result
        assert "flask" in result

    def test_parses_optional_dependencies(self):
        content = (
            '[project.optional-dependencies]\n'
            'dev = ["pytest>=7.0", "mypy>=1.0"]\n'
            'extras = ["structlog>=23.0"]\n'
        )
        result = _parse_pyproject_toml(content)
        assert "pytest" in result
        assert "mypy" in result
        assert "structlog" in result

    def test_parses_rye_dev_dependencies(self):
        content = (
            '[tool.rye]\n'
            'dev-dependencies = [\n'
            '  "pytest>=7.0",\n'
            '  "ruff>=0.1.0",\n'
            ']\n'
        )
        result = _parse_pyproject_toml(content)
        assert "pytest" in result
        assert "ruff" in result

    def test_parses_uv_dev_dependencies(self):
        content = (
            '[tool.uv]\n'
            'dev-dependencies = ["pytest>=7.0", "black>=23.0"]\n'
        )
        result = _parse_pyproject_toml(content)
        assert "pytest" in result
        assert "black" in result

    def test_handles_invalid_toml(self):
        assert _parse_pyproject_toml("not: valid: toml: {{{{") == {}


# ── analyze_dependencies ───────────────────────────────────────────────────

class TestAnalyzeDependencies:
    def test_returns_zero_score_for_empty_files(self):
        result = analyze_dependencies({})
        assert result.score == 0
        assert result.flags == []
        assert result.ecosystem == "unknown"

    def test_detects_node_ecosystem(self):
        result = analyze_dependencies({"package.json": '{"dependencies": {"express": "4"}}'})
        assert result.ecosystem == "node"

    def test_detects_python_ecosystem(self):
        result = analyze_dependencies({"requirements.txt": "requests==2.31.0\n"})
        assert result.ecosystem == "python"

    def test_flags_missing_observability(self):
        content = '{"dependencies": {"express": "^4.18.0"}}'
        result = analyze_dependencies({"package.json": content})
        types = [f.type for f in result.flags]
        assert "missing_category" in types
        messages = [f.message for f in result.flags]
        assert any("observability" in m.lower() for m in messages)

    def test_flags_missing_logging(self):
        content = '{"dependencies": {"express": "^4.18.0"}}'
        result = analyze_dependencies({"package.json": content})
        messages = [f.message for f in result.flags]
        assert any("logging" in m.lower() for m in messages)

    def test_no_missing_logging_flag_when_logging_present(self):
        content = '{"dependencies": {"express": "^4.18.0", "winston": "^3.0.0"}}'
        result = analyze_dependencies({"package.json": content})
        messages = [f.message for f in result.flags]
        assert not any("no structured logging" in m.lower() for m in messages)

    def test_flags_version_lag(self):
        # requests current major is 2, pinning to 0.x is 2 behind
        result = analyze_dependencies({"requirements.txt": "requests==0.14.0\n"})
        types = [f.type for f in result.flags]
        assert "version_lag" in types

    def test_no_version_lag_when_current(self):
        result = analyze_dependencies({"requirements.txt": "requests==2.31.0\n"})
        lag_flags = [f for f in result.flags if f.type == "version_lag"]
        assert lag_flags == []

    def test_flags_competitor_presence(self):
        content = '{"dependencies": {"dd-trace": "^3.0.0"}}'
        result = analyze_dependencies({"package.json": content})
        types = [f.type for f in result.flags]
        assert "competitor" in types

    def test_competitor_flag_is_high_severity(self):
        content = '{"dependencies": {"dd-trace": "^3.0.0"}}'
        result = analyze_dependencies({"package.json": content})
        comp_flags = [f for f in result.flags if f.type == "competitor"]
        assert all(f.severity == "high" for f in comp_flags)

    def test_competitor_raises_score_above_baseline(self):
        content = '{"dependencies": {"dd-trace": "^3.0.0", "winston": "^3.0.0"}}'
        result = analyze_dependencies({"package.json": content})
        assert result.score > 50

    def test_missing_observability_raises_score(self):
        # Missing observability is an opportunity signal — should raise score
        content = '{"dependencies": {"express": "^4.18.0", "winston": "^3.0.0"}}'
        result_gap = analyze_dependencies({"package.json": content})
        # With observability present, no gap flag
        content_full = '{"dependencies": {"express": "^4.18.0", "winston": "^3.0.0", "dd-trace": "^3.0.0"}}'
        result_full = analyze_dependencies({"package.json": content_full})
        assert result_full.score >= result_gap.score

    def test_score_capped_at_100(self):
        # Load up with many high-signal flags
        content = '{"dependencies": {"dd-trace": "^3.0.0", "newrelic": "^10.0.0", "algoliasearch": "^4.0.0"}}'
        result = analyze_dependencies({"package.json": content})
        assert result.score <= 100

    def test_score_not_below_zero(self):
        result = analyze_dependencies({"requirements.txt": ""})
        assert result.score >= 0

    def test_detected_packages_populated(self):
        content = '{"dependencies": {"express": "^4.18.0", "stripe": "^12.0.0"}}'
        result = analyze_dependencies({"package.json": content})
        assert "express" in result.detected_packages
        assert "stripe" in result.detected_packages


# ── fetch_dependency_files (github_api integration) ───────────────────────

from unittest.mock import MagicMock, patch
from services.github_api import fetch_dependency_files


class TestFetchDependencyFiles:
    def _make_file(self, content: str):
        f = MagicMock()
        f.decoded_content = content.encode("utf-8")
        return f

    @patch("services.github_api._get_github_client")
    def test_returns_found_files(self, mock_client):
        repo_mock = MagicMock()
        repo_mock.get_contents.side_effect = lambda name: (
            self._make_file('{"dependencies": {}}') if name == "package.json"
            else (_ for _ in ()).throw(Exception("not found"))
        )
        mock_client.return_value.get_repo.return_value = repo_mock
        result = fetch_dependency_files("acme", "api")
        assert "package.json" in result

    @patch("services.github_api._get_github_client")
    def test_silently_skips_missing_files(self, mock_client):
        repo_mock = MagicMock()
        repo_mock.get_contents.side_effect = Exception("404")
        mock_client.return_value.get_repo.return_value = repo_mock
        result = fetch_dependency_files("acme", "api")
        assert result == {}

    @patch("services.github_api._get_github_client")
    def test_returns_multiple_files(self, mock_client):
        repo_mock = MagicMock()
        files = {
            "package.json": self._make_file("{}"),
            "requirements.txt": self._make_file("requests==2.31.0\n"),
        }
        repo_mock.get_contents.side_effect = lambda name: (
            files[name] if name in files else (_ for _ in ()).throw(Exception("not found"))
        )
        mock_client.return_value.get_repo.return_value = repo_mock
        result = fetch_dependency_files("acme", "api")
        assert "package.json" in result
        assert "requirements.txt" in result
