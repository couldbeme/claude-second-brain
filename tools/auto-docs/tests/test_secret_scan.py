import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from secret_scan import has_secrets, scan


def test_clean_text_no_hits():
    r = scan("feat(audit): land new skill")
    assert r.hits == []
    assert r.safe == "feat(audit): land new skill"


def test_aws_access_key_redacted():
    text = "leaked AKIAIOSFODNN7EXAMPLE here"
    r = scan(text)
    assert any(name == "aws-access-key" for name, _ in r.hits)
    assert "AKIA" not in r.safe
    assert "<REDACTED-aws-access-key>" in r.safe


def test_postgres_url_redacted():
    text = "connection: postgres://user:hunter2@db.internal/app"
    r = scan(text)
    assert any(name == "postgres-url-with-password" for name, _ in r.hits)
    assert "hunter2" not in r.safe


def test_hex40_api_secret_redacted():
    text = "client_secret: " + "a" * 40
    r = scan(text)
    assert any(name == "hex40-api-secret" for name, _ in r.hits)
    assert "a" * 40 not in r.safe


def test_has_secrets_helper():
    assert has_secrets("AKIAIOSFODNN7EXAMPLE")
    assert not has_secrets("nothing to see")
