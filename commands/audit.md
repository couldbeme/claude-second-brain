---
description: Full codebase audit -- security, quality, test coverage, architecture
argument-hint: Optional focus area (security, performance, tests, architecture)
---

# Codebase Audit

Perform a comprehensive audit of the current project. Focus area (if specified): $ARGUMENTS

## Execution

Launch parallel analysis across these dimensions:

### Dimension 1: Security Audit
- Scan for hardcoded secrets, API keys, passwords (check .env files, config files, source code)
- Check dependency versions against known vulnerabilities
- Review authentication/authorization patterns
- Check for SQL injection, XSS, command injection vectors
- Review file permissions and access controls
- Return: severity-ranked list of findings with file:line references

### Dimension 2: Test Coverage & Quality
- Identify untested modules (compare src/ files to test/ files)
- Check test quality: are tests testing behavior or implementation details?
- Look for missing edge case coverage
- Check for flaky test patterns (time-dependent, order-dependent)
- Return: coverage gaps ranked by risk, with specific test suggestions

### Dimension 3: Code Quality & Architecture
- Check for DRY violations and code duplication
- Evaluate module boundaries and coupling
- Review error handling patterns (are errors swallowed? propagated correctly?)
- Check for dead code, unused imports, unreachable branches
- Return: architectural concerns ranked by impact

### Dimension 4: Documentation & Developer Experience
- Check README accuracy (do commands work? is setup complete?)
- Review inline documentation (are complex functions explained?)
- Check CLAUDE.md accuracy against actual project state
- Verify CI/CD pipeline completeness
- Return: documentation gaps ranked by developer impact

### Dimension 5: Performance & Resource Management
- Check for resource leaks (unclosed connections, file handles)
- Review async patterns (missing awaits, blocking calls in async context)
- Check for N+1 query patterns or unbounded loops
- Review memory usage patterns (large object retention, missing cleanup)
- Return: performance concerns ranked by production impact

## Synthesis

After all dimensions are analyzed:
1. Combine findings into a unified report
2. Deduplicate overlapping issues
3. Assign overall severity (Critical / High / Medium / Low)
4. Present top 10 findings with actionable fixes
5. Provide summary scorecard:

| Dimension | Score | Top Issue |
|-----------|-------|-----------|
| Security | X/10 | ... |
| Tests | X/10 | ... |
| Quality | X/10 | ... |
| Docs | X/10 | ... |
| Performance | X/10 | ... |
