// ESLint flat config — veri-kalitesi-sistemi frontend.
//
// Tool versions (verified):
//   eslint                        ^9.39.5
//   @babel/eslint-parser          ^7.29.7
//   @babel/preset-typescript      ^7.29.7
//   eslint-plugin-react-hooks     ^5.2.0
//
// LIMITATIONS (TypeScript 7.0 compatibility):
//   @typescript-eslint/parser v8 throws at module load with TS 7.0.
//   eslint-plugin-sonarjs v2/v3 depends on ts-api-utils which also fails.
//   Both are blocked until upstream adds TS 7 support.
//   See: https://github.com/typescript-eslint/typescript-eslint/issues/10940
//
//   We use @babel/eslint-parser + @babel/preset-typescript for TS syntax
//   parsing.  Type-level checking is handled by `tsc` (npm run typecheck).
//
// All rules are "warn" (not "error") in this first iteration so that
// legacy findings do not block CI.

import babelParser from "@babel/eslint-parser";
import reactHooks from "eslint-plugin-react-hooks";

export default [
  // ── Global ignores ──
  {
    ignores: [
      "dist/**",
      "node_modules/**",
      "storybook-static/**",
      "build/**",
      "coverage/**",
    ],
  },

  // ── TypeScript + React source files ──
  {
    files: ["src/**/*.{ts,tsx}"],
    languageOptions: {
      parser: babelParser,
      parserOptions: {
        requireConfigFile: false,
        babelOptions: {
          presets: [
            ["@babel/preset-typescript", { isTSX: true, allExtensions: true }],
          ],
        },
        ecmaFeatures: { jsx: true },
      },
    },
    plugins: {
      "react-hooks": reactHooks,
    },
    rules: {
      // ── React hooks ──
      "react-hooks/rules-of-hooks": "error", // always blocking
      "react-hooks/exhaustive-deps": "warn",

      // ── ESLint built-in ──
      "no-unused-vars": [
        "warn",
        { argsIgnorePattern: "^_", varsIgnorePattern: "^_" },
      ],
      "no-console": "warn",
      "no-debugger": "error",

      // Human-readability limits. These are advisory while the legacy
      // baseline is being reduced; they do not rewrite code automatically.
      complexity: ["warn", { max: 15 }],
      "max-depth": ["warn", 4],
      "max-lines-per-function": [
        "warn",
        { max: 120, skipBlankLines: true, skipComments: true },
      ],
    },
  },

  // Tests and Storybook fixtures are intentionally descriptive and can be
  // longer than production functions without obscuring runtime behavior.
  {
    files: ["src/**/*.test.{ts,tsx}", "src/**/*.stories.{ts,tsx}"],
    rules: {
      "max-lines-per-function": "off",
    },
  },

  // ── Node config files (vite, vitest, playwright, eslint) ──
  {
    files: ["*.{js,mjs}"],
    languageOptions: {
      ecmaVersion: "latest",
      sourceType: "module",
    },
    rules: {
      "no-unused-vars": ["warn", { argsIgnorePattern: "^_" }],
    },
  },
];
