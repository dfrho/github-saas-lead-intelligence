"""
Dependency signal analyzer.

Parses dependency manifest files (package.json, requirements.txt, pyproject.toml, etc.)
and scores the repo on three signals:
  1. Missing SaaS categories — gaps that represent sales opportunities
  2. Version lag — major version behind on security-sensitive packages
  3. Competitor presence — direct competitor already in deps = strong in-market signal
"""

import json
import re
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class DependencyFlag:
    type: str        # "missing_category" | "version_lag" | "competitor"
    message: str     # human-readable description
    severity: str    # "high" | "medium" | "low"


@dataclass
class DependencyAnalysis:
    score: int                        # 0–100
    flags: list[DependencyFlag]       # detected signals
    detected_packages: list[str]      # all package names found
    ecosystem: str                    # "node" | "python" | "go" | "ruby" | "java" | "unknown"


# ── Package category maps ──────────────────────────────────────────────────
# Maps known package names (lowercase) to SaaS categories they cover.
# Used to detect missing categories.

_PACKAGE_CATEGORIES = {
    # Observability / monitoring
    "prometheus_client": "observability", "prom-client": "observability",
    "opentelemetry-sdk": "observability", "@opentelemetry/sdk-node": "observability",
    "datadog": "observability", "dd-trace": "observability",
    "newrelic": "observability", "elastic-apm-node": "observability",
    "sentry-sdk": "observability", "@sentry/node": "observability",
    "winston": "logging", "pino": "logging", "bunyan": "logging",
    "loguru": "logging", "structlog": "logging", "python-json-logger": "logging",

    # Auth / identity
    "passport": "auth", "passport-jwt": "auth", "passport-local": "auth",
    "jsonwebtoken": "auth", "pyjwt": "auth", "python-jose": "auth",
    "authlib": "auth", "oauthlib": "auth", "social-auth-app-django": "auth",
    "django-allauth": "auth", "flask-login": "auth", "flask-jwt-extended": "auth",
    "bcrypt": "auth", "argon2-cffi": "auth", "passlib": "auth",

    # Messaging / event streaming
    "kafkajs": "messaging", "kafka-python": "messaging", "confluent-kafka": "messaging",
    "amqplib": "messaging", "amqp": "messaging", "pika": "messaging",
    "celery": "messaging", "redis": "messaging", "ioredis": "messaging",
    "bull": "messaging", "bullmq": "messaging", "nats": "messaging",

    # Testing
    "jest": "testing", "mocha": "testing", "vitest": "testing", "cypress": "testing",
    "pytest": "testing", "unittest": "testing", "nose2": "testing",
    "playwright": "testing", "@playwright/test": "testing",

    # Feature flags
    "launchdarkly-node-server-sdk": "feature_flags",
    "launchdarkly-server-sdk": "feature_flags",
    "unleash-client": "feature_flags", "flagsmith": "feature_flags",
    "statsig-py": "feature_flags", "statsig-node": "feature_flags",

    # Payments
    "stripe": "payments", "stripe-python": "payments",
    "braintree": "payments", "paypalrestsdk": "payments",

    # Search
    "algoliasearch": "search", "algoliasearch-helper": "search",
    "elasticsearch": "search", "elasticsearch-py": "search",
    "typesense": "search", "meilisearch": "search",

    # Analytics
    "mixpanel": "analytics", "mixpanel-python": "analytics",
    "amplitude": "analytics", "posthog-node": "analytics", "posthog": "analytics",
    "segment": "analytics", "analytics-node": "analytics",

    # Email / notifications
    "nodemailer": "email", "sendgrid": "email", "@sendgrid/mail": "email",
    "resend": "email", "postmark": "email",
    "twilio": "notifications", "vonage": "notifications",
}

# Categories we consider "expected" for repos above a certain maturity threshold.
# If all are missing, that's a strong gap signal.
_EXPECTED_CATEGORIES = {"logging", "testing"}
_MATURE_REPO_EXPECTED = {"logging", "testing", "observability"}

# ── Version lag detection ──────────────────────────────────────────────────
# Security-sensitive packages and their current major versions.
# Flag if the pinned major version is more than 1 behind.

_SECURITY_PACKAGES = {
    # Python
    "cryptography": 42, "requests": 2, "urllib3": 2, "paramiko": 3,
    "pyjwt": 2, "authlib": 1, "flask": 3, "django": 5, "fastapi": 0,
    # Node
    "jsonwebtoken": 9, "bcrypt": 5, "passport": 0, "express": 4,
    "axios": 1, "node-fetch": 3, "got": 13, "superagent": 9,
    "helmet": 7, "cors": 2,
}

# ── Competitor detection ───────────────────────────────────────────────────
# Maps competitor package names to the vendor category they represent.
# Presence = team is already evaluating this space.

