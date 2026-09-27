---
name: frontend-testing
description: Validate frontend changes with the repository's existing lint, type-check, test, and build workflows.
---

# Frontend testing

- Inspect the package manifest and existing tests first; use the project's established scripts rather than introducing a new test tool.
- Run focused tests for the changed component or behavior, then the relevant type-check, lint, or build command when available.
- Cover user-visible behavior: initial, loading, empty, error, success, disabled, and keyboard interaction states as applicable.
- Prefer accessible role/name queries and observable behavior over implementation-detail assertions.
- For responsive changes, inspect the important narrow and wide layouts, including long labels and error text.
- If the repository has no frontend test/build tooling, state that clearly and perform the available checks without adding a framework solely for this task.
