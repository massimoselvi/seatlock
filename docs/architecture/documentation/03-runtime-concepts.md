## Runtime concepts

### Concurrency

Two requests for the last seat arrive together. Both open a transaction. Both ask for `SELECT ... FOR UPDATE` on the workshop row. PostgreSQL grants it to one and makes the other wait. The first counts the seats, inserts its registration and commits. The second then counts again and sees the seat taken, so it joins the waitlist.

See the dynamic view **flow-register**, and `docs/load-test.md` for the measured result.

### After the commit

Everything that leaves the database happens after the commit: the cache invalidation, the queue message and the email. A rolled-back request therefore changes nothing outside PostgreSQL.

### Caching

The public list is cached in Redis. The cache key carries a version number. One bump after a commit makes every cached page unreachable at once. See **flow-list**.

### Rate limits

Register and cancel take a row lock, so they are limited per user (10 a minute). Login and sign-up are limited too. The counters live in Redis, so all web workers share them.

### Environments

The same containers run in four places: Docker Compose, the AWS demo, the AWS production-like setup and GitHub Actions (the load test). See the deployment views.
