# AI Health Mobile

Expo + React Native client for the AI Nutritionist experience.

## Development

```bash
yarn install
yarn dev
```

## Quality Gates

```bash
yarn lint
yarn typecheck
yarn test:unit
# optional
# yarn detox:build && yarn test:e2e
```

## Release

Managed via EAS profiles in `eas.json`:
- `development` for local development builds
- `staging` for internal distribution
- `production` for store releases

Set `EXPO_PUBLIC_API_BASE_URL` or update `app.json` `extra` before promotion. Sentry DSN can be configured with `expo.extra.sentryDsn`.
