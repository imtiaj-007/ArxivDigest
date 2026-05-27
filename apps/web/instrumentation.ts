import * as Sentry from "@sentry/nextjs";

const dsn = process.env.SENTRY_DSN;

export async function register() {
  if (!dsn) {
    console.info("[sentry] disabled — SENTRY_DSN not set");
    return;
  }

  if (process.env.NEXT_RUNTIME === "nodejs" || process.env.NEXT_RUNTIME === "edge") {
    Sentry.init({
      dsn,
      environment: process.env.SENTRY_ENVIRONMENT ?? "development",
      tracesSampleRate: 0,
      sendDefaultPii: false,
    });
  }
}

export const onRequestError = Sentry.captureRequestError;
