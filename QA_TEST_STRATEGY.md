# SLM-CIP Quality Engineering and Test Strategy

**Scope:** Smart Legal Metrology Compliance Inspection Platform (SLM-CIP), reviewed 15 September 2026.

## 1. Architecture review and risk model

SLM-CIP is a full-stack, asynchronous inspection system. Its important design boundary is sound: CV/OCR obtains evidence; the versioned deterministic rule engine makes the legal decision. Testing must preserve that boundary. A model may be wrong or uncertain, but it must never convert uncertainty into an unjustified compliant/non-compliant outcome.

| Layer | Implemented technologies and responsibility | Main test concern |
|---|---|---|
| Web client | Next.js 14, React 18, TypeScript, Tailwind; App Router screens and Axios API client | Correct state transitions, role-aware navigation, resilient async/error UI |
| Client state | `AuthContext`, `authUtils`, Axios JWT request/refresh interceptors; local component state for inspection and uploads | Expired/malformed tokens, concurrent 401 refresh, logout, unmounted polling and form retry states |
| API | FastAPI, Pydantic, async SQLAlchemy, OAuth2/JWT and RBAC | Authentication, authorization/tenant isolation, DTO validation, status/error contracts |
| Business/data | SQLAlchemy models/services, SQLite locally and PostgreSQL in Compose, Alembic | Transactionality, ownership filters, schema upgrade/downgrade, persistence integrity |
| Async processing | Celery plus Redis worker | Queue/retry/idempotency, status transitions, partial failures, no silent completion |
| Evidence pipeline | OpenCV quality/preprocessing, detector, OCR, regex extraction | Invalid media, quality thresholds, coordinate/data lineage, deterministic test doubles and model-regression corpus |
| Decision/reporting | JSON rule sets, RuleEngine/validators, compliance/audit services, PDF/DOCX output | Legal correctness, rule version provenance, four-state outcome, immutable audit and output rendering |
| Platform dependencies | Postgres, Redis, MinIO-compatible storage, Docker Compose | Service failures, credentials/configuration, recovery and performance |

### Primary data flow

```text
Officer login -> AuthContext/token storage -> Axios bearer + refresh
  -> FastAPI RBAC -> Inspection + Audit rows -> image validation/storage + quality result
  -> Celery/Redis -> preprocess -> detect regions -> OCR -> normalize fields
  -> versioned RuleEngine -> compliance/evidence/violation rows -> review/override + audit
  -> dashboard and PDF/DOCX reports -> browser
```

The frontend implements the operational flow primarily in `inspections/new`, `ImageUploadSlot`, the compliance page, and dashboard. `AuthContext` is the only global client state; other screen state is local. The worker persists intermediate `DetectedRegion`, `OCRResult`, `ExtractedField`, and compliance records, making data lineage and job idempotency essential.

### Critical paths, in priority order

1. **Legal decision integrity (P0):** rule applicability; missing, low (below 0.60), medium (0.60–below 0.90), and high-confidence fields; every validator; four legal states; rule/version mapping; overall-result precedence.
2. **Authorization and audit (P0):** JWT expiry/type/signature, role permissions, inspection ownership, overrides requiring justifications, and audit records that accurately show actor and before/after state.
3. **Inspection-to-evidence processing (P0):** secure upload, image quality handling, durable storage, Celery retry/failure/status behavior, and evidence-to-finding traceability.
4. **Database and API contract integrity (P1):** migrations, Postgres-specific behavior, concurrent review/evaluation, API error/status schemas, and duplicate task prevention.
5. **User workflow and recovery (P1):** login/refresh/logout, creation/upload/analyze/poll/review/report flows, loading/error states, refresh/retry, and responsive/a11y behavior.
6. **Reports, dashboard and admin operations (P2):** aggregate correctness, access restrictions, report generation/download/rendering, rule publication and audit search.

## 2. Current baseline and high-value findings

The current backend suite contains 27 tests in three files, largely validators/rule-engine cases plus a health check. The frontend has no test dependency or test script; neither coverage thresholds nor an E2E runner are configured. This is a useful start, but it is not representative of the risk surface above.

The execution environment did not expose a `python` executable, so the test command could not be run here. Independently, static inspection shows `test_quality_assessor_baseline` passes arbitrary undecodable bytes but expects `passed == True`; the implementation returns `passed == False` for undecodable input. That test should be corrected/split into a valid-image fixture test and an invalid-image rejection test before using it as a gate.

