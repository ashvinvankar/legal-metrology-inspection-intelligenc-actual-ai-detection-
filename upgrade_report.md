# SLM-CIP Upgrade Report

**Review type:** Read-only architecture, source, security, and UI review  
**Date:** 18 September 2026  
**Scope:** FastAPI backend, Celery pipeline, storage/deployment setup, Next.js frontend, and test readiness.

## Executive summary

SLM-CIP has a sound core concept: use AI to extract evidence and a deterministic legal rule engine to make compliance decisions. The inspection workflow is present end-to-end, but the implementation is not yet safe to treat as production-ready.

The highest risks are authorization gaps around inspection-linked resources, public static evidence serving, insecure deployment defaults, incomplete admin/report workflows, and a frontend that mixes several visual styles. The first release milestone should be **security and workflow integrity**, followed by **operational completeness**, then **visual redesign and quality automation**.



---

## 1. Current system flow

```text
Officer login
  -> JWT issued and stored in browser localStorage
  -> Create inspection
  -> Upload package/label images
  -> Image-quality check and object storage
  -> Celery/Redis analysis job
  -> CV detection, OCR, field extraction
  -> Deterministic rules evaluation
  -> Compliance findings and evidence
  -> Officer/reviewer confirmation or override
  -> Dashboard and official report
```

### Main components

| Area | Current technology | Purpose |
|---|---|---|
| Web application | Next.js 14, TypeScript, Tailwind | Inspection, evidence, compliance, dashboard, admin views |
| API | FastAPI, SQLAlchemy | Authentication, RBAC, inspections, images, reports, rules |
| Processing | Celery, Redis, OpenCV, OCR, detector/Gemini integration | Image analysis and legal declaration extraction |
| Data | SQLite locally; PostgreSQL in Compose | Users, inspections, findings, reports, audit data |
| Evidence storage | Local storage or S3-compatible MinIO | Uploaded images and generated documents |

---

## 2. Priority remediation plan

### P0 — resolve before any pilot or external access

| Issue | Why it matters | Recommended upgrade | Acceptance criteria |
|---|---|---|---|
| Broken object-level authorization | An authenticated Officer may be able to access or alter another Officer's inspection-linked data through image, compliance, report, or copilot routes. | Create a single `require_inspection_access` dependency that loads the inspection and checks role, ownership, department, and permitted action. Apply it to every inspection-linked endpoint. | Tests prove an Officer receives 403 for every action on another Officer's inspection; authorized Reviewer/Admin paths remain valid. |
| Finding review by direct ID | `PATCH /compliance/{id}/review` checks role but does not first validate the inspection that owns the finding. | Resolve finding -> inspection -> authorization before any review/update. | A non-owner cannot confirm or override any foreign finding even when its UUID is known. |
| Public static evidence/report route | `/storage` is mounted as public static content, so authorization can be bypassed when a path is obtained. | Remove public evidence serving. Use authenticated downloads or short-lived, scoped, signed object-store URLs generated only after authorization. | Unauthenticated requests never retrieve evidence or reports; signed URLs expire and are restricted to the intended object. |
| Insecure default secrets | JWT, database, and MinIO credentials have deployable defaults; Compose exposes infrastructure ports. | Require all production secrets from a secret manager/environment; refuse production startup when defaults are detected. Bind Postgres, Redis, and MinIO to internal networks unless explicitly required. | Deployment fails safely with weak/missing secrets; vulnerability scan finds no default credentials. |
| External AI data controls | Copilot can send inspection data/images to an external model without visible consent, policy, or audit controls. | Add data classification, explicit AI-use policy, redaction/minimization, per-inspection consent configuration, audit entries, rate limits, and provider retention controls. | Every AI request is authorized, auditable, policy-checked, and contains only necessary data. |

### P1 — complete before production launch

| Issue | Recommended upgrade | Acceptance criteria |
|---|---|---|
| Reusable refresh tokens in localStorage | Use `HttpOnly`, `Secure`, `SameSite` cookies; rotate refresh tokens; persist token families; revoke on logout/password change; detect reuse. | XSS cannot read refresh token; reuse of rotated token invalidates family. |
| No abuse controls for authentication/API | Add rate limiting by IP/user, failed-login backoff, structured security events, and alerting. | Brute-force tests are throttled and logged. |
| Incomplete admin modules | Replace hard-coded user, rule, and audit pages with live APIs, loading/error states, filters, permissions, and explicit empty states. | No mock records appear in production UI; role-specific workflows function end-to-end. |
| Report UX disconnected from backend | Connect report page to generation, status, download, and revision APIs. Avoid browser print as the official record. | Generated PDF/DOCX is stored, audited, downloadable, and displays its provenance. |
| Job duplication/concurrency | Add idempotency keys and enforce one active job per inspection/action. Use a formal job state machine. | Repeated requests return the existing active task; retries do not duplicate evidence/findings. |
| Organization-wide dashboard exposure | Apply Officer/department scope to violation and trend queries, not only summary data. | Data returned matches role and jurisdiction policy. |
| Audit immutability is only conventional | Use restricted DB permissions; append-only controls; audit row hashes/chaining; immutable storage/export for legal records. | Application role cannot update/delete audit records; integrity verification detects tampering. |

