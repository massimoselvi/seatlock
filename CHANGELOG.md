# Changelog

Format follows [Keep a Changelog](https://keepachangelog.com/). Versions follow milestones.

## [Unreleased]

### Security

- API 403 and 404 answers are no longer replaced by the single-page app in CloudFront (ADR 0007)
- The ALB serves only requests that carry a CloudFront secret header
- CSP, HSTS and other security headers on the site and the API
- API tokens expire (`AUTH_TOKEN_TTL_HOURS`, default 168 hours); sign-in is limited per username too
- Immutable ECR tags; `image_tag` is required
- Production: WAF managed rules (count mode first), ALB access logs, Redis AUTH token, `sslmode=require` for PostgreSQL
- Production answers JSON only; compose publishes PostgreSQL on 127.0.0.1 only

### Fixed

- Non-numeric ids in `register` and `cancel` returned 500; they now return 404
- A new user could take a seat freed by a cancellation ahead of the waitlist
- Promotion and email tasks retry with backoff; each email is its own task

### Changed

- Registering for a workshop that has started returns 409

## [0.1.0] - Foundation

### Added

- Workshop and Registration models with database constraints
- Seat allocation and waitlist promotion services
- Read-only workshops API
- Vue 3 workshops list page
- Docker Compose stack
- CI with lint, migration check and tests
