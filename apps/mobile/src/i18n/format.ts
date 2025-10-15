import { AppLocale } from "./resources";

type DateInput = Date | string | number;

const ensureDate = (value: DateInput) => {
  if (value instanceof Date) {
    return value;
  }
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    throw new Error(`Invalid date value: ${value}`);
  }
  return parsed;
};

export const formatDate = (value: DateInput, locale: AppLocale, options?: Intl.DateTimeFormatOptions) => {
  try {
    return new Intl.DateTimeFormat(locale, options).format(ensureDate(value));
  } catch (error) {
    console.warn("formatDate failed", error);
    return String(value);
  }
};

export const formatNumber = (value: number, locale: AppLocale, options?: Intl.NumberFormatOptions) => {
  try {
    return new Intl.NumberFormat(locale, options).format(value);
  } catch (error) {
    console.warn("formatNumber failed", error);
    return String(value);
  }
};

export const formatUnit = (value: number, unit: Intl.NumberFormatUnit, locale: AppLocale, options?: Intl.NumberFormatOptions) => {
  try {
    return new Intl.NumberFormat(locale, { style: "unit", unit, unitDisplay: "short", ...(options ?? {}) }).format(value);
  } catch (error) {
    console.warn("formatUnit failed", error);
    return `${value} ${unit}`;
  }
};
