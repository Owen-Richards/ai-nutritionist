# AI Nutritionist – Copilot Repository Instructions

Purpose: Help Copilot (and other AI tools) generate safe, high‑quality changes that respect this monorepo’s Clean Architecture, testing, and security standards.

## Overview

- Product: AI Nutritionist — iOS/Android, Web, SMS/WhatsApp interfaces backed by AWS Serverless (Lambda, API Gateway, DynamoDB, S3) and AWS Bedrock (Claude 3 Haiku, Titan) for AI.
- Architecture: Clean/Hexagonal with DI via `packages/core/src/container/` and domain events in `packages/core/src/events/`.
- Monorepo: Services in `src/services/*/`, shared libraries in `packages/*`, infrastructure in `infrastructure/terraform`, tests in `tests/*`.

Authoritative reference: `AGENTS.md` at the repo root. Defer to it when in doubt.

## Hard Rules (Must Follow)

1) Do not break public APIs
- Keep `src/core/*` APIs stable. No signature or model changes without a deprecation path.
- Maintain backward compatibility across services. Respect interfaces in `packages/core/src/interfaces/`.

2) Respect service boundaries and DI
- Keep business logic inside `src/services/<service>/`.
- Use constructor dependency injection; wire through `packages/core/src/container/`.
- Use adapters for AWS integration in `src/adapters/` and repositories for data access.

3) Code style
- Python 3.11+, type hints for all public functions.
- Pydantic for validation/serialization (`src/models/` and `src/models/validation/`).
- Async/await for I/O (DynamoDB, Bedrock, Pinpoint).
- Repository pattern for persistence.

4) Testing and coverage
- Add unit tests for new features and regression tests for bug fixes.
- Keep overall coverage ≥ project threshold (80%+). Never reduce coverage.
- Use `moto` or mocks for AWS in integration tests.

5) Security, privacy, secrets
- No hard‑coded secrets or credentials. Use `src/services/infrastructure/secrets_manager.py`.
- Preserve privacy/security/audit code. Follow `src/security/*` and docs/SECURITY_IMPLEMENTATION.md.
- Enforce input validation and structured error handling (`packages/shared/error-handling/*`).

6) Infrastructure safety
- For Terraform changes: run `terraform fmt` and `terraform validate` under `infrastructure/terraform`.
- Keep environment separation and avoid production‑impacting defaults.

## Preferred Building Blocks

- DI and wiring: `packages/core/src/container/*`
- Domain events and bus: `packages/core/src/events/*`
- Monitoring/observability: `packages/shared/monitoring/*`, `infrastructure/monitoring/*`
- Feature flags: `packages/shared/feature-flags/*`
- Rate limiting: `src/services/infrastructure/rate_limiting/*`
- Data quality & compliance: `src/services/data_quality/*`, `compliance-automation/*`
- Contracts: `src/contracts/*`, tests in `tests/contracts/*`

## AI & Prompt Work

- Use `packages/ai/prompt-framework/*` for prompt templates and evaluation.
- Add/update templates in `packages/ai/prompt-framework/templates/` and tests in `packages/ai/prompt-framework/tests/`.
- Ensure cost awareness and channel constraints (SMS/WhatsApp) when proposing conversational logic.

## Acceptance Gates for Changes

- Tests: `make ci` or `make test` pass; coverage unchanged or improved.
- Security: no new secrets; validation and error handling in place.
- Infra: `terraform fmt -check` and `terraform validate` pass when TF is changed.
- Docs: update README/API/architecture docs when behavior changes.

## Quick Validation Commands

```bash
# Code quality and tests
make ci

# Full test run with coverage
make test-cov

# Terraform validation (run inside infra dir when TF changed)
cd infrastructure/terraform && terraform fmt -check && terraform validate
```

## When Proposing Improvements

- Favor small, reversible changes with clear metrics (reliability, cost, latency, accuracy).
- Keep service boundaries; do not import directly across services.
- Add observability (structured logs, traces) to new flows.
- Provide acceptance criteria and a test plan.

See also: `AGENTS.md`, `docs/AI_GUIDANCE.md`, `docs/COMPREHENSIVE_MONITORING_GUIDE.md`, `docs/COST_PROTECTION_SETUP.md`.

