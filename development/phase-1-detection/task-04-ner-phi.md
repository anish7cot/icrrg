# Task 04 — spaCy NER Pipeline for PHI Detection

**Owner:** ML Lead · **Est:** 2 hr

## Before You Start

- [x] spaCy and `en_core_web_sm` model installed (Task 01)
- [x] You understand what counts as PHI: names in patient context, SSN, MRN, DOB, phone numbers

## Steps

- [x] Create `backend/app/detection/ner_pipeline.py`
- [x] Load spaCy model and configure NER pipeline
- [x] Define PHI-specific regex patterns that complement NER:
  - [x] SSN format: `\d{3}-\d{2}-\d{4}`
  - [x] Phone numbers: common US formats
  - [x] MRN-like patterns: labeled numeric IDs
  - [x] Date of birth: dates near keywords like `dob`, `birth`, `patient`
- [x] Use spaCy NER to detect PERSON entities, then check surrounding context for healthcare keywords
- [x] Each finding returns: entity text (redacted), entity type, line number, file path, confidence
- [x] Test with sample code containing patient data

## Challenges

- **"John Smith" is not always PHI.** It's PHI when next to a diagnosis. It's just a name when it's a developer or test author. Use keyword proximity (look for `patient`, `diagnosis`, `mrn` within N lines).
- **spaCy's default PERSON NER is broad.** It'll flag every name in the codebase. Without context filtering, this is useless noise. Focus on high-precision: only flag names that appear near healthcare keywords.
- **Demo trick:** Use obviously fake but realistic PHI in your test diffs (`Jane Doe, SSN: 123-45-6789, MRN: 00112233`). It shows the capability without ambiguity.

## Done

- [x] Detects SSN pattern and patient name in a healthcare code snippet
- [x] Does NOT flag developer names in comments or commit messages

---
> **Note:** Mark all checklist items `[x]` after completing this task.
