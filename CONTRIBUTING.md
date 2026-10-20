# Contributing

This project uses trunk-based development. `main` is always releasable.

## Workflow

1. Pick an issue. Every change starts from an issue with acceptance criteria.
2. Create a short-lived branch from `main`: `feat/…`, `fix/…`, `chore/…`, `docs/…`, `test/…`, `build/…`, `ci/…`.
3. Make small commits. Use [Conventional Commits](https://www.conventionalcommits.org/): `feat(workshops): add waitlist promotion`.
4. Open a pull request. Link the issue with `Closes #n`.
5. Wait for green checks and one approval. Merge with a merge commit.

Direct pushes, force pushes and deletion of `main` are blocked by a repository ruleset.

## Review SLA

- A reviewer gives a first response within **24 hours** on working days.
- The author answers review comments within 24 hours.
- Keep pull requests under about 400 changed lines. Large changes wait longer for a review.
- Findings use three tags: **Blocker** (must fix), **Suggestion** (should consider), **Nitpick** (optional).
  Only a Blocker stops a merge.

## Definition of done

- Acceptance criteria in the issue are met.
- Tests cover the new behavior. Seat-count changes have a concurrency test.
- `ruff check`, `ruff format --check`, `makemigrations --check` and `pytest` pass.
- `pnpm build` passes for frontend changes.
- Docs and ADRs are updated when a decision changes.

## Architecture decisions

A decision that is hard to reverse needs an ADR in `docs/adr/`. Number the files in order: `0001-title.md`.
An ADR states the context, the decision, the alternatives and the consequences.

## Local setup

See the [README](README.md).
