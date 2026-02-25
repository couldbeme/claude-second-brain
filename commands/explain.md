---
description: Explain a codebase, component, or concept in depth
argument-hint: What to explain (file path, module name, concept, or "whole project")
---

# Codebase Explainer

Provide a clear, structured explanation of the specified code or concept.

## Input

Target: $ARGUMENTS

## Process

1. **Identify scope**: Is this a single file, a module, a concept, or the whole project?

2. **For a file or module**: Analyze the code to:
   - Trace the execution flow from entry points to outputs
   - Map dependencies (what it uses, what uses it)
   - Identify the design patterns in use

3. **Read the key files** identified.

4. **Build the explanation** at three levels:

   ### High Level (for someone new to the project)
   - What does this code do? (1-2 sentences)
   - Where does it fit in the overall architecture?
   - What are the main inputs and outputs?

   ### Medium Level (for a developer working on it)
   - Key classes/functions and their responsibilities
   - Data flow diagram (ASCII)
   - Important design decisions and why they were made
   - How to extend or modify it

   ### Detail Level (for debugging)
   - Critical code paths with file:line references
   - Error handling approach
   - State management
   - Performance characteristics
   - Known quirks or tech debt

5. **Ask**: Would you like me to go deeper into any specific part?