_COMPETITOR_SIGNALS = {
    # Observability competitors
    "dd-trace": "observability (Datadog)", "newrelic": "observability (New Relic)",
    "elastic-apm-node": "observability (Elastic)", "elastic-apm": "observability (Elastic)",
    # Auth competitors
    "auth0": "auth (Auth0)", "passport-auth0": "auth (Auth0)",
    # Payments competitors
    "braintree": "payments (Braintree)", "paypalrestsdk": "payments (PayPal)",
    # Search competitors
    "algoliasearch": "search (Algolia)", "elasticsearch": "search (Elastic)",
    # Feature flags competitors
    "launchdarkly-node-server-sdk": "feature_flags (LaunchDarkly)",
    "launchdarkly-server-sdk": "feature_flags (LaunchDarkly)",
}


# ── Parsers ────────────────────────────────────────────────────────────────

def _parse_package_json(content: str) -> dict[str, str]:
    """Return {name: version_string} from package.json dependencies."""
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        return {}
    packages = {}
    for section in ("dependencies", "devDependencies", "peerDependencies"):
        packages.update(data.get(section, {}))
    return packages


def _parse_requirements_txt(content: str) -> dict[str, str]:
    """Return {name: version_string} from requirements.txt."""
    packages = {}
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("-"):
            continue
        # Handle: package==1.2.3, package>=1.0, package~=1.0, package
        match = re.match(r"^([A-Za-z0-9_\-\.]+)\s*([><=~!]+.*)?$", line)
        if match:
            name = match.group(1).lower().replace("_", "-")
            version = match.group(2) or ""
            packages[name] = version.strip()
    return packages


def _parse_pyproject_toml(content: str) -> dict[str, str]:
    """Return {name: version_string} from pyproject.toml dependencies."""
    import tomllib

    try:
        data = tomllib.loads(content)
    except Exception:
        return {}

    packages: dict[str, str] = {}

    def _add_pep508_list(dep_list: list) -> None:
        """Parse a list of PEP 508 dep strings like 'requests>=2.0, <3'."""
        for dep in dep_list:
            if not isinstance(dep, str):
                continue
            m = re.match(r"^([A-Za-z0-9_\-\.]+)\s*([><=~!,][^;]*)?", dep.strip())
            if m:
                name = m.group(1).lower().replace("_", "-")
                packages[name] = (m.group(2) or "").strip().rstrip(",").strip()

    def _add_poetry_dict(dep_dict: dict) -> None:
        """Parse a Poetry-style {name: version_or_dict} mapping."""
        for name, ver in dep_dict.items():
            if name.lower() == "python":
                continue
            packages[name.lower().replace("_", "-")] = ver if isinstance(ver, str) else ""

    project = data.get("project", {})

    # PEP 621: [project] dependencies
    if isinstance(project.get("dependencies"), list):
        _add_pep508_list(project["dependencies"])

    # PEP 621: [project.optional-dependencies] — each group is a list
    for group_deps in project.get("optional-dependencies", {}).values():
        if isinstance(group_deps, list):
            _add_pep508_list(group_deps)

    tool = data.get("tool", {})

    # [tool.rye] dev-dependencies and [tool.uv] dev-dependencies
    for tool_key in ("rye", "uv"):
        dev_deps = tool.get(tool_key, {}).get("dev-dependencies")
        if isinstance(dev_deps, list):
            _add_pep508_list(dev_deps)

    # Poetry: [tool.poetry.dependencies] and dev-dependencies
    poetry = tool.get("poetry", {})
    if isinstance(poetry.get("dependencies"), dict):
        _add_poetry_dict(poetry["dependencies"])
    if isinstance(poetry.get("dev-dependencies"), dict):
        _add_poetry_dict(poetry["dev-dependencies"])
    for group in poetry.get("group", {}).values():
        if isinstance(group.get("dependencies"), dict):
            _add_poetry_dict(group["dependencies"])

    return packages


def _extract_version_number(version_str: str) -> Optional[int]:
    """Extract the major version integer from a version constraint string."""
    match = re.search(r'(\d+)', version_str)
    return int(match.group(1)) if match else None


