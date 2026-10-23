# Weekly PM Status Report

| | |
|---|---|
| Version | 1.0, issued 2026-10-23 |
| Owner | Project manager |
| Cadence | Every Friday, one report a week |
| Reports | [reports/](reports/): the first is [2026-W43](reports/2026-W43.md) |

A status report has one job: let the sponsor decide with facts. It is short, it compares the **plan with the facts**, and it ends with what the sponsor must decide.

## 1. How to write one

1. Collect the facts. Do not type numbers from memory.

   ```bash
   docs/pm/tools/weekly-data.sh <from-date> <to-date>      # pull requests, issues, milestones, commits, CI
   docker compose run --rm web pytest -q --cov=.           # backend tests and coverage
   cd frontend && pnpm run ci                              # frontend checks
   cd infra && uv run pytest -q                            # infra tests
   ```

2. Copy the template below to `reports/YYYY-Www.md`, with the ISO week number.
3. Fill it from the facts. Say what is **not known** instead of guessing.
4. Record the hours spent. They give the cost performance index (CPI) in the [baseline](03-estimates-and-schedule-baseline.md#6-baseline-control).
5. Re-read the risk table of the [charter](01-project-charter.md#8-risks) and update the scores.
6. Commit the report on a branch and merge it by pull request, like any other change.

## 2. Status colors

| Color | Meaning |
|-------|---------|
| **Green** | On the baseline. Nothing needs the sponsor. |
| **Amber** | A deviation exists and the recovery is known and within the reserve. The sponsor is informed. |
| **Red** | The baseline cannot be met without a decision. A [change request](05-change-request-log.md) is raised. |

The thresholds for schedule are in the [baseline](03-estimates-and-schedule-baseline.md#6-baseline-control). Cost is red above the cap. Quality is red when a check on `main` fails and is not fixed the same day.

## 3. Template

```markdown
# Status report: <YYYY-Www>

| | |
|---|---|
| Period | <from> to <to> |
| Report date | <date> |
| Overall | <Green | Amber | Red>: <one sentence why> |

| Area | Status | Note |
|------|--------|------|
| Scope | | |
| Schedule | | |
| Cost | | |
| Quality | | |
| Risk | | |

## Summary
<Three or four sentences. What happened, what matters, what is needed.>

## Done this period
<Grouped by theme, with pull request and issue numbers.>

## Measures
| Measure | Plan | Actual |
|---------|-----:|-------:|
| Earned hours (packages closed) | | |
| Hours spent | | |
| SPI, CPI | | |
| Issues closed, opened | | |
| Pull requests merged | | |
| Tests (backend, frontend, infra) and coverage | | |
| Cloud spend against the cap | | |

## Next period
<The packages the baseline schedules, by ID.>

## Milestones
<Planned and forecast dates. Mark any that moved.>

## Risks and issues
| ID | Risk or issue | Score | Change | Action |
|----|---------------|:-----:|--------|--------|

## Changes
<Change requests raised or decided this period.>

## Decisions needed
<Numbered. Each one says who decides and by when.>
```

## 4. Rules

- **Facts before opinion.** Every number comes from a command or a link.
- **One page.** If it grows, the detail belongs in the issue, not the report.
- **Name the variance.** "Two days late because the AWS login was not active" is a report. "Some delay" is not.
- **No hidden changes.** Anything that changed scope, schedule, cost or architecture is listed under Changes, with its CR number.
- **Honest unknowns.** If a measure was not collected, write "not recorded" and fix the collection.
