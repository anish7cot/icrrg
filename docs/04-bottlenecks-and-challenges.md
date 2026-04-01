# 04 — Bottlenecks, Challenges & Mitigations

## Why This Document Exists

Every hackathon project has failure modes. The teams that win aren't the ones that avoid problems — they're the ones that anticipated them and had a plan. This document is your pre-mortem. Read it before you start building and revisit it when things go sideways.

---

## 1. LLM Latency — The Silent Killer

### The Problem
A single GPT-4 API call for code review takes 5–15 seconds depending on diff size and API load. A developer waiting 15 seconds on every `git commit` will abandon the tool by day two. Developers commit far more frequently than they push — sometimes dozens of times a day. Multiply that wait across multiple files in a single commit and you're looking at 30–60 seconds of blocking time per commit. That's a developer experience killer.

### Why It's Worse Than You Think
During hackathon demos, you're typically running multiple scans in quick succession to show off the tool. OpenAI's rate limits will throttle you at the worst possible moment — mid-demo. Nothing kills a presentation faster than a spinner that doesn't stop.

### Mitigation
- **Make LLM code review async.** The pre-commit hook runs PHI/secret detection synchronously (it's fast — regex + NER finishes in under a second). Code review runs in the background via Celery. The commit is allowed or blocked based on PHI/secret findings alone. Code review results arrive on the dashboard and via notification shortly after.
- **Cache aggressively.** If the same file hasn't changed between commits, don't re-review it. Hash file contents and check cache before calling the LLM.
- **Have a demo backup.** Pre-seed some completed scan results in the database so you can show the full pipeline even if the API is slow during the live demo.
- **Set hard timeouts.** If the LLM doesn't respond in 20 seconds, gracefully degrade: log the timeout, allow the commit, and mark the scan as "pending review." Never let a tool failure block developer workflow.

---

## 2. False Positives — The Trust Destroyer

### The Problem
If your PHI/secret scanner flags every UUID, test fixture, and configuration template as a leak, developers will ignore it within a week. False positives are the number one reason security tooling gets disabled by engineering teams. This isn't hypothetical — it's the history of every SAST tool ever deployed.

### Specific False Positive Scenarios
- **Test fixtures:** `patient_ssn = "123-45-6789"` in a test file is not a leak — it's a test constant
- **Documentation:** A README explaining SSN format with an example is not a leak
- **Environment templates:** `.env.example` with `DATABASE_URL=postgresql://user:password@localhost/db` is a template, not a credential
- **UUIDs and hashes:** Random-looking strings in configuration are not necessarily secrets
- **Base64-encoded data:** Not everything that's base64 is a secret

### Mitigation
- **Context awareness is non-negotiable.** Your classifier must consider the file path (test files, docs, templates), the variable assignment context, and the surrounding code. A string that looks like a secret in `config/production.py` is very different from the same string in `tests/test_config.py`.
- **Configurable allowlists.** Let developers mark patterns, files, or paths as safe. Store these as project-level configuration.
- **Confidence scoring, not binary classification.** Every finding should have a confidence score. Show high-confidence findings prominently. Let low-confidence findings be informational, not blocking.
- **Start strict, loosen with data.** It's easier to reduce sensitivity than to explain why you missed a real secret. Tune after you have real usage data.

---

## 3. PHI Detection Accuracy

### The Problem
PHI is contextual. "John Smith" is PHI when it appears next to a diagnosis code in a healthcare application's source code. "John Smith" is not PHI when it's the name of a developer in a git commit message, or a variable in a test file. Medical Record Numbers (MRNs) look like regular integers. Dates of birth look like any other date. ZIP codes are just numbers.

### Why This Is Harder Than Secret Detection
Secrets have recognizable structures — AWS keys start with `AKIA`, private keys have headers, API keys have specific entropy profiles. PHI has no such structural signature. It requires understanding *what the data represents* in context, not just *what it looks like*.

### Mitigation
- **Layer your approach.** Regex catches the obvious patterns (SSN format, phone numbers). NER catches entity types (person names, locations). The context classifier determines whether the entity in this context constitutes PHI.
- **Domain-specific NER training.** If you have access to sample healthcare application code (even synthetic), fine-tune your spaCy model on healthcare entity recognition. The default NER model recognizes "John Smith" as a person but doesn't know that a person in a patient context is PHI.
- **Focus on high-precision for the demo.** It's better to catch 70% of PHI with 95% precision than 95% of PHI with 70% precision. Missing some PHI is acceptable for a hackathon. Flagging every name in the codebase as PHI will tank your demo credibility.
- **Acknowledge the limitation.** In your pitch, be honest: "Our current model catches structured PHI patterns with high confidence. Unstructured PHI detection is a roadmap item requiring domain-specific training data." Judges respect honesty more than overclaiming.

---

## 4. OpenAI API Dependency & Cost

### The Problem
Your code review and report generation engines depend entirely on a third-party API. If OpenAI is down, those features are dead. During a hackathon, you can't wait for an outage to resolve. Also, GPT-4 API calls cost money — a large diff review can cost $0.10–$0.50 per call, and rapid iteration during development burns through budget.

### Mitigation
- **Budget guardrails.** Set a hard spending limit on your OpenAI account. Know what your demo will cost and pad it by 3x for testing.
- **Use GPT-4o-mini for development iteration.** Only switch to GPT-4/GPT-4o for final testing and demo. The mini model is 10–20x cheaper and sufficient for prompt development.
- **Build a mock mode.** Implement a flag that returns pre-canned LLM responses instead of making real API calls. Use this during frontend development and integration testing. It also serves as your demo backup if the API goes down.
- **Abstract the LLM provider.** Your code should call an internal `LLMService` that wraps the API. If you need to switch to Azure OpenAI, Anthropic, or a local model, you change one service implementation — not every callsite.
- **Have Azure OpenAI as a backup.** If you have Azure credits, set up Azure OpenAI as a failover. Same API, different endpoint, independent availability.

---

## 5. Pre-Commit Hook: Frequency, Edge Cases & Developer Friction

### The Problem
Pre-commit hooks fire on **every single commit**. Developers commit far more often than they push — quick save-point commits, WIP commits, amend commits, squash-during-rebase commits. A hook that adds even 2 seconds of latency will be felt dozens of times a day. A hook that misfires during a rebase will make developers hostile to the tool.

This is the fundamental tradeoff you accepted by choosing pre-commit over pre-push: you get the strongest possible security posture (secrets never enter git history), but you pay for it with tighter developer workflow constraints.

### Specific Edge Cases That Will Bite You

- **Interactive rebase (`git rebase -i`):** Every commit being replayed triggers the pre-commit hook. A 20-commit rebase means 20 hook invocations. If any one of them contains a flagged pattern (even a false positive from an old commit), the rebase halts mid-way, leaving the developer in a messy detached state.
- **Amend commits (`git commit --amend`):** The hook fires again on the entire staged diff, not just what changed since the last amend. This means a developer who already fixed a finding might see it re-flagged if they amend for an unrelated reason.
- **Merge commits:** During a merge, the hook fires on the combined diff, which can be massive and contain code the developer didn’t write. Flagging issues in someone else’s merged code is frustrating and confusing.
- **Partial staging (`git add -p`):** Developers who stage individual hunks may have unstaged changes in the same file. The hook must scan only `git diff --cached` (staged changes), not the working tree. Getting this wrong means scanning code that isn’t being committed.
- **Hook bypass (`git commit --no-verify`):** This flag skips all hooks. Developers frustrated by slow or noisy hooks will learn this command fast. Unlike a server-side check, there’s no way to prevent this locally.

### Mitigation
- **Skip scans during rebase.** Detect `GIT_REBASE_TODO` or `GIT_SEQUENCE_EDITOR` environment variables and skip the hook entirely during rebase operations. Rebasing replays existing commits — they were already scanned when first committed.
- **Cache by content hash.** Before calling the API, hash the staged diff content. If the hash matches a previous scan that passed, return immediately with a cached result. This makes amend commits near-instant if the flagged content hasn’t changed.
- **Skip merge commits.** Detect merge state (`MERGE_HEAD` exists) and either skip the hook or scan only the conflict resolution changes, not the full merge diff.
- **Use only `git diff --cached`.** This is non-negotiable. The hook must scan staged content only, never the working tree. Test this explicitly with partial staging scenarios.
- **Track `--no-verify` usage.** You can't prevent it locally, but the Bitbucket webhook acts as a server-side safety net. If a commit arrives via push without a corresponding scan record in the database, flag it as "unscanned" on the dashboard. This creates visibility without blocking the developer.
- **Keep hook execution under 2 seconds.** This is the hard budget. PHI/secret detection via regex + NER must complete in under 2 seconds. LLM code review is always async — never in the pre-commit path. If the sync scan exceeds 2 seconds, something is wrong with the pipeline or the diff is unusually large (in which case, scan async and allow the commit).
- **Use the `pre-commit` framework.** The Python `pre-commit` framework handles hook installation, virtual environment management, and hook lifecycle across OS environments. It’s the standard for Python projects and solves most of the "works on my machine" hook issues.

### Why This Tradeoff Is Still Worth It
The alternative (pre-push) lets secrets exist in local git history for minutes to hours. During that window:
- Any `git clone` or `git fetch` from a shared repo exposes the secret
- Any backup or sync tool that touches `.git/` captures the secret
- Removing it requires history rewriting (`filter-branch`, `BFG`), which is disruptive to the entire team

Pre-commit prevents the data from ever existing in a commit object. The edge cases above are solvable engineering problems. A leaked secret in git history is a security incident.

---

## 6. Scope Creep — The Hackathon Killer

### The Problem
At hour 20, someone on the team will say "wouldn't it be cool if we also added..." — a Slack integration, a VS Code extension, auto-fix suggestions, multi-language support, a mobile app. These ideas are good ideas. They are also the road to having nothing demoable at hour 48.

### Mitigation
- **The priority matrix in the roadmap document is law.** If it's not P0 or P1, it doesn't get built during the hackathon. No exceptions.
- **Write down the ideas.** When someone proposes a feature, add it to the post-hackathon roadmap. Acknowledge it, document it, and move on.
- **One person owns scope.** Designate a team lead who has veto power over new features. This feels bureaucratic for a hackathon, but it's the difference between winners and participants.

---

## 7. Demo Data Quality

### The Problem
Your tool is only as impressive as the problems it finds. If your demo diff is trivial, the findings will be trivial, and judges won't be impressed. If your demo diff is too complex, the audience won't follow what's happening. If your LLM returns a mediocre review, the demo falls flat regardless of how good your architecture is.

### Mitigation
- **Craft intentional demo scenarios.** Build 3–4 specific diffs that showcase each capability:
  - A diff with a planted AWS secret key and a hardcoded database password
  - A diff with PHI (patient name + SSN) in a data processing module
  - A diff with a SQL injection vulnerability and an insecure API endpoint
  - A real commit history with meaningful messages for report generation
- **Test the exact demo flow 5+ times.** Know exactly what the LLM will say for your demo inputs. If the output is inconsistent, adjust your prompts until it's reliable.
- **Pre-seed the database.** For the dashboard and reporting demo, pre-populate with 2–3 weeks of realistic scan history. Charts with two data points aren't compelling.

---

## 8. Team Coordination & Merge Conflicts

### The Problem
3–5 people building in parallel for 48 hours will create merge conflicts, especially around shared files (database models, API routes, shared types). In a hackathon, time lost to resolving conflicts is time lost to building features.

### Mitigation
- **Vertical slicing over horizontal.** Each person owns a vertical slice (e.g., "PHI detection end-to-end") rather than a horizontal layer ("all backend work"). This minimizes shared file conflicts.
- **Define interfaces early.** In Phase 0, agree on API contracts (endpoint paths, request/response shapes) and database schema. Frontend and backend can then work in parallel against those contracts.
- **Short-lived branches.** Merge every 2–3 hours. Long-lived branches and big-bang merges are the enemy.
- **One person owns the database models.** Schema changes go through one person to prevent migration conflicts.

---

## 9. Angular + Python Full-Stack Complexity

### The Problem
Running two separate technology stacks (Python backend, Angular frontend) means two build systems, two dependency managers, two debugging environments. For a small hackathon team, the cognitive load of context-switching is real.

### Mitigation
- **A startup script is mandatory.** Create `scripts/start_all.ps1` (Windows) and `scripts/start_all.sh` (Mac/Linux) that starts PostgreSQL, Redis, the backend (uvicorn), the Celery worker, and the frontend (`ng serve`) in sequence. One script, one command. No one should need to open five terminals and remember five commands.
- **Document the native install steps.** PostgreSQL and Redis installation varies by OS. Write a concise setup guide in the README or a separate `SETUP.md` that covers Windows (PostgreSQL installer + Memurai for Redis), macOS (Homebrew), and Linux (apt/dnf). Test it on a clean machine early.
- **API-first development.** Backend developers test with Swagger UI (auto-generated by FastAPI). Frontend developers test with mock data or the Swagger-generated client. They converge when both sides are stable.
- **If the team is small (2–3 people), consider simplifying the frontend.** A clean Angular Material dashboard with 4–5 well-designed views beats a complex frontend with half-broken features. Scope the frontend aggressively.

---

## 10. LLM Output Consistency

### The Problem
LLMs are non-deterministic. The same prompt with the same input can produce different outputs across calls. For a code review tool, this means the same vulnerability might be described differently each time, or worse, might not be flagged at all on some runs.

### Mitigation
- **Use structured outputs.** OpenAI's function calling / structured output feature forces the response into a predefined JSON schema. This ensures every review has the same structure even if the natural language varies.
- **Set temperature to 0 for code review.** You want deterministic, focused analysis — not creative writing. Temperature 0 (or near-zero) maximizes consistency.
- **Validate outputs with Pydantic.** Every LLM response should be parsed through a Pydantic model that enforces required fields, severity enums, and field types. If validation fails, retry once. If it fails again, return a degraded response rather than crashing.
- **Few-shot examples in your prompts.** Show the model exactly what you want the output to look like. This dramatically reduces output variance.

---

## Risk Summary Matrix

| Risk | Likelihood | Impact | Mitigation Effort | Priority |
|---|---|---|---|---|
| LLM latency on every commit | High | Critical | Medium (async + caching) | Immediate |
| False positives eroding trust | High | High | High (context classifier) | Phase 1 |
| OpenAI API outage during demo | Low | Critical | Low (mock mode) | Phase 2 |
| PHI detection inaccuracy | Medium | High | High (NER tuning) | Phase 1 |
| Scope creep | High | High | Low (discipline) | Ongoing |
| Pre-commit hook edge cases (rebase, merge, amend) | High | Medium | Medium (detection + skip logic) | Phase 4 |
| Hook bypass via `--no-verify` | Medium | High | Medium (server-side webhook safety net) | Phase 4 |
| Merge conflicts | Medium | Medium | Low (vertical slicing) | Ongoing |
| Demo data quality | Medium | High | Low (intentional prep) | Phase 5 |
| API cost overrun | Low | Medium | Low (budget limits) | Phase 0 |
| LLM output inconsistency | Medium | Medium | Medium (structured outputs) | Phase 2 |

---

## The One Thing That Will Make or Break Your Hackathon

It's not the technology. It's not the architecture. It's the **demo**.

You can have the most elegant architecture in the room, but if your demo is a mumbled walkthrough of code files and API responses, you'll lose to a team with a mediocre product and a killer presentation.

Allocate real time for demo preparation. Script it. Rehearse it. Have a backup plan. Know exactly which screen to show, which button to click, and which story to tell. The demo is the deliverable — everything else is in service of making those 5–10 minutes unforgettable.
