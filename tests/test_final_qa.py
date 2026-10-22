"""Automated final QA assertions verifying environment placeholders, data safety,
and submission readiness contracts."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_env_example_has_only_safe_placeholders():
    """Verify .env.example contains only non-secret placeholders and safe defaults."""
    env_example = (ROOT / ".env.example").read_text(encoding="utf-8")
    lines = [line.strip() for line in env_example.splitlines() if line.strip() and not line.startswith("#")]
    parsed = dict(line.split("=", 1) for line in lines)

    # Required environment keys must exist
    assert "GNANI_API_KEY" in parsed
    assert "JWT_SECRET" in parsed
    assert "GNANI_CALL_LIMIT" in parsed
    assert "OWNER_EMAIL" in parsed
    assert "DAILY_CALL_CAP_PER_USER" in parsed
    assert "DATA_DIR" in parsed
    assert "TRUST_PROXY" in parsed

    # Sensitive values must contain only placeholders
    assert parsed["GNANI_API_KEY"] == "your-key-here"
    assert parsed["JWT_SECRET"] == "generate-one-with-the-command-above"
    assert parsed["OWNER_EMAIL"] == "you@example.com"
    assert parsed["DEMO_INVITE_CODE"] == ""
    assert parsed["TRUST_PROXY"] == "0"


def test_gitignore_protects_local_data_and_secrets():
    """.gitignore must protect secrets, local data directories, and generated artifacts."""
    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
    ignored_patterns = {line.strip() for line in gitignore.splitlines() if line.strip() and not line.startswith("#")}

    assert ".env" in ignored_patterns
    assert ".venv/" in ignored_patterns
    assert "data/*" in ignored_patterns
    assert "!data/default_phrases_*.txt" in ignored_patterns
    assert "logs/" in ignored_patterns
    assert "web/node_modules/" in ignored_patterns
    assert "web/dist/" in ignored_patterns
    assert "web/certs/" in ignored_patterns
