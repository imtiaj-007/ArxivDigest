CREATE TABLE IF NOT EXISTS "runs" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"started_at" timestamp with time zone DEFAULT now() NOT NULL,
	"completed_at" timestamp with time zone,
	"status" text NOT NULL,
	"papers_crawled" integer DEFAULT 0 NOT NULL,
	"papers_summarized" integer DEFAULT 0 NOT NULL,
	"papers_classified" integer DEFAULT 0 NOT NULL,
	"papers_embedded" integer DEFAULT 0 NOT NULL,
	"papers_ranked" integer DEFAULT 0 NOT NULL,
	"papers_published" integer DEFAULT 0 NOT NULL,
	"error_summary" text
);
--> statement-breakpoint
CREATE INDEX IF NOT EXISTS "runs_started_at_idx" ON "runs" USING btree ("started_at" DESC NULLS LAST);