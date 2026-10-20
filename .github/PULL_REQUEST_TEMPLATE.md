## What and why

<!-- One or two sentences. Say why the change is needed. -->

Closes #

## How to test

<!-- Commands or steps a reviewer can run. -->

## Checklist

- [ ] Acceptance criteria in the issue are met
- [ ] Tests added or updated
- [ ] Business rules are in `services.py`, not in views
- [ ] Seat-count changes lock the Workshop row and have a concurrency test
- [ ] Migrations included and `makemigrations --check` is clean
- [ ] Docs or ADR updated if a decision changed

## Risk and rollback

<!-- What can break? How do we revert? -->
