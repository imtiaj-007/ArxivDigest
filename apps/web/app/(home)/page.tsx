import Link from "next/link";
import { buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

export default function Home() {
  return (
    <main className="mx-auto flex w-full max-w-3xl flex-1 flex-col items-center justify-center gap-12 px-6 py-24">
      <section className="flex flex-col items-center gap-6 text-center">
        <div className="flex items-center gap-2">
          <Badge variant="secondary">cs.AI</Badge>
          <Badge variant="secondary">cs.LG</Badge>
          <Badge variant="secondary">cs.CL</Badge>
        </div>
        <h1 className="text-balance text-5xl font-semibold tracking-tight">ArxivDigest</h1>
        <p className="text-balance text-lg text-muted-foreground">
          An autonomous AI agent that reads the day&apos;s arxiv submissions, summarizes what matters,
          and publishes a ranked digest every morning.
        </p>
        <div className="flex flex-wrap items-center justify-center gap-3">
          <Link href="/docs" className={buttonVariants({ size: "lg" })}>
            Read the docs
          </Link>
          <a
            href="https://github.com/imtiaj-007/ArxivDigest"
            target="_blank"
            rel="noreferrer"
            className={buttonVariants({ size: "lg", variant: "outline" })}
          >
            View on GitHub
          </a>
        </div>
      </section>

      <Card className="w-full">
        <CardHeader>
          <CardTitle>Status</CardTitle>
          <CardDescription>This site is pre-V0 scaffolding.</CardDescription>
        </CardHeader>
        <CardContent className="text-sm text-muted-foreground">
          The pipeline is under construction. First daily digest will appear here once V0 ships — see
          the <Link href="/docs" className="underline underline-offset-4">docs</Link> for the roadmap.
        </CardContent>
      </Card>
    </main>
  );
}
