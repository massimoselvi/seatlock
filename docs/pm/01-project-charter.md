# Project Charter

| | |
|---|---|
| Project | Seatlock |
| Version | 1.0, issued 2026-10-23 |
| State | Approved 2026-10-23 |
| Sponsor, project manager, tech lead | Massimo Selvi |
| Repository | `massimoselvi/seatlock` (public) |

> **Initiation note.** Work started on 2026-10-20 and this charter is issued on day 4. It formalizes a project that is already under way. The scope below is rebuilt from the README, the ADRs, the issues and the milestones, not from a document that existed on day 1. The first four milestones had due dates, so the early plan can be compared with what happened. See the [baseline](03-estimates-and-schedule-baseline.md#1-completed-work-plan-and-actual).

## 1. Purpose and justification

**Problem.** A workshop has a fixed number of seats. When many people try to book the last seat at the same moment, a naive system sells it twice.

**Project.** Build Seatlock: a workshop booking system whose one promise is that **a seat is never sold twice**. Attendees register, join a waitlist when a workshop is full, and cancel. A freed seat goes to the oldest person waiting. Organizers see who registered.

**Why this project exists.** It is a reference project. Its value is the evidence it leaves: a hard concurrency problem solved and *proved*, a backend whose rules can be tested without a database, infrastructure written as code, and decisions recorded as ADRs. A reader should be able to check each claim in the repository.

## 2. Objectives and success criteria

| # | Objective | Measure | Target | Status on 2026-10-23 |
|---|-----------|---------|--------|----------------------|
| O1 | Seats are never oversold | Confirmed seats after 200 simultaneous requests for 10 seats | Exactly 10, in every run | **Met.** 8 of 8 runs. The same test on code without the lock confirmed up to 24. |
| O2 | The code is tested and the checks are green | Backend line coverage, and CI on every pull request | At least 95%, all checks pass | **Met.** 98% (1,150 statements). 76 backend, 40 frontend and 16 infra tests. |
| O3 | The architecture is deployable | A real AWS deployment, verified, then destroyed | Done once, cost at most 10 USD | **Not met yet.** Blocked on the dry run ([#43](https://github.com/massimoselvi/seatlock/issues/43)). Planned by 2026-10-28. |
| O4 | The service is hardened | Issues of milestone v0.6 closed | All 13 open issues and the 3 added items, by the baseline date | **In progress.** 1 of 14 issues closed. Baseline finish 2026-12-09. |
| O5 | Decisions and structure are documented | ADRs for each hard-to-reverse decision, C4 model, runbooks | Every such decision has an ADR | **Met.** 6 ADRs, 23 C4 views, 3 runbooks, an SLO document. |

The source code is **delivered on 2026-10-23** (milestone v1.0). At delivery O1, O2 and O5 are met. O3 and O4 are not, and are listed as known limits. They continue as the hardening release v0.6 after delivery. The project is **complete** when O1 to O5 are met and the [Implementation Plan](../product/06-implementation-plan.md) exit criteria for phase E hold. See [CR-011](05-change-request-log.md#cr-011).

## 3. Scope

### In scope

- The product described in the [PRD](../product/01-prd.md): accounts, the workshop list, registration with a waitlist, cancellation with promotion, the organizer dashboard.
- A Django API, a Vue single-page app, a Celery worker, PostgreSQL and Redis.
- Infrastructure as code (AWS CDK) for a demo and a production-like environment, and the deployment guide.
- CI: lint, tests, the load test, the architecture checks.
- The documents in [docs/](../../README.md): ADRs, C4 model, runbooks, SLOs, the plan and these project documents.

### Out of scope

- Payments, ticketing for money, invoices.
- Email verification, password reset, social login.
- Mobile apps and native clients.
- Operating a public, always-on production service for real users. A demo can be public only after phase C of the plan.
- Creating workshops in the UI. Today a workshop is created in the Django admin or by a one-off task. This is a known gap, recorded as an open question in the PRD.

### Deliverables

| Deliverable | State |
|-------------|-------|
| Backend API and worker | Delivered |
| Single-page app | Delivered |
| Test suites and the load test | Delivered |
| CI workflows (checks, load test, architecture) | Delivered |
| ADRs 0001 to 0006, C4 model, runbooks, SLOs | Delivered |
| CDK stacks and the deploy guide | Written, **not yet run on AWS** |
| Hardening (milestone v0.6) | In progress |
| Product, technical and project documents | Issued with this charter |

## 4. Approach

- **Incremental, milestone by milestone.** v0.1 Foundation, v0.2 Registration, v0.3 Operations, v0.4 Deploy, v0.5 Security, v0.6 Hardening. Each milestone is a GitHub milestone.
- **Small changes through pull requests.** `main` changes only through a PR, and the checks must pass. Each PR does one thing and says how it was verified.
- **Decisions before code when they are hard to reverse.** The decision goes into an ADR. The [change workflow](05-change-request-log.md#workflow) decides when.
- **Prove, do not assert.** A guarantee gets a test that fails when the guarantee breaks. The lock has a concurrency test and a load test with a control run.
- **Plan in hours, report weekly.** Estimates use three points. A weekly status report compares the plan with the facts.

## 5. Milestones

| Milestone | Planned | Actual | Result |
|-----------|---------|--------|--------|
| v0.1 Foundation | 2026-10-20 | 2026-10-20 | On time |
| v0.2 Registration | 2026-10-21 | 2026-10-21 | On time |
| v0.3 Operations | 2026-10-22 | 2026-10-21 | 1 day early |
| v0.4 Deploy | 2026-10-23 | 2026-10-21 | 2 days early |
| v0.5 Security | none | 2026-10-21 | Added after the first review |
| **v1.0 Source delivery** | 2026-10-23 | 2026-10-23 | Delivered with known limits ([CR-011](05-change-request-log.md#cr-011)) |
| v0.6 Hardening, phase A to E | 2026-12-09 (baseline) | | After delivery. See the [schedule](03-estimates-and-schedule-baseline.md#4-schedule). |

## 6. Budget

| Item | Amount | Basis |
|------|-------:|-------|
| Labor | 0 cash | The owner's time. Planned at about 94 hours, including the reserve. |
| AWS dry run | up to 10 USD | A budget alarm at 10 USD. The [cost analysis](../cost-analysis.md) estimates about 3 USD for a one-day demo. |
| Domain name for HTTPS to the load balancer (issue #47) | not yet quoted | A certificate needs a domain. **Decision needed.** |
| Tools and services | 0 | Free tiers and open source. |

The cost of keeping the demo running is 0.12 to 0.16 USD an hour, or 113 to 177 USD a month. It is destroyed after each session.

## 7. Assumptions, constraints, dependencies

**Assumptions**

- A1. The owner can spend about 15 productive hours a week. This is the main planning parameter. The schedule shows 10 and 20 hours too.
- A2. A sandbox AWS account is available and its login works.
- A3. No real user data is stored in any environment.

**Constraints**

- C1. One contributor.
- C2. The repository is public, so no secrets, no personal data and no client data go into it.
- C3. The seat rules stay inside the domain and application layers ([ADR 0005](../architecture/adr/0005-clean-architecture-experiment.md)).
- C4. PostgreSQL must be a real PostgreSQL, reached directly or through a pooler in session mode ([ADR 0003](../architecture/adr/0003-target-aws-architecture.md)).

**Dependencies**

- D1. AWS: the sandbox account, quotas, and the policies of its organization (not yet checked).
- D2. GitHub: Actions minutes, the Project board.
- D3. Open-source tools: Django, DRF, Celery, Vue, UnoCSS, Structurizr. A change in any of them can cost time. Structurizr Lite already became a stub during this project.

## 8. Risks

Scored 1 to 3. Score is probability times impact. The register is re-read in every [status report](04-weekly-status-report.md).

| ID | Risk | P | I | Score | Response | Trigger |
|----|------|:-:|:-:|:-----:|----------|---------|
| R1 | The AWS dry run finds deployment defects (quotas, IAM, organization policies), and fixing them costs more than planned | 2 | 2 | 4 | A read-only preflight script exists. Run in a dedicated sandbox account. Time-box to the estimate and re-plan. | A preflight check fails |
| R2 | A cloud environment is left running and costs more than the cap | 2 | 2 | 4 | Budget alarm at 10 USD. `DestroyBy` tag on every resource. A destroy gate in the plan. | Spend above 50% of the cap |
| R3 | The 15 hours a week assumption is wrong, so the schedule slips | 2 | 2 | 4 | 20% reserve. Weekly re-forecast. Sensitivity table in the baseline. | A phase finishes more than 2 days late |
| R4 | Documentation and tooling grow faster than the product (42 PRs in 4 days, many of them documents) | 3 | 1 | 3 | The change workflow. A capacity cap for the Product and Content workstream. | More than 25% of hours on that stream |
| R5 | A public link appears before the security hardening is done (13 open issues) | 1 | 3 | 3 | No public demo before phase C. The demo holds only fake data. | Someone asks for a link |
| R6 | A write bypasses the use cases and the lock (Django admin, a shell) and oversells a seat | 1 | 3 | 3 | The admin is off in AWS. A runbook exists. The oversold-seats alarm (#46) is in phase B. | An oversold alarm |
| R7 | A promotion email or a queued promotion is lost after a commit (ADR 0002 gap) | 2 | 1 | 2 | The sweep in phase E. The recovery steps are in the queue runbook. | A user reports a missing email |
| R8 | A tool changes or is withdrawn | 2 | 1 | 2 | Pin versions. Record the change in the change log. | A deprecation notice |

## 9. Roles and authority

| Role | Holder | Authority |
|------|--------|-----------|
| Sponsor | Massimo Selvi | Approves the charter, the baseline and any change to scope, schedule or cost. |
| Project manager | Massimo Selvi | Plans, tracks, reports, runs the change workflow. |
| Tech lead | Massimo Selvi | Decides architecture, through ADRs. |
| Reviewer | CI checks, then the owner | A change merges when the checks pass and the owner has read it. |

With one person in every role, the controls that protect the project are the written ones: the baseline, the change log, the ADRs and the CI gates.

## 10. Approval

| Role | Name | Decision | Date |
|------|------|----------|------|
| Sponsor | Massimo Selvi | Approved | 2026-10-23 |
