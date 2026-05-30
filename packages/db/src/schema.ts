import { sql } from "drizzle-orm";
import {
  date,
  index,
  integer,
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

export const runs = pgTable(
  "runs",
  {
    id: uuid("id").primaryKey().defaultRandom(),
    startedAt: timestamp("started_at", { withTimezone: true }).notNull().defaultNow(),
    completedAt: timestamp("completed_at", { withTimezone: true }),
    status: text("status").notNull(), // 'running' | 'completed' | 'failed'
    papersCrawled: integer("papers_crawled").notNull().default(0),
    papersSummarized: integer("papers_summarized").notNull().default(0),
    papersClassified: integer("papers_classified").notNull().default(0),
    papersEmbedded: integer("papers_embedded").notNull().default(0),
    papersRanked: integer("papers_ranked").notNull().default(0),
    papersPublished: integer("papers_published").notNull().default(0),
    errorSummary: text("error_summary"),
  },
  (t) => [index("runs_started_at_idx").on(t.startedAt.desc())],
);

export type Paper = typeof papers.$inferSelect;
export type NewPaper = typeof papers.$inferInsert;
export type Digest = typeof digests.$inferSelect;
export type NewDigest = typeof digests.$inferInsert;
export type Run = typeof runs.$inferSelect;
export type NewRun = typeof runs.$inferInsert;