| Observation | Risk | Required test/control |
|---|---|---|
| `GET /inspections/{id}/analysis` returns a fixed 80%/EXTRACTING response and has no authentication dependency | Inaccurate workflow and potential inspection-status disclosure | Replace with persisted task state; test 401/403/404 plus queued/running/retry/failed/completed transitions |
| `PATCH /inspections/{id}` authorizes an Officer role but does not check that the inspection belongs to that Officer | Cross-inspection modification | Add ownership check and negative RBAC integration tests for every role/resource combination |
| Upload persistence writes a local filesystem path while Compose advertises MinIO | Deployment/storage contract can diverge and evidence can be lost or inaccessible | Test local and S3-compatible adapters against a common contract; use MinIO integration tests |
| Worker writes intermediate/result rows across multiple commits | Re-run, retry, or mid-job crash can duplicate findings or leave inconsistent statuses | Give jobs a persisted identity and idempotency key; test retries and crash injection at every stage |
| API tests use the application directly, but no isolated database/dependency override is established in `conftest.py` | Tests can couple to local state/startup configuration | Use disposable PostgreSQL/Testcontainers or Compose test DB, transaction rollback, seeded roles/rules |
| The single Alembic revision alters/adds columns rather than creating a baseline schema | A clean PostgreSQL upgrade needs verification | Run upgrade from empty DB, upgrade from prior release, downgrade/upgrade, and schema-diff checks in CI |

These are QA findings from source review, not fixes applied by this assessment. They should be triaged before calling the platform production-ready.

## 3. White-box (structural) test strategy

### Coverage policy

Measure coverage with `coverage.py`/`pytest-cov` on backend and Vitest coverage (`@vitest/coverage-v8`) on frontend. Do not use a single aggregate percentage to hide risk.

| Scope | Statement | Branch | Condition/decision | Additional requirement |
|---|---:|---:|---:|---|
| Rule engine, validators, auth/RBAC, services, worker orchestration | >=95% | >=90% | 100% for legal/security decisions | Mutation score >=80%; all legal state/transition table rows exercised |
| Parser/preprocessor/quality/detector/extractor | >=90% | >=85% | 100% for thresholds and error fallbacks | Golden corpus plus metamorphic/property tests |
| API routers/report generation | >=90% | >=85% | >=90% | Every documented error mapping and permission path |
| Frontend auth/api client/workflow components | >=85% | >=80% | >=90% for auth, refresh and UI decisions | Critical E2E scenarios must pass; visual coverage does not replace behavior coverage |
| Repository minimum gate during ramp-up | >=80% | >=75% | n/a | Ratchet upward; exclude generated/migration boilerplate only with justification |

### Control-flow and path testing

**RuleEngine and `FieldValidators`** must use a decision table and parameterized tests. For each rule, cover applicable/not-applicable category; absent field; confidence exactly 0.00, 0.599..., 0.60, 0.899..., 0.90, and 1.00; valid/invalid/ambiguous validator return; medium-confidence downgrade; generic-validator fallback; and every aggregate precedence result. Test malformed/missing `confidence`, `raw_value`, and normalized dictionaries so input validation cannot turn into a 500.

**Extractor and CV pipeline** need branch coverage for undecodable image, no Hough lines, vertical lines, angle exactly +/-0.5 degrees, image re-encode failure, each quality condition independently and in combination, empty OCR regions, regex match/no match/invalid number, every recognized region, and unknown region fallback. Use deterministic image fixtures and mock model adapters for structural unit tests; reserve real-model testing for a labeled corpus. For image transforms, use metamorphic assertions: original bytes remain unchanged; a small rotation yields expected deskew behavior; cropping stays in bounds; and normalized outputs remain stable under harmless whitespace/case variation.

**Worker paths** must be tested with eager Celery in unit tests and a real Redis worker in integration tests: missing inspection, no images, missing storage file, preprocessing fallback, zero regions/OCR spans, DB-rule version mapping missing, every exception/retry, and success. Assert the state machine, database rows, audit/event data, and cleanup/idempotency after each path. Add failure injection before/after every commit.

**Security/API paths** require white-box tests of invalid/missing/expired/wrong-token-type JWTs, UUID failures, inactive users, each allowed and denied role, officer-owned versus another officer’s resource, 404 versus 403 policy, pagination bounds, invalid multipart payloads, 0/10 MiB/10 MiB+1 boundaries, image extension/magic-byte mismatch, and override decisions with blank/whitespace/nonblank justification.

**Frontend structural tests** should test `AuthContext` hydration (valid, expired, malformed claims), successful/failed login and logout redirects, Axios single refresh, simultaneous 401 requests, refresh failure, and no refresh loop. Test `ImageUploadSlot`’s file type/size/drag/drop/progress/error/success transitions, the new-inspection wizard’s retries and disabled states, and compliance-page polling/cleanup/override UX. Use fake timers and MSW so tests execute deterministic API branches.

### Static and security analysis

Run these in pull-request CI and fail on new high-severity issues:

