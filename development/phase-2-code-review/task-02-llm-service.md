# Task 02 — LLM Service Wrapper

**Owner:** Backend · **Est:** 1.5 hr

## Before You Start

- [x] OpenAI Python SDK is installed (from Phase 0 Task 01)
- [x] API key is in `.env` and loadable via config

## Steps

- [x] Create `backend/app/llm/base.py` — abstract interface with a `review(diff)` method
- [x] Create `backend/app/llm/openai_provider.py` — implements the interface using OpenAI SDK
- [x] Use structured outputs / function calling to enforce JSON response schema
- [x] Add retry logic: retry once on timeout or rate limit, then fail gracefully
- [x] Set hard timeout: 30 seconds max per call
- [x] Create `backend/app/llm/mock_provider.py` — returns canned responses for testing/demo backup
- [x] Make provider choice configurable via `.env` variable (`LLM_PROVIDER=openai` or `mock`)

## Challenges

- **OpenAI rate limits will hit you during rapid testing.** Use mock provider during frontend dev. Switch to real API for integration testing only.
- **API costs add up fast.** Each GPT-4 call on a decent-sized diff costs $0.10–$0.50. Budget $20–$50 for the entire hackathon.
- **Mock provider is your demo insurance.** If OpenAI goes down mid-demo, switch to mock. Pre-load it with impressive responses for your demo diffs.

## Done

- [x] `openai_provider.review(diff)` returns structured findings
- [x] `mock_provider.review(diff)` returns canned findings instantly
- [x] Provider is switchable via config

---
> **Note:** Mark all checklist items `[x]` after completing this task.