def _parse_all_files(dep_files: dict[str, str]) -> tuple[dict[str, str], str]:
    """
    Parse all available dependency files and return merged {name: version} dict
    and detected ecosystem name.
    """
    packages: dict[str, str] = {}
    ecosystem = "unknown"

    if "package.json" in dep_files:
        packages.update(_parse_package_json(dep_files["package.json"]))
        ecosystem = "node"
    if "requirements.txt" in dep_files:
        packages.update(_parse_requirements_txt(dep_files["requirements.txt"]))
        ecosystem = "python"
    if "pyproject.toml" in dep_files:
        packages.update(_parse_pyproject_toml(dep_files["pyproject.toml"]))
        ecosystem = "python"
    if "Pipfile" in dep_files:
        packages.update(_parse_requirements_txt(dep_files["Pipfile"]))
        ecosystem = "python"
    if "go.mod" in dep_files:
        ecosystem = "go"
    if "Gemfile" in dep_files:
        ecosystem = "ruby"
    if "pom.xml" in dep_files or "build.gradle" in dep_files:
        ecosystem = "java"

    return packages, ecosystem


# ── Scoring ────────────────────────────────────────────────────────────────

def analyze_dependencies(dep_files: dict[str, str]) -> DependencyAnalysis:
    """
    Analyze dependency files and return a scored DependencyAnalysis.

    Args:
        dep_files: {filename: content} dict from fetch_dependency_files

    Returns:
        DependencyAnalysis with score, flags, detected packages, and ecosystem
    """
    if not dep_files:
        return DependencyAnalysis(score=0, flags=[], detected_packages=[], ecosystem="unknown")

    packages, ecosystem = _parse_all_files(dep_files)
    package_names = list(packages.keys())
    flags: list[DependencyFlag] = []

    # ── 1. Missing category detection ─────────────────────────────────────
    covered_categories: set[str] = set()
    for pkg_name in package_names:
        category = _PACKAGE_CATEGORIES.get(pkg_name.lower())
        if category:
            covered_categories.add(category)

    # Always flag if logging is missing (universal expectation)
    if "logging" not in covered_categories and ecosystem in ("node", "python"):
        flags.append(DependencyFlag(
            type="missing_category",
            message="No structured logging library detected — teams at scale typically adopt one (Winston, Pino, structlog, loguru)",
            severity="medium",
        ))

    # Flag missing observability if no logging either (stronger signal)
    if "observability" not in covered_categories and ecosystem in ("node", "python"):
        flags.append(DependencyFlag(
            type="missing_category",
            message="No observability/APM library detected (Datadog, New Relic, OpenTelemetry, Sentry) — strong in-market signal",
            severity="high",
        ))

    # Flag missing testing only if completely absent
    if "testing" not in covered_categories and ecosystem in ("node", "python"):
        flags.append(DependencyFlag(
            type="missing_category",
            message="No test framework detected — may indicate early-stage or process-immature team",
            severity="low",
        ))

    # ── 2. Version lag detection ───────────────────────────────────────────
    for pkg_name, version_str in packages.items():
        current_major = _SECURITY_PACKAGES.get(pkg_name.lower())
        if current_major is None:
            continue
        pinned_major = _extract_version_number(version_str)
        if pinned_major is None:
            continue
        lag = current_major - pinned_major
        if lag >= 2:
            flags.append(DependencyFlag(
                type="version_lag",
                message=f"{pkg_name} is {lag} major versions behind (pinned: {pinned_major}, current: {current_major}) — security risk",
                severity="high" if lag >= 3 else "medium",
            ))
        elif lag == 1:
            flags.append(DependencyFlag(
                type="version_lag",
                message=f"{pkg_name} is 1 major version behind (pinned: {pinned_major}, current: {current_major})",
                severity="low",
            ))

    # ── 3. Competitor presence ─────────────────────────────────────────────
    for pkg_name in package_names:
        category = _COMPETITOR_SIGNALS.get(pkg_name.lower())
        if category:
            flags.append(DependencyFlag(
                type="competitor",
                message=f"{pkg_name} detected — team is already evaluating {category}",
                severity="high",
            ))

    # ── Score calculation ──────────────────────────────────────────────────
    # Start at 50 (neutral — we found dep files).
    # High-severity signals are positive (strong in-market indicators).
    # Missing testing is slightly negative (immature team).
    score = 50

    high_flags = sum(1 for f in flags if f.severity == "high")
    medium_flags = sum(1 for f in flags if f.severity == "medium")
    low_flags = sum(1 for f in flags if f.severity == "low")

    # Missing category + competitor presence = team is in-market = raises score
    missing_high = sum(1 for f in flags if f.type == "missing_category" and f.severity == "high")
    competitor_flags = sum(1 for f in flags if f.type == "competitor")
    score += missing_high * 15
    score += competitor_flags * 20

    # Version lag = pain point = raises score
    score += high_flags * 10 + medium_flags * 5

    # Missing testing = early-stage, may not be a buyer yet = slight reduction
    missing_test = sum(1 for f in flags if f.type == "missing_category" and f.severity == "low")
    score -= missing_test * 10

    return DependencyAnalysis(
        score=max(0, min(100, score)),
        flags=flags,
        detected_packages=package_names,
        ecosystem=ecosystem,
    )
