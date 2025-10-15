import Constants from "expo-constants";
import * as Sentry from "sentry-expo";
import { ReactNavigationInstrumentation, ReactNativeTracing } from "@sentry/react-native";

const routingInstrumentation = new ReactNavigationInstrumentation();

const scrubEvent = (event: Sentry.Native.Event) => {
  if (event.request?.headers?.Authorization) {
    event.request.headers.Authorization = "[Filtered]";
  }
  if (event.user) {
    event.user.email = undefined;
    event.user.username = undefined;
  }
  if (event.extra?.token) {
    event.extra.token = "[Filtered]";
  }
  return event;
};

const getRelease = () => {
  const version = Constants.expoConfig?.version ?? "0.0.0";
  const revisionId = Constants.expoConfig?.extra?.revisionId ?? "dev";
  return `${Constants.expoConfig?.slug}@${version}+${revisionId}`;
};

const getDist = () => Constants.expoConfig?.runtimeVersion ?? "dev";

export const initSentry = () => {
  const dsn = (Constants.expoConfig?.extra as { sentryDsn?: string } | undefined)?.sentryDsn;
  if (!dsn) {
    return;
  }

  Sentry.init({
    dsn,
    release: getRelease(),
    dist: getDist(),
    enableInExpoDevelopment: false,
    debug: false,
    integrations: [
      new ReactNativeTracing({
        routingInstrumentation,
        tracesSampleRate: 0.2
      })
    ],
    beforeSend: scrubEvent
  });
};

export const sentryRoutingInstrumentation = routingInstrumentation;
