# Project management

How Seatlock is run as a project. The structure follows the **PMBOK 7 performance domains**, kept light for a one-person project. The product and technical documents are in [../product/](../product/README.md).

| Status | |
|--------|--|
| Version | 1.0, issued 2026-10-23 (project day 4) |
| State | **Proposed baseline.** It becomes the baseline when the owner approves it in the table at the end of this page. |
| Owner | Massimo Selvi (sponsor, project manager and tech lead) |

## The documents

| # | Document | What it answers |
|---|----------|-----------------|
| 1 | [Project Charter](01-project-charter.md) | Why the project exists, what it delivers, who decides. |
| 2 | [Stakeholder Register and Engagement Matrix](02-stakeholder-register.md) | Who is affected, what they expect, how we engage them. |
| 3 | [Estimates and Schedule Baseline](03-estimates-and-schedule-baseline.md) | How long the remaining work takes, and how the finished work compared with its plan. |
| 4 | [Weekly PM Status Report](04-weekly-status-report.md) | The template, and the reports in [reports/](reports/). |
| 5 | [Change Request Log and Workflow](05-change-request-log.md) | How a change to scope, schedule, cost or architecture is decided and recorded. |
| 6 | [Workstream Structure](06-workstream-structure.md) | The two workstreams, who does what, and where each issue belongs. |

## PMBOK 7 performance domains

| Domain | Where it is handled |
|--------|---------------------|
| Stakeholders | [Stakeholder Register](02-stakeholder-register.md) |
| Team | [Workstream Structure](06-workstream-structure.md) (roles, RACI) |
| Development approach and life cycle | [Charter](01-project-charter.md#4-approach) and [Implementation Plan](../product/06-implementation-plan.md) |
| Planning | [Estimates and Schedule Baseline](03-estimates-and-schedule-baseline.md) |
| Project work | [Change Request Log](05-change-request-log.md), the GitHub Project and the milestones |
| Delivery | [Charter](01-project-charter.md) (scope, success criteria) and the [product documents](../product/README.md) |
| Measurement | [Weekly Status Report](04-weekly-status-report.md) |
| Uncertainty | The risk table in the [Charter](01-project-charter.md#8-risks), re-read each week in the status report |

## Where the work lives

| What | System of record |
|------|------------------|
| Work items | GitHub issues, grouped in milestones, shown on the GitHub Project "Seatlock" |
| Technical decisions | ADRs in [docs/architecture/adr/](../architecture/adr/) |
| Architecture | The [C4 model](../architecture/README.md) |
| Scope, schedule, cost and plan changes | The [Change Request Log](05-change-request-log.md) |
| Status | The weekly report in [reports/](reports/) |

## Rhythm

| When | What |
|------|------|
| Every Friday | Write the weekly status report. Run `docs/pm/tools/weekly-data.sh` to get the numbers. |
| On every change | Log it as described in the [Change Request Workflow](05-change-request-log.md#workflow). |
| When a milestone closes | Update the schedule baseline's actuals and the changelog. |
| When a decision is hard to reverse | Write an ADR first. |

## What these documents are not

- They are not a claim about the book *Practical Project Management* by Dmytro Nizhebetskyi. The structure here is PMBOK 7, and the six documents are the ones the owner asked for. If the book has templates you prefer, the sections can be changed to match them.
- They are not a record of what was planned before 2026-10-20. Where the early history is reconstructed, the document says so.

## Approval

| Role | Name | Decision | Date |
|------|------|----------|------|
| Sponsor and project manager | Massimo Selvi | Pending | |
