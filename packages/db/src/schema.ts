import { sql } from "drizzle-orm";
import {
  date,
  index,
  pgTable,
  real,
  text,
  timestamp,
  uniqueIndex,
  uuid,
  vector,
} from "drizzle-orm/pg-core";

export const papers = pgTable(
  "papers",
  {
    id: uuid("id").primaryKey().defaultRandom(),
    arxivId: text("arxiv_id").notNull(),
    title: text("title").notNull(),
    abstract: text("abstract").notNull(),
    authors: text("authors").array().notNull().default(sql`'{}'::text[]`),
    categories: text("categories").array().notNull().default(sql`'{}'::text[]`),
    publishedAt: timestamp("published_at", { withTimezone: true }).notNull(),
    embedding: vector("embedding", { dimensions: 1024 }),
    summary: text("summary"),
    themes: text("themes").array(),
    score: real("score"),
    createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
    updatedAt: timestamp("updated_at", { withTimezone: true }).notNull().defaultNow(),
  },
  (t) => [
    uniqueIndex("papers_arxiv_id_idx").on(t.arxivId),
    index("papers_published_at_idx").on(t.publishedAt.desc()),
    index("papers_embedding_idx").using("hnsw", t.embedding.op("vector_cosine_ops")),
  ],
);

export const digests = pgTable(
  "digests",
  {
    id: uuid("id").primaryKey().defaultRandom(),
    date: date("date").notNull(),
    summary: text("summary").notNull(),
    paperIds: uuid("paper_ids").array().notNull().default(sql`'{}'::uuid[]`),
    createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
  },
  (t) => [uniqueIndex("digests_date_idx").on(t.date)],
);

export type Paper = typeof papers.$inferSelect;
export type NewPaper = typeof papers.$inferInsert;
export type Digest = typeof digests.$inferSelect;
export type NewDigest = typeof digests.$inferInsert;
