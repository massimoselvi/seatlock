# 7. Harden the edge and API tokens

Date: 2026-10-23

## Status

Accepted

## Context

A security audit on 2026-10-23 found these gaps:

- CloudFront replaced API 403 and 404 answers with `200 index.html`. The client read a denial as a success.
- The CloudFront address list that the ALB allows covers every CloudFront customer. Any distribution could reach the ALB.
- API tokens never expired. The site sent no CSP, HSTS or other security headers.
- Sign-in was limited per address only, and a task image tag could move (`latest`).

## Decision

1. **No distribution-wide error page.** A CloudFront Function on the site behavior rewrites paths without a dot to `/index.html`. The `/api/*` behavior keeps its real status codes. The client also rejects a `200` answer that is not JSON.
2. **Origin verification.** CloudFront adds `X-Origin-Verify` with a random value from Secrets Manager. The ALB default action is a 403. Only requests with the header are forwarded.
3. **Security headers.** One CloudFront response headers policy sets CSP, HSTS, `nosniff`, `X-Frame-Options` and a referrer policy. The CSP allows no inline script. The theme script moved to `public/theme-init.js`.
4. **Token lifetime.** `ExpiringTokenAuthentication` rejects tokens older than `AUTH_TOKEN_TTL_HOURS` (default 168). Sign-in replaces an expired token and reuses a live one.
5. **Sign-in limits per username** (10 per minute) on top of the per-address limit.
6. **Immutable image tags.** The ECR repository is immutable and `image_tag` is required, except for the bootstrap deploy.
7. **Production only:** AWS WAF on the ALB with two managed rule groups (known bad inputs, common rules), ALB access logs and ALB deletion protection. The WAF starts in count mode. After a week of metrics with no false positives, set `waf_block=True` in `config.py`. The IP reputation group is left out: the ALB sees CloudFront addresses, not viewer addresses.
8. **Data in transit:** Redis requires an AUTH token and PostgreSQL connections use `sslmode=require`.

## Alternatives

- **HTTPS between CloudFront and the ALB.** Better, but it needs a domain and a certificate (issue #47). The secret header is the interim control.
- **WAF on CloudFront.** It sees the viewer address, so it supports rate rules and IP reputation. It must live in `us-east-1`, which means a second stack and region. This is the better design and is tracked as a follow-up. A rate rule on the ALB sees only CloudFront addresses, and the forwarded-IP key can be spoofed. Until then, rate limits stay in the application.
- **httpOnly session cookie instead of a token in `localStorage`.** It removes token theft by script, but it adds CSRF handling and a larger change to the client. The CSP and short lifetime reduce the risk for now.

## Consequences

- The secret and the Redis token appear in the CloudFormation template as dynamic references, not as plain text. Anyone who can read the secret can bypass the origin check.
- Rotating the origin secret needs two steps, to avoid a window of 403 answers. Accept both values on the ALB, then change CloudFront.
- A user who knows a victim's username can block their sign-in for a minute at a time. The per-address limit has the same weakness. Accept this for now.
- DRF stores tokens in plain text in the database. This is unchanged.
- Not done: read-only root filesystem for tasks, rotation of the database secret, pinning base images and Actions by digest.