### P2 — operational hardening

- Add malware scanning and image decoder hardening before durable storage.
- Enforce a server-side allow-list for `image_type`; do not accept arbitrary form values.
- Add report retention, legal hold, purge, backup, and restore policies.
- Add correlation IDs from browser request through Celery task and audit event.
- Establish metrics and alerts for login failures, queue age, task failure, storage errors, and 5xx responses.
- Pin/review dependency versions and run SCA/container scans in CI.

---

## 3. Confirmed source-review findings

| Finding | Key locations |
|---|---|
| Default JWT and storage credentials | `backend/app/core/config.py` |
| Public `/storage` static mount | `backend/app/main.py` |
| Image routes lack inspection ownership enforcement | `backend/app/api/v1/images.py` |
| Compliance read/evaluate/review routes lack a consistent inspection authorization check | `backend/app/api/v1/compliance.py` |
| Report generation/read/download lack inspection-level authorization | `backend/app/api/v1/reports.py` |
| Copilot route loads inspection evidence without ownership check | `backend/app/api/v1/copilot.py` |
| Refresh token is reused and frontend persists tokens in localStorage | `backend/app/api/v1/auth.py`, `frontend/src/contexts/AuthContext.tsx`, `frontend/src/lib/api.ts` |
| Admin pages contain hard-coded sample data | `frontend/src/app/admin/*/page.tsx` |
| Users/rules API handlers return placeholders | `backend/app/api/v1/users.py`, `backend/app/api/v1/rules.py` |
| Frontend has no test command/dependency setup | `frontend/package.json` |

---

## 4. Frontend redesign brief

### Problem statement

The frontend currently combines an official enforcement workflow with soft SaaS cards, glass panels, gradients, animated glows, shimmer, and multiple badge treatments. The result is visually busy and reduces confidence in a legal/inspection tool.

### Design goal

Create a restrained **Legal Metrology Operations Console**: readable, evidence-led, trustworthy, accessible, and optimized for long work sessions.

### Theme direction

| Element | Recommendation |
|---|---|
| Brand palette | Deep navy/ink, off-white, slate neutrals, one official blue/indigo accent. Use green/amber/red only for semantic legal states. |
| Typography | One sans-serif family, four predictable sizes, body text at least 14px, avoid frequent 10–11px text. |
| Cards | White surface, thin neutral border, restrained shadow, consistent 8px or 12px radius. |
| Motion | Use only for real progress, task status, and user-triggered transitions. Remove decorative shimmer/glow/pulse. |
| Status | Standardize `COMPLIANT`, `NON_COMPLIANT`, `NEEDS_REVIEW`, `NOT_APPLICABLE`, `DRAFT`, `RUNNING`, `FAILED`. Never use color alone. |
| Layout | Collapsible desktop sidebar; mobile drawer; clear page title/action bar; persistent workflow state. |
| AI | Present as “AI extraction assistance,” with confidence and source evidence. Do not visually overstate AI compared with legal rules and officer judgment. |

### Recommended screen structure

```text
Top bar: product identity | task state | user menu

Sidebar: Dashboard | Inspections | Rules | Users | Audit

Inspection workspace:
  Inspection header: ID, product, owner, status, primary action
  Workflow rail: Draft -> Evidence -> Analysis -> Declarations -> Compliance -> Review -> Report
  Main content: one task at a time
  Context panel: evidence quality, audit activity, AI assistant
```

### Frontend work items

1. Define design tokens in Tailwind: colors, typography, spacing, borders, shadows, statuses.
2. Replace page-level one-off styles with reusable `Button`, `Card`, `DataTable`, `StatusBadge`, `EmptyState`, `ErrorState`, and `PageHeader` components.
3. Remove duplicated user/profile/logout UI in header and sidebar.
4. Replace static admin examples with empty/loading/error/live data states.
5. Route newly queued analyses to the progress page, then advance after task completion.
6. Add draft autosave, upload retries, unsaved-change notice, task cancellation/retry, and clear failure explanations.
7. Add keyboard support, focus traps for drawers, labels for controls, skip navigation, and WCAG 2.2 AA contrast checks.
8. Add responsive breakpoints and a compact mobile navigation approach.

