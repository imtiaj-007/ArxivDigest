# Evals — ground truth + metric history

This directory holds the human-labeled ground truth the eval harness checks
the agent against.

## Files

- `ground_truth.jsonl` — labeled papers, one JSON object per line:
  ```jsonl
  {"arxiv_id": "2605.30351", "expected_themes": ["efficiency", "vision"], "expected_summary_keywords": ["KV cache", "low-rank latent", "video diffusion", "minute-scale"]}
  ```
- `metrics/history.jsonl` *(created by Phase 2)* — append-only log of every eval run.
- `baseline.json` *(created by Phase 3)* — current accepted thresholds that CI compares against.

## Labeling workflow

```sh
cd apps/agent && uv run arxivdigest label
```

The helper walks every unlabeled paper in DB and shows:

- title + abstract preview
- the agent's proposed themes (from the classify stage)
- heuristic-extracted keyword candidates (acronyms, capitalized phrases, hyphenated compounds)

Prompts: `[a]ccept` / `[e]dit` / `[s]kip` / `[q]uit`. Each accepted entry
writes to `evals/ground_truth.jsonl` immediately, so the session is
resume-safe — quit any time and re-run to pick up.

## Labeling rubric

### Themes (1–3 per paper)

- Choose from the [14-theme taxonomy](https://arxiv-digest-preview.vercel.app/docs/themes).
- Order by relevance (most relevant first).
- Use `other` only when nothing else fits.
- The agent's proposal is the starting point, **not** the answer — if it
  classified wrongly, that's exactly the kind of finding the eval is for.

### Keywords (3–7 per paper)

Substantive terms that any decent summary of the paper *should* mention:

- **Yes:** acronyms (`KV cache`, `RAG`), capitalized concepts (`Vision Transformer`),
  hyphenated compounds (`low-rank`, `minute-scale`), distinctive numbers
  with units (`6x`, `1024d`).
- **No:** generic words (`paper`, `method`, `approach`, `model`),
  author names, arxiv category codes (`cs.AI`).

## Why this exists

The eval harness measures the pipeline's output against this labeled set.
Pure-LLM labeling would test the pipeline against itself, defeating the
metric. Every label here is human-vetted; the agent's proposals are a
one-keypress starting point, never the answer.
