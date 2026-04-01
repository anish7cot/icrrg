# Task 01 — Commit History Aggregation Service

**Owner:** Backend · **Est:** 2 hr

## Before You Start

- [x] Database has scan and finding data from Phases 1–2
- [x] You have realistic commit history to query (seed data if needed)

## Steps

- [x] Create `backend/app/reports/aggregator.py`
- [x] Query scans within a date range, join with scan findings
- [x] Group data by: module/file path, author, severity, finding type
- [x] Calculate summary metrics: total commits, total findings, findings by severity, most common issues
- [x] Return as a structured Pydantic model that the prompt builder can consume
- [x] Create `POST /api/v1/reports` endpoint — accepts date range, repo, audience type
- [x] Test: query last 2 weeks of data → get structured aggregation

## Challenges

- **You probably don't have 2 weeks of real data.** Seed the database with realistic mock data early. A report generated from 3 commits is unconvincing. Aim for 30+ commits with varied findings.
- **Aggregation query performance doesn't matter for hackathon.** Don't optimize. A simple query that works beats an optimized query that you spent 45 minutes on.

## Done

- [x] Aggregation returns structured summary for any date range
- [x] Report API endpoint accepts config and returns aggregated data

---
> **Note:** Mark all checklist items `[x]` after completing this task.
