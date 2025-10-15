---
name: AI/Architecture Improvement Proposal
about: Propose a concrete, incremental improvement for AI Nutritionist
title: "[IMP] <short title>"
labels: enhancement, ai, architecture
assignees: ''
---

## Summary

Describe the improvement and the user/business value.

## Rationale

Why this matters (accuracy, reliability, cost, performance, security, accessibility, DX).

## Scope & Impacted Areas

- Services: (e.g., src/services/meal_planning, src/services/messaging)
- Shared packages: (e.g., packages/core/src/events)
- Infra: (e.g., infrastructure/terraform/*)
- Contracts/specs: (e.g., docs/api-reference/*)

## Design Outline

- Approach and alternatives considered
- Boundaries respected (no public API breakage in src/core/*)
- DI, repository, adapters patterns usage
- Observability (structured logs, tracing) plan

## Acceptance Criteria

- [ ] Backward compatible; service boundaries preserved
- [ ] Tests added (unit/integration/e2e/contract as applicable)
- [ ] Coverage unchanged or improved (≥ 80%)
- [ ] Security/privacy reviewed; no secrets committed
- [ ] Docs updated (README/API/architecture)

## Test Plan

- Unit tests:
- Integration tests (moto/mocks):
- E2E/contract tests:

## Risks & Rollback

- Risks:
- Rollback plan:

## Metrics & Validation

- Metrics to monitor (latency, errors, cost, engagement)
- Validation commands:
```bash
make ci
make test-cov
cd infrastructure/terraform && terraform fmt -check && terraform validate
```

## Additional Context

Links to related issues, docs, or prior art.

