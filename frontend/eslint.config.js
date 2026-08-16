// ESLint flat config — veri-kalitesi-sistemi frontend.
//
// Tool versions (verified):
//   eslint                        ^9.39.5
//   typescript-eslint             ^8.67.0
//   typescript                    ^5.9.3
//   eslint-plugin-react           ^7.37.5
//   eslint-plugin-react-hooks     ^5.2.0
//
// F-11: Bu dosya daha once TypeScript 7.0 varsayimiyla @typescript-eslint'i
// devre disi birakip @babel/eslint-parser kullaniyordu. Kurulu surum 5.9.3
// oldugu icin bu kisit gecerli degildi; cekirdek `no-unused-vars` kurali TS
// tiplerini ve parametre ozelliklerini anlamadigi icin 113 yanlis pozitif
// uretiyordu. Parser artik @typescript-eslint/parser, kullanilmayan degisken
// kontrolu ise TS-farkindali @typescript-eslint/no-unused-vars.
// Tip duzeyi kontrol yine `tsc` sorumlulugunda (npm run typecheck).
//
// All rules are "warn" (not "error") in this first iteration so that
// legacy findings do not block CI.
//
// `npm run lint` bu nedenle sifir degil, mevcut baseline (59) uzerinden
// gecer: yeni uyari eklenirse CI kirmizi olur, eski okunabilirlik borcu
// (max-lines-per-function / complexity) gate'i kilitlemez. Borc azaldikca
// package.json'daki --max-warnings degeri asagi cekilmelidir.

import react from "eslint-plugin-react";
import reactHooks from "eslint-plugin-react-hooks";
import tseslint from "typescript-eslint";

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
      parser: tseslint.parser,
      parserOptions: {
        ecmaFeatures: { jsx: true },
        sourceType: "module",
      },
    },
    plugins: {
      react,
      "react-hooks": reactHooks,
      "@typescript-eslint": tseslint.plugin,
    },
    settings: {
      react: { version: "detect" },
    },
    rules: {
      // ── React JSX ──
      // Mark variables referenced in JSX as used (prevents false-positive
      // no-unused-vars for every component import / local variable).
      "react/jsx-uses-vars": "error",

      // ── React hooks ──
      "react-hooks/rules-of-hooks": "error", // always blocking
      "react-hooks/exhaustive-deps": "warn",

      // ── ESLint built-in ──
      // Cekirdek kural TS tiplerini goremedigi icin kapali; yerine
      // TS-farkindali surumu kullanilir.
      "no-unused-vars": "off",
      "@typescript-eslint/no-unused-vars": [
        "warn",
        { argsIgnorePattern: "^_", varsIgnorePattern: "^_" },
      ],
      // Birakilmis `console.log` hata ayiklama artigidir; catch blogundaki
      // bilincli `console.warn`/`console.error` ise tek hata kanalimiz.
      "no-console": ["warn", { allow: ["warn", "error"] }],
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
