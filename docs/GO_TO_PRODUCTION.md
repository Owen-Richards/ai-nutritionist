# Codex + Copilot Shipping Blueprint

A pragmatic, end-to-end plan to take AI-Nutritionalist to production and profitability, using ChatGPT/Codex for macro design and GitHub Copilot for micro execution.

## 0) Outcomes & Guardrails
- Product KPIs (90 days):
  - WAU = 20k; D7 retention = 35%; weekly adherence = 60% median
  - Free?Paid conversion = 6%; 3-mo LTV = 3× CAC; refund rate = 3%
- Reliability: API SLO 99.9%, p95 latency = 300ms core reads, = 800ms plan writes
- Privacy: consented data only; regional residency; deletion = 7 days
- Cost: COGS/user = $0.18/wk (LLM + SMS + infra) at target scale

## 1) Roles: Codex vs Copilot
- Codex (this chat): system design, specs, data contracts, API definitions, test plans, incident playbooks, PRDs, rollout plans, postmortems.
- Copilot: inline implementations, adapters, serializers, SQL/ORM, glue code, unit tests, small refactors.

Cadence:
- Daily: Codex generates 1–2 specs/TODO blocks ? paste into files; Copilot fills code; run tests.
- Weekly: Codex creates release plan + experiment slate; you ship behind flags.

## 2) Critical Path Backlog (execution-ready)
Track A — Personalization & Plans
- A1 Spec: meal plan pipeline v1 (inputs: profile, prefs, budget, time; outputs: 7-day plan + grocery list) with rule engine first, ML later.
  Implemented via `MealPlanPipeline` (see `src/services/meal_planning/pipeline.py`) combining `PlanCoordinator`, data store, and feature logger.
- A2 API: `POST /v1/plan/generate`, `POST /v1/plan/feedback`, `GET /v1/plan/current`.
  Implemented via `src/api/routes/plan.py` with `PlanCoordinator` orchestration.
- A3 Data: tables `users`, `user_preferences`, `recipes`, `meal_plans`, `meal_feedback`, `pantry_items`.
  In-memory equivalents captured in `data_store.py` and `repository.py` for local dev & contract definition.
- A4 Tests: golden plans for fixtures (vegan, gluten-free, low-budget, 15-min meals).
- A5 ML hook: log features ? warehouse; add offline scorer (not on critical path for GA).
  Feature logging implemented via `FeatureLogger` (`ml_logging.py`) capturing generation metrics for warehouse export.

Track B — Community (SMS-first Crews)
- B1 Templates: daily pulse, weekly challenge, reflection; link to lightweight web pulse card.
- B2 API: `POST /v1/crews/join`, `GET /v1/crews/{id}/pulse`, `POST /v1/reflections`.
- B3 Anonymization: bucket sizes =5 for aggregates; throttle quotes if <5.
- B4 Tests: content rules, opt-in/opt-out, rate limit 1 SMS/min/user.

Track C — Widgets (iOS/Android)
- C1 Widget API: `GET /v1/gamification/summary` ? adherence ring, streak, mini-challenge.
- C2 iOS WidgetKit + Android AppWidget shells with deep links to SMS/web.
- C3 Contract tests for JSON shape + caching headers (ETag, 5–15 min TTL).

Track D — Integrations
- D1 Calendar: Google/Outlook OAuth; create prep/cook events w/ reminders; store `calendar_event_id`.
- D2 Grocery: list generator; export to CSV + partner deeplinks (no hard dependency for GA).
- D3 Fitness: import daily summary (steps, workout) to adjust recovery meals (optional, behind flag).

Track E — Monetization
- E1 Tiers: Free (basic plan + SMS nudges), Plus ($9–$14/mo: adaptive planning + widgets), Pro ($19–$29/mo: crews + calendar + grocery export).
- E2 Billing: Stripe customer + subscription + webhook processors; entitlement middleware.
- E3 Paywall: server-driven; `GET /v1/paywall/config` with copy/price/test bucket.
- E4 Experiments: price points, trial length (7 vs 14 days), nudge frequency; guardrails.

Track F — Data & Analytics
- F1 Event taxonomy: `plan_generated`, `meal_logged`, `nudge_sent`, `nudge_clicked`, `crew_joined`, `reflection_submitted`, `paywall_viewed`, `subscribe_started`, `subscribe_activated`, `churned`.
- F2 Schemas w/ consent flags; PII split from behavioral.
- F3 Warehouse jobs + dashboards: activation funnel, adherence, retention, revenue.

