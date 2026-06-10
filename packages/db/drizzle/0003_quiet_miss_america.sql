CREATE TABLE IF NOT EXISTS "eval_runs" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"ran_at" timestamp with time zone NOT NULL,
	"git_sha" text,
	"processed" integer NOT NULL,
	"total" integer NOT NULL,
	"micro_f1" real NOT NULL,
	"macro_f1" real NOT NULL,
	"schema_validity_rate" real NOT NULL,
	"avg_keyword_coverage" real NOT NULL,
	"per_theme_f1" jsonb DEFAULT '{}'::jsonb NOT NULL,
	"per_paper" jsonb,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE INDEX IF NOT EXISTS "eval_runs_ran_at_idx" ON "eval_runs" USING btree ("ran_at" DESC NULLS LAST);