- Python: Ruff (already configured), Black, mypy/pyright, Pylint for complexity/duplication, Bandit, Semgrep (`p/python`, `p/fastapi`, `p/owasp-top-ten`), `pip-audit`, and `detect-secrets`/Gitleaks.
- TypeScript: `tsc --noEmit`, ESLint with `next/core-web-vitals`, `eslint-plugin-jsx-a11y`, Prettier, `npm audit --omit=dev`, and Semgrep TypeScript/React rules.
- Cross-cutting: SonarQube/SonarCloud for code smells, coverage, duplications and quality gates; Trivy for Docker images/config; Checkov for Compose/IaC; OWASP Dependency-Check/SBOM (CycloneDX).
- Set complexity alerts at cyclomatic complexity >10 and cognitive complexity >15. Any changed decision in legal/security code requires an explicit path-test table and reviewer sign-off.

## 4. Testing pyramid and execution plan

### Unit tests — largest, fast layer

Use **pytest + pytest-asyncio + pytest-cov + Hypothesis + Faker/factories** for backend; use **Vitest + React Testing Library + MSW + `@testing-library/user-event`** for frontend. Add Playwright only for browser-level tests.

- Pure backend: validators, rule loading/schema validation, `RuleEngine`, regex extraction, quality-score calculations, JWT/password helpers, URI/file-type validation, report value formatting, and dashboard aggregates.
- Service layer: fake/repository adapters or an ephemeral DB to verify query predicates, transaction behavior, audit payload construction, and overall result computation.
- UI: each component/page state as listed under structural tests; snapshots only for stable presentational components, never as the primary assertion.
- Property-based tests: generated legal quantities, price formats, dates and OCR noise; assert no exceptions, confidence bounds [0,1], a valid four-state enum only, and stable normalized semantics. Seed/report every failing Hypothesis example.

### Integration tests — real boundaries

Use a dedicated Compose test profile or Testcontainers for **PostgreSQL, Redis and MinIO**. Do not treat SQLite as proof of PostgreSQL compatibility.

- Migrations: clean `alembic upgrade head`; seeded-rule verification; `downgrade -1`/upgrade recovery where supported; upgrade a copy of the previous released schema; assert indexes, constraints, defaults and enum/null behavior.
- API: `httpx.AsyncClient` against FastAPI with a clean DB and real dependency overrides. Test request/response OpenAPI contracts (Schemathesis can fuzz them), auth/RBAC, inspection CRUD/ownership, multipart upload, quality persistence, analysis enqueue, manual compliance evaluation, review/audit, reports, dashboard and admin endpoints.
- Queue/storage: real Celery + Redis + MinIO test job from upload through persisted result. Exercise broker unavailable, worker unavailable, duplicate delivery, retry and storage unavailable.
- Contract compatibility: generate the FastAPI OpenAPI schema and validate typed client expectations; run consumer-driven API contract checks before backend/frontend deployment.

### End-to-end tests — small, decisive layer

Use **Playwright** with Chromium/Firefox/WebKit for the following seeded, repeatable journeys:

1. Officer logs in, creates a Packaged Food inspection, uploads valid front/back/label fixtures, sees quality feedback, starts analysis, observes real status, and sees compliance/evidence results.
2. Valid high-confidence evidence produces `COMPLIANT`; each required declaration absent produces `NON_COMPLIANT`; low/medium confidence produces `NEEDS_REVIEW`; excluded category yields `NOT_APPLICABLE`.
3. Reviewer confirms a finding; reviewer overrides one only after adding justification; audit and report show the decision/provenance.
4. Officer cannot view/edit another officer’s inspection; admin/reviewer permitted paths work; expired token silently refreshes once, failed refresh returns to login.
5. Upload rejection (oversize, extension/magic mismatch, corrupt media) is understandable and leaves no orphaned file/row.
6. Worker failure/retry is visible, does not display a fabricated completed result, and recovery works from a retry.
7. Report generation/download has findings, legal references, evidence and correct status; keyboard-only flow works.

Run a smoke subset per PR, all browsers nightly, and all release scenarios against a production-like deployment. Use stable fixture images and mock model mode for deterministic PR E2E; run a separate real-model candidate build against the labeled corpus.

### Non-functional quality

