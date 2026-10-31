# How Concord Voice Uses AI in Development

Concord Voice is built by a small team that uses AI coding assistants. This page explains how we use them and the rules we follow. It applies to every Concord Voice repository, and to contributions from outside the team.

## The short version

- **People are responsible for every change.** An AI tool can draft code, but the person who asks for it, reviews it and commits it owns it.
- **Your data never goes into an AI tool.** Customer data, production secrets and signing keys are never given to an AI tool, whatever that tool's privacy terms say.
- **AI-assisted commits are labelled.** Each one carries a `Co-Authored-By` trailer that names the tool.
- **Security-sensitive code gets extra review.** Changes to encryption, authentication, permissions and the desktop app's process boundary get a security review, whoever or whatever wrote them.
- **AI tools have no access to production.** They work only in development environments, with development credentials.

## Which tools we use

| Tool | What we use it for |
| --- | --- |
| Claude Code (Anthropic) | Main coding agent, in the terminal and the editor |
| GitHub Copilot | Code completion and pull request review |
| OpenAI Codex | Code generation and pull request review |

We also use automated reviewers and scanners on pull requests, such as SonarQube Cloud, CodeQL and Semgrep. Any new AI tool needs the project owner's written approval first. The request must describe how the tool handles data.

## What data an AI tool may see

| Kind of data | Allowed? | Extra controls |
| --- | --- | --- |
| Public code | Yes | Normal review |
| Internal code | Yes | Normal review |
| Sensitive code (auth, encryption, personal data flows) | Yes | Security review required |
| Production secrets, signing keys, customer data | **Never** | Not applicable |

## What an AI tool must not do

1. Create or change production secrets, API keys or credentials.
2. Write encryption code (key generation, encryption, decryption) without an expert review.
3. Change login or permission logic without a security review.
4. Write code that handles personal or payment data without a review.
5. Connect to production or staging systems.
6. Skip pre-commit hooks or CI checks.

If an AI-written change starts using encryption, secrets or login APIs that the task didn't call for, the developer must flag it for security review before it merges.

## How we keep agents in check

We treat an AI agent like an outside contractor: it gets the least access it needs, its work is reviewed, and its actions leave a record.

| Risk | Examples | What happens |
| --- | --- | --- |
| Low | Reading files, searching code, viewing git history | Allowed automatically |
| Medium | Editing files, running builds and tests, committing | The developer approves |
| High | Pushing code, opening issues or PRs, changing CI | The developer approves explicitly |
| Critical | Rewriting history, deleting work, reading credential stores | Blocked, or explicit approval plus review |

Our shared agent settings deny destructive commands, such as force pushes, hard resets and recursive deletes. They also block reads of credential stores and secret files. A developer can always stop an agent, and git can undo every file it changes.

## Tool integrations (MCP servers)

Some AI tools connect to outside services through Model Context Protocol (MCP) servers. Each server is checked before we approve it, and checked again every quarter, after a major version and after any security advisory. These servers get the narrowest credentials that work, such as test-mode or restricted keys. They never get production or staging credentials, and no credential is ever committed to a repository.

## Supply chain

Our rule is that every third-party GitHub Action in our workflows is pinned to a full commit SHA, so a changed tag can't alter our build without review. We treat updating a pinned action as a trust decision, with its own review.

## Contributing with AI

You may use AI tools when you contribute. If you do:

1. Add a `Co-Authored-By` trailer that names the tool.
2. Review and test the change yourself. You are responsible for it, just as for code you typed.
3. Never paste secrets, private keys or other people's personal data into an AI tool.
4. Say in the pull request if AI wrote encryption, login or permission code.

## Frameworks we follow

- [OWASP Top 10 for LLM Applications](https://owasp.org/www-project-top-10-for-large-language-model-applications/)
- [OWASP Agentic AI Threats](https://owasp.org/www-project-agentic-ai-threats/)
- [NIST AI Risk Management Framework](https://www.nist.gov/artificial-intelligence/ai-risk-management-framework)
- [OpenSSF guide for AI code assistant instructions](https://openssf.org/blog/2025/04/17/introducing-the-security-focused-guide-for-ai-code-assistant-instructions/)

We review this policy every quarter. To report a security problem, see our [security policy](SECURITY.md).
