import commonEn from "./locales/en-US/common.json";
import todayEn from "./locales/en-US/today.json";
import plansEn from "./locales/en-US/plans.json";
import groceriesEn from "./locales/en-US/groceries.json";
import trackEn from "./locales/en-US/track.json";
import profileEn from "./locales/en-US/profile.json";

import commonEs from "./locales/es-ES/common.json";
import todayEs from "./locales/es-ES/today.json";
import plansEs from "./locales/es-ES/plans.json";
import groceriesEs from "./locales/es-ES/groceries.json";
import trackEs from "./locales/es-ES/track.json";
import profileEs from "./locales/es-ES/profile.json";

export const resources = {
  "en-US": {
    common: commonEn,
    today: todayEn,
    plans: plansEn,
    groceries: groceriesEn,
    track: trackEn,
    profile: profileEn
  },
  "es-ES": {
    common: commonEs,
    today: todayEs,
    plans: plansEs,
    groceries: groceriesEs,
    track: trackEs,
    profile: profileEs
  }
} as const;

export type AppLocale = keyof typeof resources;
export type AppNamespace = keyof typeof resources["en-US"];

export const defaultLocale: AppLocale = "en-US";

export const localeDisplayNames: Record<AppLocale, string> = {
  "en-US": "English (US)",
  "es-ES": "Español (España)"
};
