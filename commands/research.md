---
description: Deep research on a technical topic with web search and synthesis
argument-hint: Topic or question to research
---

# Deep Research

Conduct thorough research on a technical topic and synthesize findings.

## Input

Topic: $ARGUMENTS

## Process

1. **Clarify scope**: What specifically needs to be answered? What is the intended use case? If unclear, ask one round of questions.

2. **Multi-source research**: Launch 3 parallel research tracks:

   **Track A -- Web search (current sources)**:
   Use WebSearch to find:
   - Official documentation
   - Recent blog posts and tutorials (within last 12 months)
   - GitHub repositories and examples
   - Stack Overflow discussions with high-vote answers

   **Track B -- Codebase context**:
   Search the current project for:
   - Existing usage of the technology/pattern
   - Related implementations that could inform the approach
   - Configuration or dependency references

   **Track C -- Comparative analysis**:
   Search for:
   - Alternative approaches to the same problem
   - Benchmarks or performance comparisons
   - Known pitfalls and failure modes

3. **Synthesize findings** into a structured report:

   ## Research Report: [Topic]

   ### Summary
   [2-3 sentence answer to the core question]

   ### Key Findings
   - [Finding 1 with source]
   - [Finding 2 with source]

   ### Recommended Approach
   [Concrete recommendation with reasoning]

   ### Alternatives Considered
   | Approach | Pros | Cons |
   |----------|------|------|

   ### Code Examples
   [Relevant code snippets from research]

   ### Risks & Gotchas
   - [Known issue 1]
   - [Known issue 2]

   ### Sources
   - [URL 1 -- description]
   - [URL 2 -- description]

4. **Ask**: Does this answer your question, or should I dig deeper into a specific aspect?
