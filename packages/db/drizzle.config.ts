import { defineConfig } from "drizzle-kit";
import { config as loadEnv } from "dotenv";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";

// Load the canonical repo-root .env (two levels up from packages/db/).
const here = dirname(fileURLToPath(import.meta.url));
loadEnv({ path: resolve(here, "../../.env") });

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
