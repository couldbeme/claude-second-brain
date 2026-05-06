"""Self-learning protocol tests — STUB.

Phase 5 build pass implements:

class TestTriggerClassifier:
    # Pure-function tests against tests/fixtures/triggers/*.yaml
    # @pytest.mark.llm-free — runs in CI without LLM invocation
    ...

class TestSelfLearningPipeline:
    # Integration tests: simulate trigger → assert markdown write +
    # audit-log row, using tmp_path fixtures
    # @pytest.mark.llm — mocked-LLM tests (deterministic via fixtures)
    ...

See docs/SELF-LEARNING-TESTS.md for the full test architecture.
"""
