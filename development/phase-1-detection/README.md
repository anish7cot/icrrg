# Phase 1 — PHI & Secret Detection (Hours 4–14)

Submit a code diff → get back detected PHI/secret leaks with confidence scores.

## Tasks

| # | Task | Owner | Est. |
|---|---|---|---|
| 01 | [Diff parsing service](task-01-diff-parser.md) | Backend | 1.5h |
| 02 | [Regex rule engine for secrets](task-02-regex-secrets.md) | ML / Backend | 2h |
| 03 | [Entropy analysis](task-03-entropy.md) | ML / Backend | 1.5h |
| 04 | [spaCy NER for PHI](task-04-ner-phi.md) | ML Lead | 2h |
| 05 | [Scan API endpoint](task-05-scan-api.md) | Backend Lead | 1.5h |
| 06 | [Angular scan submission view](task-06-scan-ui.md) | Frontend | 1.5h |
| 07 | [Findings display component](task-07-findings-display.md) | Frontend | 1.5h |
| 08 | [Test with planted secrets + PHI](task-08-integration-test.md) | Everyone | 1h |

## Exit Criteria

- [ ] Paste a diff with a hardcoded AWS key and a patient SSN
- [ ] System identifies both with correct severity and entity type
- [ ] Results display in the Angular UI
