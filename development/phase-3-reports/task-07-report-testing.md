# Task 07 — Test Reports with Realistic Data

**Owner:** Everyone · **Est:** 1 hr

## Before You Start

- [x] Report pipeline works end-to-end for at least one audience role
- [x] Database has sufficient scan history (seed if needed)

## Steps

- [x] Seed database with 30+ realistic scan records across 2–3 weeks (use `scripts/seed_demo_data.py`)
- [x] Generate Developer report — verify it includes technical details and code references
- [x] Generate EM report — verify it includes delivery metrics and team contributions
- [x] Generate Leadership report — verify it uses business language, no jargon
- [x] Compare all three side-by-side — they must feel genuinely different
- [x] If any report is weak, adjust the corresponding prompt template and regenerate
- [x] Save the best generated reports as demo backup (in case LLM is slow during live demo)

## Challenges

- **Seeding realistic data is non-trivial.** Create a script that generates varied commits with different authors, files, and finding types. Monotonous data = monotonous reports.
- **If all three reports look the same, the prompt templates aren't distinct enough.** The dev report should mention file names and line numbers. The EM report should mention sprint velocity. The leadership report should mention business risk.
- **Save the outputs.** These become your demo fallback if the API is slow during presentation.

## Done

- [x] Three visibly distinct reports generated from same data
- [x] Demo data seeded and reports saved as backup
- [x] ✅ PHASE 3 COMPLETE — third demoable milestone

---
> **Note:** Mark all checklist items `[x]` after completing this task.
