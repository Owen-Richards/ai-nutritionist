import { markAppStart } from "@/observability/performance";
import { initSentry } from "@/observability/sentry";

markAppStart();
initSentry();

import "expo-router/entry";
