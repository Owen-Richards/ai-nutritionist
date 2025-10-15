# AI Nutritionist Assistant Documentation

## Prerequisites

- Python 3.11 or higher
- AWS SAM CLI
- AWS Account with appropriate permissions
- Node.js (for some development tools)

## Quick Start Checklist

1. Install Python 3.11+ and AWS SAM CLI.
2. Create a virtual environment and install dependencies (`pip install -r requirements.txt`).
3. Duplicate `.env.template` to `.env` and fill in:
   - `BEDROCK_REGION`
   - `AWS_SMS_CONFIGURATION_SET`
   - `AWS_SMS_ORIGINATION_IDENTITY`
   - DynamoDB table names / ARNs (or use Parameter Store references).
4. Run local tests: `pytest tests -q`.
5. Deploy with `sam build && sam deploy --guided`.

## Domain Overview

- `services/messaging` – channel orchestration backed by AWS End User Messaging, Telegram, and Messenger adapters.
- `services/meal_planning` � rule engine, optimisation pipeline, and feedback ingestion.
- `services/nutrition` � consolidated nutrition analytics and insight generation.
- `services/personalization` � preference storage, user profiling, and adaptive learning.
- `services/infrastructure` � Bedrock AI integration, caching, resilience, observability, agents.

## Request Flow

1. Incoming messages reach API Gateway (HTTPS endpoint).
2. The Universal Lambda handler normalises events and consults the Bedrock reasoning agent.
3. Actions are routed to domain services (meal planning, nutrition, subscription).
4. Responses are formatted and delivered via AWS End User Messaging or fallback channels.
5. State updates (profiles, plans, usage) are persisted in DynamoDB with audit logging.

## Deployment Considerations

- **Messaging**: configure AWS End User Messaging for both outbound (SMS/WhatsApp) and inbound (SNS) flows. Update the origination pool and account-level settings before traffic.
- **Secrets**: store API keys and credentials in AWS Systems Manager Parameter Store (`/{env}/messaging/...`).
- **Observability**: enable CloudWatch dashboards and X-Ray tracing through the `services/infrastructure/observability` utilities.
- **Costs**: `services/business/cost_tracking.py` tracks AWS End User Messaging, DynamoDB, and Lambda usage for each user and surface area.

## Reasoning Agent

`services/infrastructure/agent.py` wraps Amazon Bedrock Titan Text to orchestrate between direct responses and tool calls. The universal handler evaluates the decision and delegates to meal planning, nutrition insight, or subscription helpers accordingly.

## Privacy & Compliance Controls

- Consent capture and DSAR tooling live in `services/infrastructure/privacy_compliance`.
- Messages and user profiles are scoped per tenant/user with strict DynamoDB key design.
- Rate limiting and abuse detection (`services/infrastructure/rate_limiter`) throttle high-velocity actors across IP, user, and platform identifiers.

## Testing Strategy

- `tests/unit` � focused unit coverage for meal planning pipeline and API handlers.
- `tests/integration` � light integration scenarios validating inbound messaging payloads and repository behaviour.
- `tests/test_project_validation.py` � guardrails ensuring fixtures, docs, and configuration templates ship with the repo.

## Additional Resources

- Architecture diagram: `docs/architecture-diagram.mmd`
- Deployment checklist: `docs/deployment_instructions.md`
- Demo script: `docs/demo_script.md`
- **Monitoring & Analytics Guide**: `docs/MONITORING_USAGE_GUIDE.md`

For questions or contributions, open an issue or reach out via the contact channels referenced in the main README.