| Area | Tooling and scenario | Initial release acceptance target |
|---|---|---|
| Performance/load | k6 or Locust for login, list/dashboard, upload, enqueue, polling and report APIs; worker throughput tests with fixed image mix | Establish production-baseline SLOs; initially p95 read API <500 ms and p95 metadata write <1 s excluding upload/CV; no error-rate >1% at expected peak |
| Capacity/resilience | k6 soak, Celery/Redis backlog metrics, fault injection/Compose chaos (restart worker, Redis, DB, storage) | No lost job; explicit retry/failure state; bounded queue age and idempotent recovery |
| Security | OWASP ASVS/API Top 10 verification, ZAP authenticated DAST, Burp/manual authorization tests, SCA/container scans, secret scan, rate-limit and upload-malware assessment | No open critical/high finding; every endpoint authz-tested; security review of stored-token/XSS exposure |
| Accessibility | axe-core in Playwright, eslint JSX a11y, manual keyboard/screen-reader test, contrast/responsive zoom | No serious/critical axe findings; WCAG 2.2 AA for operational flows |
| Documents | Render generated PDF/DOCX to images and compare structured content/visual goldens | No clipped legal/evidence content; correct page count and accessible text |
| Observability | Structured logs, correlation IDs from API through Celery, metrics/traces, audit-log verification | Alert on queue age, task failures, 5xx, auth failures, and rule-result anomalies |

## 5. Exhaustive testing: feasibility and optimized substitute

Literal exhaustive testing is mathematically infeasible. Images alone have enormous pixel, encoding, language and lighting spaces; OCR/model behavior multiplies these. The combinations of user role, data state, rule version, field values/confidences, worker failure timing, browser and infrastructure state create an unbounded practical state space. Exhaustive path execution is also impossible once loops depend on image dimensions, OCR spans and database records.

The correct objective is **risk-based, bounded exhaustiveness**: exhaust every finite, safety/legal-critical partition and state transition; sample the remainder scientifically; continuously add real defects as regression tests.

### Test-case optimization method

1. **Equivalence partitioning.** Partition every input by behavior, not appearance. Examples: valid/invalid/missing/ambiguous MRP; recognized/unrecognized net-quantity unit; applicable/non-applicable category; valid/expired/wrong-type/malformed JWT; owner/non-owner/admin; supported/corrupt/magic-mismatch/oversize image. Choose at least one representative per partition, then one historical defect per high-risk partition.
2. **Boundary value analysis.** Test immediately below, at, and immediately above boundaries: OCR confidence `0.5999/0.60/0.6001` and `0.8999/0.90/0.9001`; quality score `0.6499/0.65/0.6501`; image dimension `479/480/481`; blur `39.9/40.0/40.1`; glare `7.99%/8%/8.01%`; file `0/10 MiB/10 MiB+1`; pagination `0/1/50/200/201`; and price/quantity `0/epsilon/maximum supported`.
3. **Decision tables and state-transition testing.** Exhaust the finite RuleEngine decision matrix: applicability x evidence existence x confidence band x validator outcome. Exhaust valid inspection lifecycle transitions (`draft -> analyzing -> completed/needs_review/failed`, retries and review outcomes) and reject every illegal transition. This is where exhaustive testing is both feasible and most valuable.
4. **Pairwise/orthogonal-array testing.** For combinatorial UI/API/CV scenarios, choose factors such as role (Officer/Reviewer/Admin), category, number/type of images, confidence band, rule result, pipeline outcome, browser and network condition. Generate a strength-2 covering array (for example with `allpairspy` or NIST ACTS), then elevate known coupled risks to strength-3: role x ownership x action; confidence x rule x normalized value; retry x persistence stage x storage outcome. Pairwise reduces a full factorial suite without losing interactions that typically cause defects.
5. **Combinatorial interaction testing plus fuzzing.** Use Hypothesis/Schemathesis to explore malformed request and parser combinations, retain shrinking counterexamples, and fuzz upload parsers in an isolated environment. Differential-test mock versus real extraction formats where their contract is shared.
6. **Risk-weighted corpus and mutation testing.** Maintain labeled image sets across languages, commodity categories, labels, quality defects, adversarial OCR errors, and production incidents. Track extraction precision/recall per field and false `COMPLIANT` rate as release gates. Apply mutation testing (mutmut/cosmic-ray) to legal/security code; surviving mutations identify tests that only execute code rather than verify its logic.

## 6. Delivery roadmap and quality gates

**Phase 1 — establish a trustworthy baseline (first):** fix/triage the observations above; add backend coverage reporting; add Vitest/RTL/MSW and Playwright scaffolding; make test configuration use a disposable Postgres/Redis/MinIO stack; add representative golden images and roles/rules fixtures.

**Phase 2 — protect P0 decisions:** complete RuleEngine decision table, validator/property/mutation tests, auth/ownership/audit integration tests, migration validation and idempotent worker tests. Enforce the P0 coverage targets before adding features.

**Phase 3 — operational confidence:** implement E2E journeys, performance baseline, a11y gate, authenticated DAST and resilience tests. Add real-model corpus evaluation with field-level metrics and human-review audit samples.

A pull request may merge only when formatting/type/static/security gates pass, affected unit/integration tests pass, no coverage metric regresses, migration checks pass when models change, and a reviewer confirms changed legal/security decision tables. A release additionally requires smoke E2E, full critical E2E, performance/security/a11y gates, and no untriaged P0/P1 defect.
