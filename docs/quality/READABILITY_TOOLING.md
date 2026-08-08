# Readability Tooling

The readability checks are advisory. A finding is a review candidate, not
permission to delete or split code automatically.

## Signals

| Concern | Tool | Default threshold or scope |
|---|---|---|
| Human cognitive load | Complexipy | complexity greater than 15 |
| Python structural complexity | Ruff | `C90`, selected `PLR09` rules |
| TypeScript/React complexity | ESLint | complexity 15, nesting 4, function length 120 |
| AI-style wrappers and no-op abstractions | Semgrep | custom rules under `tools/semgrep/rules/` |
| Dead exports and symbols | Knip and Vulture | advisory candidates |
| Copy-paste blocks | jscpd | minimum 5 lines |
| Callers and architectural impact | Graphify | required before removal or API collapse |

The default scan excludes the `single-method-adapter` Semgrep rule because its
precision is intentionally very low. It remains available for focused reviews,
where every result must be checked with Graphify.

Run all signals:

```bash
./scripts/check_quality.sh --advisory
```

Inspect a named candidate against the refreshed graph:

```bash
./scripts/review_readability_candidate.sh <symbol>
```

## Refactoring contract

Before changing a candidate:

1. Confirm its callers with Graphify and direct text search.
2. Classify it as behavior, boundary, compatibility surface, or accidental
   indirection. Protocol methods, framework hooks and DTO mappings are not
   removed merely because a static tool reports them.
3. Prefer flattening control flow and removing needless indirection. Do not
   introduce a class, helper, factory, or interface unless it has multiple
   callers, owns state, isolates a real boundary, or makes testing materially
   clearer.
4. Keep the smallest coherent public API and preserve behavior with focused
   tests.
5. Re-run the affected tests, type checks, readability scan, and Graphify.

Complexipy suggestions are deterministic hints. They do not rewrite source
code and must be reviewed against domain meaning.

`max-params` is deliberately not enabled for TypeScript yet. ESLint's built-in
rule crashes on TypeScript function-type properties when used through the
project's Babel parser, while `@typescript-eslint/parser` and SonarJS currently
declare TypeScript support only below 6.1. Python parameter counts remain
covered by Ruff `PLR0913`; frontend support can be enabled after the parser
toolchain supports TypeScript 7.
