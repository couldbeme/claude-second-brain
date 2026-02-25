"""Structural tests validating the security-auditor agent and audit command.

These tests ensure the security checklist doesn't regress -- all required
items must be present in the agent definition and audit command.
"""

from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
SECURITY_AUDITOR = REPO_ROOT / "agents" / "security-auditor.md"
AUDIT_COMMAND = REPO_ROOT / "commands" / "audit.md"


def _read(path: Path) -> str:
    return path.read_text()


class TestSecurityAuditorTraditionalItems:
    """Original 6 checklist items must remain present."""

    def test_has_secrets_check(self):
        content = _read(SECURITY_AUDITOR)
        assert "Secrets" in content

    def test_has_injection_check(self):
        content = _read(SECURITY_AUDITOR)
        assert "Injection" in content

    def test_has_auth_check(self):
        content = _read(SECURITY_AUDITOR)
        assert "Authentication" in content or "Authorization" in content

    def test_has_dependencies_check(self):
        content = _read(SECURITY_AUDITOR)
        assert "Dependencies" in content or "dependency" in content.lower()

    def test_has_data_handling_check(self):
        content = _read(SECURITY_AUDITOR)
        assert "Data handling" in content or "data handling" in content

    def test_has_infrastructure_check(self):
        content = _read(SECURITY_AUDITOR)
        assert "Infrastructure" in content


class TestSecurityAuditorLLMItems:
    """New AI/LLM security items must be present."""

    def test_has_prompt_injection_check(self):
        content = _read(SECURITY_AUDITOR)
        assert "Prompt injection" in content or "prompt injection" in content

    def test_has_tool_agent_safety_check(self):
        content = _read(SECURITY_AUDITOR)
        assert "agent safety" in content.lower() or "tool" in content.lower() and "least" in content.lower()

    def test_has_data_exfiltration_check(self):
        content = _read(SECURITY_AUDITOR)
        assert "exfiltration" in content.lower() or "poisoning" in content.lower()

    def test_has_model_supply_chain_check(self):
        content = _read(SECURITY_AUDITOR)
        assert "supply chain" in content.lower() or "provenance" in content.lower()

    def test_references_owasp_llm(self):
        content = _read(SECURITY_AUDITOR)
        assert "OWASP" in content and "LLM" in content


class TestAuditCommandDimensions:
    """The /audit command must include all 6 dimensions."""

    def test_has_security_dimension(self):
        content = _read(AUDIT_COMMAND)
        assert "Security" in content

    def test_has_test_coverage_dimension(self):
        content = _read(AUDIT_COMMAND)
        assert "Test Coverage" in content or "test" in content.lower()

    def test_has_code_quality_dimension(self):
        content = _read(AUDIT_COMMAND)
        assert "Code Quality" in content or "Quality" in content

    def test_has_documentation_dimension(self):
        content = _read(AUDIT_COMMAND)
        assert "Documentation" in content

    def test_has_performance_dimension(self):
        content = _read(AUDIT_COMMAND)
        assert "Performance" in content

    def test_has_ai_llm_security_dimension(self):
        content = _read(AUDIT_COMMAND)
        assert "AI" in content or "LLM" in content

    def test_scorecard_has_six_rows(self):
        """Scorecard table should have 6 dimension rows."""
        content = _read(AUDIT_COMMAND)
        # Count rows in the scorecard table (lines starting with |, excluding header/separator)
        lines = content.split("\n")
        scorecard_rows = [
            line for line in lines
            if line.strip().startswith("| ") and "X/10" in line
        ]
        assert len(scorecard_rows) == 6, f"Expected 6 scorecard rows, got {len(scorecard_rows)}: {scorecard_rows}"
