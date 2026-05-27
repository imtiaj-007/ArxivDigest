import { nextJsConfig } from "@repo/eslint-config/next-js";
import globals from "globals";

/** @type {import("eslint").Linter.Config[]} */
export default [
  ...nextJsConfig,
  {
    // Node globals (process, etc.) for build/instrumentation files.
    files: ["instrumentation*.ts", "next.config.js", "source.config.ts", "postcss.config.mjs"],
    languageOptions: {
      globals: { ...globals.node },
    },
  },
  {
    ignores: [".source/**", ".next/**"],
  },
];
