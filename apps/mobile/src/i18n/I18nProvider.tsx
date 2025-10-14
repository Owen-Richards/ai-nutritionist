import AsyncStorage from "@react-native-async-storage/async-storage";
import * as Localization from "expo-localization";
import i18next, { i18n as I18nInstance } from "i18next";
import React from "react";
import { ActivityIndicator, I18nManager, StyleSheet, View } from "react-native";
import { I18nextProvider, initReactI18next, useTranslation, UseTranslationOptions, UseTranslationResponse } from "react-i18next";

import { formatDate, formatNumber, formatUnit } from "@/i18n/format";
import { AppLocale, AppNamespace, resources, defaultLocale, localeDisplayNames } from "@/i18n/resources";

const STORAGE_KEY = "ai-health/mobile/locale";
const supportedLocales = Object.keys(resources) as AppLocale[];
const availableLocaleOptions = supportedLocales.map((code) => ({
  locale: code,
  label: localeDisplayNames[code]
}));

const formatInterpolation = (value: unknown, format?: string, locale?: string) => {
  const resolvedLocale = normalizeLocale(locale) ?? defaultLocale;
  if (!format) {
    return value as string;
  }

  const [formatter, preset] = format.split(":");

  switch (formatter) {
    case "number":
      return typeof value === "number" ? formatNumber(value, resolvedLocale) : value;
    case "date": {
      const options = getDateOptions(resolvedLocale, preset);
      return formatDate(value as Date | string | number, resolvedLocale, options);
    }
    case "unit": {
      if (typeof value !== "number" || !preset) return value;
      return formatUnit(value, preset as Intl.NumberFormatUnit, resolvedLocale);
    }
    default:
      return value as string;
  }
};

const getDateOptions = (locale: AppLocale, preset?: string) => {
  const common = resources[locale].common as Record<string, unknown>;
  const formats = (common.dateFormats as Record<string, Intl.DateTimeFormatOptions | undefined>) ?? {};
  if (!preset) {
    return formats.short ?? { month: "short", day: "numeric" };
  }
  return formats[preset] ?? { dateStyle: "medium" };
};

const normalizeLocale = (input?: string | null): AppLocale | undefined => {
  if (!input) return undefined;
  const canonical = input.replace("_", "-");
  if (supportedLocales.includes(canonical as AppLocale)) {
    return canonical as AppLocale;
  }
  const base = canonical.split("-")[0];
  return supportedLocales.find((locale) => locale.startsWith(base));
};

let initializationPromise: Promise<I18nInstance> | null = null;

const ensureInitialized = async (initialLocale?: AppLocale) => {
  if (!initializationPromise) {
    initializationPromise = i18next
      .use(initReactI18next)
      .init({
        compatibilityJSON: "v4",
        resources,
        fallbackLng: defaultLocale,
        supportedLngs: supportedLocales,
        lng: initialLocale ?? defaultLocale,
        ns: Object.keys(resources[defaultLocale]),
        defaultNS: "common",
        interpolation: {
          escapeValue: false,
          format: formatInterpolation
        },
        returnNull: false,
        react: {
          useSuspense: false
        }
      });
  }
  return initializationPromise;
};

type I18nContextValue = {
  locale: AppLocale;
  changeLocale: (next: AppLocale) => Promise<void>;
  availableLocales: Array<{ locale: AppLocale; label: string }>;
  isRTL: boolean;
  formatDate: (value: Date | string | number, options?: Intl.DateTimeFormatOptions) => string;
  formatNumber: (value: number, options?: Intl.NumberFormatOptions) => string;
  formatUnit: (value: number, unit: Intl.NumberFormatUnit, options?: Intl.NumberFormatOptions) => string;
};

const I18nContext = React.createContext<I18nContextValue | undefined>(undefined);

const updateLayoutDirection = (locale: AppLocale) => {
  const dir = i18next.dir(locale);
  if (I18nManager.isRTL !== (dir === "rtl")) {
    I18nManager.allowRTL(true);
  }
};

const resolveInitialLocale = async (): Promise<AppLocale> => {
  const stored = await AsyncStorage.getItem(STORAGE_KEY);
  if (stored) {
    const normalized = normalizeLocale(stored);
    if (normalized) {
      return normalized;
    }
  }
  const locales = Localization.getLocales();
  const device = locales[0]?.languageTag;
  return normalizeLocale(device) ?? defaultLocale;
};

export const I18nProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [locale, setLocale] = React.useState<AppLocale>((i18next.language as AppLocale) ?? defaultLocale);
  const [isReady, setReady] = React.useState(i18next.isInitialized);

  React.useEffect(() => {
    if (isReady) {
      updateLayoutDirection(locale);
      return;
    }

    let cancelled = false;
    (async () => {
      const initialLocale = await resolveInitialLocale();
      await ensureInitialized(initialLocale);
      if (cancelled) {
        return;
      }
      const current = (i18next.language as AppLocale) ?? initialLocale;
      setLocale(current);
      updateLayoutDirection(current);
      setReady(true);
    })();

    return () => {
      cancelled = true;
    };
  }, [isReady, locale]);

  const changeLocale = React.useCallback(async (next: AppLocale) => {
    await ensureInitialized();
    await i18next.changeLanguage(next);
    setLocale(next);
    updateLayoutDirection(next);
    await AsyncStorage.setItem(STORAGE_KEY, next);
  }, []);

  const contextValue = React.useMemo<I18nContextValue>(
    () => ({
      locale,
      changeLocale,
      availableLocales: availableLocaleOptions,
      isRTL: i18next.dir(locale) === "rtl",
      formatDate: (value, options) => formatDate(value, locale, options),
      formatNumber: (value, options) => formatNumber(value, locale, options),
      formatUnit: (value, unit, options) => formatUnit(value, unit, locale, options)
    }),
    [changeLocale, locale]
  );

  if (!isReady) {
    return (
      <View style={styles.loading}>
        <ActivityIndicator size="small" />
      </View>
    );
  }

  return (
    <I18nextProvider i18n={i18next}>
      <I18nContext.Provider value={contextValue}>{children}</I18nContext.Provider>
    </I18nextProvider>
  );
};

export const useI18n = () => {
  const context = React.useContext(I18nContext);
  if (!context) {
    throw new Error("useI18n must be used within I18nProvider");
  }
  return context;
};

export const useAppTranslation = <Ns extends AppNamespace | undefined = undefined>(
  namespace?: Ns,
  options?: UseTranslationOptions<Ns>
): UseTranslationResponse<Ns> => {
  const ns = (namespace ?? "common") as Ns;
  return useTranslation(ns, options);
};

const styles = StyleSheet.create({
  loading: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center"
  }
});
