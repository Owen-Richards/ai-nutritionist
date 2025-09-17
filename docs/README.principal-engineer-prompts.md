# Principal Engineer Prompt Playbook

Curated prompt patterns to help a FAANG-level principal engineer drive the AI Nutritionalist platform from idea to production. Each entry includes when to use it, the levers it pulls, and the outcomes it expects.

## 1. North-Star Architecture Charter
**Use when:** Kicking off a new initiative or revisiting the strategic roadmap.

```
Act as a principal engineer defining the north-star architecture for an AI-powered nutrition coaching platform that must ship to production within two quarters. Deliver:
1. A layered architecture diagram description covering client apps (mobile, SMS, widgets), API gateway, services (personalization, community, notifications), data stores, ML pipelines, and analytics.
2. A maturity matrix outlining MVP, v1, and v2 capabilities, including compliance (HIPAA/GDPR), observability, and incident response.
3. A risk register with mitigations across scalability, privacy, vendor lock-in, and model drift.
4. A 90-day execution roadmap that sequences architecture spikes, build milestones, and launch-readiness gates.
Output must be concise, actionable, and ready for director/stakeholder review.
```

## 2. Productionization Readiness Audit
**Use when:** Assessing whether a feature is fit for launch.

```
You are the DRI for production readiness. Audit the AI Nutritionist release candidate that introduces community crews and adaptive meal planning. Produce:
1. Release checklist status across testing (unit/integration/e2e), data privacy reviews, red-team results, SLOs, alerts, rollout plan, and documentation sign-offs.
2. Gaps prioritized by severity, with owners and remediation timelines.
3. Launch decision recommendation (Go, No-Go, Conditional Go) with clear contingencies.
Ensure findings are formatted for an exec production review meeting.
```

## 3. Data Contract Blueprint
**Use when:** Standardizing data collection for personalization and compliance.

```
Draft a data contract for the AI Nutritionist platform that captures user profile, behavioral signals, health metrics, and community engagement data. Include:
1. Schema tables with field names, types, validation rules, retention, and consent flags.
2. Data lineage from ingestion sources (mobile, SMS, integrations) to storage (OLTP, warehouse, feature store) and downstream consumers.
3. Privacy impact assessment: access controls, anonymization strategy, region routing, deletion workflows.
4. Monitoring SLAs for data freshness, quality, and drift.
Deliver in a format consumable by data engineering and privacy teams.
```

## 4. Cross-Platform Client Launch Plan
**Use when:** Coordinating multi-surface experiences (SMS, mobile app, widgets).

```
Create a cross-platform launch plan for releasing community-driven habit tracking across SMS, iOS/Android apps, and home-screen widgets. Provide:
1. Surface-specific feature scopes, UX guardrails, and accessibility criteria.
2. Dependency map covering backend contracts, feature flags, analytics events, and release trains.
3. Rollout choreography with phased cohorts, kill-switch strategy, and telemetry read-outs.
4. Post-launch operational plan: dashboards, on-call rotation updates, and feedback loops.
Keep the plan precise enough for TPM and release engineering execution.
```

## 5. ML System Ops Guide
**Use when:** Formalizing machine learning lifecycle.

```
As principal engineer overseeing ML ops, write the operating guide for personalization models (meal recommendation, adherence prediction). Cover:
1. Training pipeline architecture (data prep, labeling, feature store, training jobs, model registry).
2. Deployment topology (batch vs real-time scoring, AB testing harness, shadow traffic).
3. Monitoring stack (drift detection, bias evaluation, business KPI alignment) with alert thresholds.
4. Incident playbooks for model rollback, hotfixes, and audit logging.
Tailor the guide for SRE and applied science teams collaborating on 24/7 support.
```

## 6. Vendor & Partnership Due Diligence Prompt
**Use when:** Evaluating third-party integrations (grocery delivery, health data).

```
Lead the technical diligence for integrating with a grocery fulfillment partner. Deliver:
1. API capability comparison (Instacart vs Amazon Fresh vs Walmart) with auth, rate limits, SLAs, and webhooks.
2. Security review: data sharing scope, encryption, breach history, compliance alignment.
3. Operational risk analysis: resilience patterns, fallback flows, commercial contingencies.
4. Recommendation memo with phased rollout plan and success metrics.
Target audience: finance, legal, product leadership.
```

## 7. Cost-to-Serve Optimization Brief
**Use when:** Reducing unit economics without sacrificing user value.

```
Generate a cost optimization plan for the AI Nutritionist service. Include:
1. Current cost stack (compute, storage, messaging, integrations, human-in-the-loop) with monthly burn.
2. Prioritized savings plays: architectural adjustments, reserved instances, vendor renegotiations.
3. Impact analysis on latency, reliability, and user experience.
4. Decision matrix to present at the quarterly business review.
Keep recommendations data-backed and implementation-ready.
```

## 8. Privacy & Compliance Review Prompt
**Use when:** Preparing for external audits or regulatory reviews.

```
Prepare the privacy and compliance dossier for the AI Nutritionist platform ahead of a HIPAA/GDPR audit. Provide:
1. System inventory with data classification, residency, and encryption posture.
2. Access governance summary: RBAC, audit trails, least privilege reviews, third-party access.
3. Incident response readiness: past incidents, tabletop outcomes, breach notification plan.
4. Open risks and remediation roadmap.
Format as an executive-ready briefing with appendices for auditors.
```

## 9. Community Health & Safety Framework
**Use when:** Ensuring community features stay supportive and safe.

```
Define the community health framework for crew-based nutrition coaching. Output:
1. Behavior guidelines, automated moderation rules, and escalation runbooks.
2. Tooling requirements: content filters, report flows, human reviewer interfaces, analytics.
3. Trust metrics (positive interactions, churn reasons, incident rates) and alert thresholds.
4. Integration points with privacy/legal for sensitive data handling.
Provide enough depth for policy, product, and engineering to align quickly.
```

## 10. Revenue Strategy Workshop Prompt
**Use when:** Aligning monetization with product vision.

```
Facilitate a revenue strategy workshop for the AI Nutritionist product trio. Deliver:
1. Segmented monetization opportunities (B2C tiers, corporate wellness, affiliate commerce, coach marketplace).
2. Technical implications for billing, entitlements, and reporting pipelines.
3. Experiment roadmap: hypotheses, measurement plans, guardrails, and rollout cadence.
4. Alignment memo summarizing decisions, open questions, and owner assignments.
Keep tone pragmatic, highlighting trade-offs and execution risks.
```

---
Use these prompts as starting points; tailor them with live telemetry, stakeholder input, and organizational constraints before execution.

## 11. Codex + Copilot Execution Cadence
Use this cadence to accelerate delivery while maintaining quality.

```
Daily
- Ask Codex: generate spec + TODOs for one backlog item.
- Paste TODOs/docstrings; use Copilot to implement in small, typed functions.
- Run tests/linters; ask Codex for focused patches on failures.
- Commit small diffs; Codex drafts PR summary + risks.

Weekly
- Ask Codex: create release plan, experiment slate, and rollout gates.
- Ship behind flags; monitor dashboards; run retros.

Reference
- Shipping Blueprint: docs/GO_TO_PRODUCTION.md
```
