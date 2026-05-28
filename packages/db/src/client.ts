import { drizzle } from "drizzle-orm/postgres-js";
import postgres from "postgres";
import * as schema from "./schema";

export type Database = ReturnType<typeof createDb>;

function createDb() {
  if (!process.env.DATABASE_URL) {
    throw new Error("DATABASE_URL is required to create the Drizzle client");
  }
  const queryClient = postgres(process.env.DATABASE_URL, { prepare: false });
  return drizzle(queryClient, { schema });
}

let _db: Database | undefined;

/**
 * Lazily-constructed Drizzle client. The connection is created on first call,
 * not at import time — so importing this module during `next build` (where
 * DATABASE_URL may be absent) doesn't throw. The error surfaces only if the DB
 * is actually queried without a configured URL.
 */
export function getDb(): Database {
  if (!_db) {
    _db = createDb();
  }
  return _db;
}