---

## 5. Functional upgrade backlog

### Inspection and workflow

- Define workflow transition policy: `draft -> evidence_ready -> queued -> analyzing -> needs_review/completed -> reported`.
- Reject illegal transitions on the server.
- Persist task attempt, source inputs, model version, rule version, and result provenance.
- Support cancel, retry, re-analyze, and archival with audit history.
- Add clear empty states for no images, no OCR, no findings, and failed analysis.

### Evidence and legal decisions

- Preserve immutable original evidence; clearly distinguish processed/cropped derivatives.
- Record source image, region, OCR span, model/provider version, and confidence for every extracted declaration.
- Require justification for every manual correction and override.
- Version rule sets with draft/review/publish/supersede stages, legal source documents, effective dates, approval identity, and rollback.
- Show rule citation, evidence, confidence, and officer action together in compliance review.

### Reporting

- Generate authoritative PDF/DOCX server-side only.
- Include report revision, rule version, evidence references, QR verification, signed/audited issuance metadata, and download history.
- Render-test generated documents to catch clipping and missing content.

### Administration

- Implement real user lifecycle: create, invite/reset, activate/disable, role assignment, department assignment, session revocation.
- Add rule authoring, version comparison, approvals, scheduled activation, and audit history.
- Build audit search with filters, pagination, exports, access scope, and tamper-verification status.

---

## 6. Testing and quality plan

### Immediate test additions

| Layer | Recommended tools | Required coverage |
|---|---|---|
| Backend unit/API | Pytest, pytest-asyncio, pytest-cov, Hypothesis, httpx | Auth, ownership, state transitions, rule outcomes, upload bounds, report access |
| Frontend unit/component | Vitest, React Testing Library, MSW | Auth restore/login/refresh, upload states, workflow state, errors, role UI |
| E2E | Playwright | Officer inspection journey, reviewer override, unauthorized access, failed job recovery, report download |
| Integration | PostgreSQL, Redis, MinIO test stack | Migrations, storage, Celery retries, idempotency, cross-service behavior |
| Security | Bandit, Semgrep, pip-audit, npm audit, Gitleaks, Trivy, OWASP ZAP | Secrets, dependencies, authorization, upload/API attack surface |

### Minimum release gates

- No open P0/P1 security issue.
- Every protected endpoint has tests for missing token, invalid token, wrong role, correct owner, wrong owner, and privileged user.
- Full inspection journey passes against PostgreSQL, Redis, and MinIO.
- Rule-engine decision tables cover every legal state and confidence boundary.
- Frontend TypeScript, linting, accessibility checks, and critical Playwright suite pass.
- Migration from a clean database and previous release schema passes.
- Generated report rendering is verified.

---

## 7. Suggested delivery sequence

### Sprint 1: security and access foundation

- Introduce resource authorization dependency and apply it everywhere.
- Secure storage/report delivery.
- Replace deployment defaults with required secrets and internal networking.
- Add API ownership test matrix.

### Sprint 2: workflow integrity

- Implement task idempotency and state machine.
- Connect progress, compliance, and report screens to live status/data.
- Implement report generation/download flow.
- Add job retry/failure recovery.

### Sprint 3: administration and audit

- Implement live users, rules, and audit modules.
- Add department/jurisdiction scoping.
- Strengthen immutable audit controls and verification.

### Sprint 4: design system and accessibility

- Establish operations-console design tokens/components.
- Redesign dashboard, repository, inspection pages, and admin tables.
- Add responsive navigation and accessibility improvements.

### Sprint 5: release confidence

- Build CI quality/security gates.
- Run full integration, E2E, load, DAST, and report-render testing.
- Complete operational runbooks, backup/restore drill, and incident response plan.

---

## 8. Definition of production-ready

SLM-CIP should be considered production-ready only when:

1. Every inspection-linked action is protected by verified object-level authorization.
2. Evidence and reports cannot be retrieved without authorization.
3. Production cannot start with default credentials or weak secrets.
4. Admin, rule, audit, and official report workflows are real—not sample/stub experiences.
5. Analysis jobs are idempotent, observable, retryable, and legally traceable.
6. The UI follows a single accessible, evidence-first design system.
7. Security, integration, E2E, migration, and report-render tests are automated in CI.