Track G — Reliability, Security, Compliance
- G1 Observability: structured logs, traces, RED metrics; alerts for SLO breaches.
- G2 Rate limiting + abuse protection; per-user + per-IP.
- G3 Secrets management; key rotation; audit logging for access.
- G4 Privacy: DSAR export/delete, region routing, data retention windows.
- G5 Runbooks: incident severities, on-call, rollback checklists.

## 3) File-Level TODOs (paste into code to drive Copilot)
- src/services/plan_service.py
  """
  compute_weekly_plan(user_id: UUID) -> MealPlan
  Inputs: profile, prefs, budget, time windows, pantry.
  Rules: diet constraints, time = max_prep, budget = weekly_budget, variety = 70%.
  Edge cases: empty pantry; allergy conflicts; missing breakfasts.
  Invariants: macros within ±10%; duplicate meals = 2/week.
  """
- src/api/routes/plan.py
  # TODO: POST /v1/plan/generate, POST /v1/plan/feedback, GET /v1/plan/current with auth, idempotency keys, JSON schema validation.
- src/services/community.py
  # TODO: crew pulse aggregation with k-anonymity = 5; redact free-text PII.
- src/monetization/entitlements.py
  # TODO: check_subscription(user)->FeatureSet with cache; fallback to free.
- tests/test_plan_service.py
  # TODO: golden tests for vegan, budget, 15-minute constraints; property tests for macro bounds.

## 4) Data Contracts (OLTP excerpt)
- users(id PK, email pii, region, created_at)
- user_preferences(user_id FK, diet, allergies[], budget_weekly, max_prep_min, grocery_cadence)
- meal_plans(id PK, user_id FK, week_start, items jsonb, total_cost_cents)
- meal_feedback(id PK, user_id FK, meal_id, mood_score int, energy_score int, satiety int, skipped_reason text)
- crews(id PK, name, cohort_key, created_at), crew_members(crew_id, user_id)
- reflections(id PK, user_id, crew_id, text, created_at, pii_redacted bool)
- subscriptions(user_id, tier, status, started_at, renews_at)

## 5) Analytics Events (properties)
- plan_generated { user_id, plan_id, ruleset, est_cost, duration_ms }
- meal_logged { user_id, meal_id, status:eaten|skipped, source:sms|app|widget }
- nudge_sent { user_id, template_id, channel, experiment_id }
- paywall_viewed { user_id, price, variant, source }
- subscribe_activated { user_id, tier, price_usd, coupon, experiment_id }

## 6) Production Readiness Checklist (GA gate)
- Testing: unit = 80% changed lines, integration for APIs, e2e happy paths; red team for abuse flows.
- Observability: dashboards (latency, error rate, saturation), alert runbooks, trace sampling.
- Reliability: idempotency on POSTs, retries with backoff, circuit breakers on vendors.
- Security/Privacy: authN/Z, PII isolation, encryption at rest/in transit, DSAR flows tested, DPA/SCCs with vendors.
- Compliance: consent logging, data retention policies, deletion within SLA.
- Rollout: feature flags, staged cohorts, canary + kill switch, rollback validated.
- Docs: API contracts, on-call runbooks, admin SOPs, PRD/CHANGELOG.

## 7) Monetization Plan & Experiments
- Pricing: start $12.99 Plus, $24.99 Pro; test ±20% via server-driven paywall.
- Trial: 7-day default; experiment 14-day for low-intent cohorts.
- Bundles: annual discount 2 months free; family add-on +40%.
- Affiliates: grocery partners (tagged deeplinks), kitchen gear; 5–10% rev share.
- B2B: employer wellness pilots; crew challenges with aggregated, anonymized reporting.
- Guardrails: hard cap weekly SMS for free tier; high-value features (adaptive plans, calendar) paywalled.

## 8) Launch Plan
- Beta 1 (Internal + friends): core plans, SMS nudges, basic analytics.
- Beta 2 (Closed): crews + widget; start billing in soft mode.
- GA: enable billing; run 2–3 experiments; PR + partner co-marketing.
- Post-GA: model improvements; corporate pilots; expand partners.

## 9) Using Codex + Copilot Daily
- Start of day: ask Codex to produce a spec/TODOs for one Track item; paste TODO/docstrings.
- Code: accept Copilot completions; keep functions small; add types and examples.
- Validate: run tests/linters; if failures, ask Codex for a minimal patch.
- Commit: small diffs with clear titles; Codex drafts PR description and risk notes.

## 10) Executive Scorecard (weekly)
- Activation: % finishing onboarding + first plan
- Engagement: weekly adherence %, D7 retention
- Monetization: paywall view?start?activate; ARPU; churn
- Reliability: SLOs, incidents, cost/user

—
Adapt this blueprint to your current stack; use it as the weekly source of truth for shipping.
