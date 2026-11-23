---
name: review-pr
description: Comprehensive PR review checking security, tests, quality, and conventions
argument-hint: [pr-number]
disable-model-invocation: true
allowed-tools:
  - Bash(gh pr *)
  - Bash(gh api *)
  - Bash(git rev-parse *)
  - Bash(cat *)
  - Read
  - Grep
  - Glob
---

Review PR #$0 against this repository's standards.

## Review Steps

Use a positive decimal PR number for `Concord-Voice/.github`. A full `https://github.com/Concord-Voice/.github/pull/NUMBER` URL identifies the same target. Validate the argument before constructing commands and use only the extracted number as `PR_NUMBER`. A fork may supply the head branch. The target is always the base repository.

1. **Fetch PR context** — use `gh pr view "$PR_NUMBER" --repo github.com/Concord-Voice/.github` and `gh pr diff "$PR_NUMBER" --repo github.com/Concord-Voice/.github` to understand the change
2. **Categorize** — is this a feature, fix, refactor, chore, or docs change?

## Agent Dispatch (Priority 0 — runs first)

Read the review policy as JSON at the PR's exact base commit. Run this block with the validated `PR_NUMBER`. Stop if GitHub cannot establish the base or read its Git data.

```bash
set -e
[[ ${PR_NUMBER:-} =~ ^[1-9][0-9]*$ ]] || exit 1
base_oid=$(gh api --hostname github.com "repos/Concord-Voice/.github/pulls/$PR_NUMBER" \
  --jq 'select(.base.repo.full_name == "Concord-Voice/.github") | .base.sha')
[[ $base_oid =~ ^[0-9a-f]{40}$ ]] || exit 1

gh api --hostname github.com graphql -f base="$base_oid" -f path="$base_oid:.claude/repo-config.json" \
  -f query='query($base: GitObjectID!, $path: String!) {
    repository(owner: "Concord-Voice", name: ".github") {
      base: object(oid: $base) { __typename }
      config: object(expression: $path) { __typename ... on Blob { isBinary isTruncated text } }
    }
  }' --jq '
    .data.repository |
    if .base.__typename != "Commit" then error("base commit unavailable")
    elif .config == null then {}
    elif .config.__typename != "Blob" or .config.isBinary or .config.isTruncated or .config.text == null
      then error("review configuration is unreadable")
    else (try (.config.text | fromjson) catch {}) end |
    (try .review_agents.base catch null) as $base |
    (try .review_agents.patterns catch null) as $patterns |
    {base: (if ($base | type) == "array" then $base else ["security-reviewer","code-reviewer","docs-reviewer"] end),
     patterns: (if ($patterns | type) == "array" then $patterns else [] end)}'

gh pr diff "$PR_NUMBER" --repo github.com/Concord-Voice/.github --name-only
```

### Base agents (always dispatched)

Dispatch every agent in the returned `base` list in parallel. The defaults are `security-reviewer`, `code-reviewer`, and `docs-reviewer`.

### Pattern-triggered agents (dispatched when a changed file matches)

For each `{glob, agent}` in `patterns`, match the glob against the changed filenames from the same PR. Dispatch each distinct matching agent only once, alongside the base agents. An absent pattern list adds no agents.

Include each agent's findings under the appropriate Priority section below.

## Security Review (Priority 1)

Check against any `docs/policies/ai-generated-code-policy.md` and applicable `.claude/rules/*.md` the repo provides:
- No hardcoded secrets, API keys, or credentials
- No `eval()`, `dangerouslySetInnerHTML`, `innerHTML` without sanitization
- No `fmt.Sprintf` for SQL — parameterized queries only
- No `any` type in security-critical paths (auth, crypto, E2EE, RBAC)
- Crypto uses approved algorithms only (AES-256-GCM, RSA-4096, Argon2id)
- Auth changes revoke tokens atomically
- IPC through preload bridge only (no `nodeIntegration`, no `@electron/remote`)

## Correctness Review (Priority 2)

- Does the code do what the PR description claims?
- Are edge cases handled?
- Error handling: all errors checked (Go `errcheck`), no fail-open patterns
- Database: `defer rows.Close()`, `rows.Err()` checked, correct `argIdx` in dynamic queries

## Test Coverage (Priority 3)

- New code has corresponding test files
- Happy path + error path tests present
- Go: `t.Run` subtests, `require` for preconditions, `assert` for checks
- React: `resetAllStores()` in `beforeEach`, MSW for API mocking
- Coverage target: >= 80% on new code

## Style & Conventions (Priority 4)

- Conventional Commits format
- One issue per PR (`Closes #NNN`)
- Go: handler-struct pattern, Gin conventions (`ShouldBindJSON`)
- React: functional components, Zustand selective subscriptions
- `Co-Authored-By` trailer if AI-assisted

## Documentation Drift (Priority 5)

`@docs-reviewer` is dispatched via the Agent Dispatch table above when any `.md` file is changed. Report its findings here:
- Source areas touched in this PR have corresponding doc updates
- No duplicated facts (counts, phase status, agent lists) became inconsistent
- Cross-references to CLAUDE.md (when the repo has one) are present where counts are stated

Report findings inline with severity (HIGH/MEDIUM/LOW/INFO).

## Output Format

Report findings by severity:
- **CRITICAL** — blocks merge (security, correctness)
- **MAJOR** — should fix before merge (quality, missing tests)
- **MINOR** — nice to fix (style, docs)
- **APPROVED** — if all checks pass

Reference specific files and line numbers.
