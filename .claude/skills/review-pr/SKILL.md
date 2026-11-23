---
name: review-pr
description: Comprehensive PR review checking security, tests, quality, and conventions
argument-hint: "[pr-number or target PR URL]"
disable-model-invocation: true
allowed-tools:
  - Bash(gh pr *)
  - Bash(gh api *)
  - Read
  - Grep
  - Glob
---

Review the PR identified by the invocation argument `$ARGUMENTS` against this repository's standards.

## Review Steps

Treat the entire argument as data in the host. Match it against this whole-string grammar before calling Bash:

```regex
^(?:([1-9][0-9]*)|https://github\.com/Concord-Voice/\.github/pull/([1-9][0-9]*)/?)$
```

Use only the digits in the matching capture group as the literal `NUMBER` in the commands below. Reject other inputs. Never put the original argument in a shell command. For example, `/review-pr 15` and `/review-pr https://github.com/Concord-Voice/.github/pull/15` both run `gh pr view 15 --repo github.com/Concord-Voice/.github`. Each command runs independently.

1. **Fetch PR context** — use `gh pr view NUMBER --repo github.com/Concord-Voice/.github` and `gh pr diff NUMBER --repo github.com/Concord-Voice/.github` to understand the change
2. **Categorize** — is this a feature, fix, refactor, chore, or docs change?

## Agent Dispatch (Priority 0 — runs first)

Get the base Git object ID from the same PR. The target repository is fixed even if the head comes from a fork. Stop on any command error.

```bash
gh pr view NUMBER --repo github.com/Concord-Voice/.github --json number,url,baseRefOid --jq '
  if .number == NUMBER and .url == ("https://github.com/Concord-Voice/.github/pull/" + (.number | tostring))
     and (.baseRefOid | test("^[0-9a-f]{40}$"))
  then .baseRefOid else error("cannot verify PR base") end'
```

Use the returned 40 lowercase hex digits as the literal `BASE_OID` in both arguments of the next command. Read the policy from that commit as JSON.

```bash
gh api --hostname github.com graphql -f base=BASE_OID -f path=BASE_OID:.claude/repo-config.json \
  -f query='query($base: GitObjectID!, $path: String!) {
    repository(owner: "Concord-Voice", name: ".github") {
      base: object(oid: $base) { __typename }
      config: object(expression: $path) { __typename ... on Blob { isBinary isTruncated text } }
    }
  }' --jq '
    def agent: type == "string" and test("^[^[:space:]]+$");
    def pattern: type == "object" and (.agent | agent)
      and (.glob | type == "string" and length > 0 and (test("[\\t\\r\\n]") | not));
    .data.repository |
    if .base.__typename != "Commit" then error("base commit unavailable")
    elif .config == null then {}
    elif .config.__typename != "Blob" or .config.isBinary or .config.isTruncated or .config.text == null
      then error("review configuration is unreadable")
    else (.config.text | fromjson) end |
    if type != "object" then error("review configuration must be an object") end |
    if has("review_agents") then .review_agents else {} end |
    if type != "object" then error("review_agents must be an object") end |
    if has("base") and (.base | type != "array" or (all(.[]; agent) | not))
      then error("invalid review_agents.base") end |
    if has("patterns") and (.patterns | type != "array" or (all(.[]; pattern) | not))
      then error("invalid review_agents.patterns") end |
    {base: (.base // ["security-reviewer","code-reviewer","docs-reviewer"]), patterns: (.patterns // [])}'
```

```bash
gh pr diff NUMBER --repo github.com/Concord-Voice/.github --name-only
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
