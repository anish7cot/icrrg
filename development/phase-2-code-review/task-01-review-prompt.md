# Task 01 — Design Code Review Prompt

**Owner:** ML Lead · **Est:** 2 hr

## Before You Start

- [x] You have an OpenAI API key with GPT-4 access
- [x] You understand the diff format from Phase 1 Task 01
- [x] You've reviewed OWASP Top 10 categories for reference

## Steps

- [x] Create `backend/app/review/prompts/system.py` — the system prompt that defines the reviewer persona
- [x] Define the reviewer as a senior security engineer; output must be structured JSON
- [x] Create output schema: array of findings, each with `severity`, `category`, `file`, `line`, `issue`, `explanation`, `suggestion`
- [x] Create `backend/app/review/prompts/few_shot.py` — 2–3 example input/output pairs
- [x] Include examples covering: SQL injection, hardcoded credential, insecure HTTP usage
- [x] Test the prompt manually in the OpenAI playground with a sample diff
- [x] Iterate until the output is consistently structured and useful

## Challenges

- **LLM output is non-deterministic.** Same prompt, different output each run. Use `temperature=0`, structured outputs, and few-shot examples to maximize consistency.
- **Prompt too long = expensive + slow.** Keep the system prompt under 500 tokens. The diff is the payload; the prompt is the instructions.
- **Don't ask the LLM to "find everything."** Be specific: "Identify security vulnerabilities, data leaks, and anti-patterns. Ignore style issues." Focus produces better results.
- **Use GPT-4o-mini for prompt iteration** — 10x cheaper. Switch to GPT-4/4o only for final testing.

## Done

- [x] Prompt produces structured JSON findings from a test diff in OpenAI playground

---
> **Note:** Mark all checklist items `[x]` after completing this task.
