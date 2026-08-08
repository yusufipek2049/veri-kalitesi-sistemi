import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    exclude: ["e2e/**", "node_modules/**", "storybook-static/**"],
    setupFiles: ["./src/test/setup.ts"],
    // Coverage via @vitest/coverage-v8.
    // Reports written to build/coverage/frontend/.
    coverage: {
      provider: "v8",
      reporter: ["text", "text-summary", "html", "json"],
      reportsDirectory: "../build/coverage/frontend",
      include: ["src/**/*.{ts,tsx}"],
      exclude: [
        "src/**/*.test.*",
        "src/**/*.spec.*",
        "src/test/**",
        "src/**/stories/**",
        "src/**/*.stories.*",
      ],
    },
  },
});
