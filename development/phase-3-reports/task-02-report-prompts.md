# Task 02 — Role-Specific Report Prompt Templates

**Owner:** ML Lead · **Est:** 2 hr

## Before You Start

- [x] You have the aggregation output structure from Task 01
- [x] You understand what each audience (Dev, EM, Leadership) cares about

## Steps

- [x] Create `backend/app/reports/templates/` with Jinja2 templates for each role:
  - [x] `developer.j2` — technical changelog: what changed, what broke, what was fixed, security findings
  - [x] `manager.j2` — delivery summary: features completed, bugs fixed, velocity, risk areas, team contributions
  - [x] `leadership.j2` — business narrative: release readiness, risk posture, high-level feature summary
- [x] Each template takes the aggregated data and produces a structured prompt for the LLM
- [x] Include explicit instructions for tone and detail level per role
- [x] Test each prompt in OpenAI playground with sample aggregated data

## Challenges

- **The three reports must feel genuinely different.** If they look similar with different headings, the demo point is lost. Dev report should have code references. EM report should have metrics. Leadership report should have zero jargon.
- **Templates get the data in shape — LLM provides the narrative.** Don't try to have the template generate the report. Let it structure the prompt, and let the LLM write naturally.
- **If time is short, build one role first** (EM report is usually most impressive for judges). Add the other two as variations.

## Done

- [x] Three prompt templates produce distinct, role-appropriate instructions for LLM

---
> **Note:** Mark all checklist items `[x]` after completing this task.
