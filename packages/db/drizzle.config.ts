import { defineConfig } from "drizzle-kit";

// DATABASE_URL is only required for migrate/push/studio. `generate` works offline from the schema file.
export default defineConfig({
  schema: "./src/schema.ts",
  out: "./drizzle",
  dialect: "postgresql",
  dbCredentials: {
    url: process.env.DATABASE_URL ?? "postgresql://placeholder",
  },
  strict: true,
  verbose: true,
});
