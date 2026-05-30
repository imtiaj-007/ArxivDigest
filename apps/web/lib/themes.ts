// Mirrors the agent's canonical taxonomy in
// apps/agent/src/arxivdigest/domain/themes.py. Kept here so the web side can
// resolve a slug to its display name + description without a DB round-trip.

export type Theme = { slug: string; name: string; description: string };

export const THEMES: Theme[] = [
  { slug: "llm", name: "Large Language Models",
    description: "LLM architectures, training, scaling, inference." },
  { slug: "agents", name: "Agents & Tool Use",
    description: "Autonomous agents, planning, tool/function calling, multi-agent systems." },
  { slug: "retrieval", name: "Retrieval & RAG",
    description: "Retrieval-augmented generation, embeddings, vector search, memory." },
  { slug: "reasoning", name: "Reasoning",
    description: "Chain-of-thought, math, code, planning, problem-solving." },
  { slug: "efficiency", name: "Efficiency & Systems",
    description: "Quantization, distillation, KV-cache, serving, inference speedups." },
  { slug: "rl", name: "Reinforcement Learning",
    description: "RL, RLHF, preference optimization, alignment training." },
  { slug: "vision", name: "Computer Vision",
    description: "Image/video understanding, generation, diffusion, multimodal vision." },
  { slug: "multimodal", name: "Multimodal",
    description: "Vision-language, audio, cross-modal models and benchmarks." },
  { slug: "speech", name: "Speech & Audio",
    description: "ASR, TTS, audio generation and understanding." },
  { slug: "robotics", name: "Robotics & Embodied AI",
    description: "Manipulation, control, embodied agents, sim-to-real." },
  { slug: "safety", name: "Safety & Alignment",
    description: "Alignment, interpretability, red-teaming, evaluation of risks." },
  { slug: "data", name: "Data & Benchmarks",
    description: "Datasets, benchmarks, evaluation methodology, data curation." },
  { slug: "theory", name: "ML Theory",
    description: "Optimization, generalization, learning theory, statistics." },
  { slug: "other", name: "Other",
    description: "Anything that doesn't fit the themes above." },
];

export const THEME_BY_SLUG: ReadonlyMap<string, Theme> = new Map(
  THEMES.map((t) => [t.slug, t]),
);
