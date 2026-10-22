# Runbook: seats oversold

**Trigger:** the oversold check finds a workshop with more confirmed registrations than capacity.
This must never happen. Treat it as a Sev 1 incident.

## 1. Confirm

```sql
SELECT w.id, w.title, w.capacity, COUNT(*) AS confirmed
FROM workshops_workshop w
JOIN workshops_registration r ON r.workshop_id = w.id AND r.status = 'confirmed'
GROUP BY w.id
HAVING COUNT(*) > w.capacity;
```

## 2. Contain

- Stop new registrations for the workshop. Set capacity to the current confirmed count in the admin, or disable the register endpoint at the load balancer.
- Do not delete rows. Keep the data for the investigation.

## 3. Investigate

- Check recent deploys. Does every path that changes seat counts still lock the workshop first (`DjangoWorkshopRepository.lock`) inside a unit of work? See [ADR 0001](../architecture/adr/0001-row-locks-for-seat-allocation.md).
- Look for writes that bypass the use cases in `application/workshops/services.py`: admin actions, shell sessions, data fixes.
- Check that the database is not behind a pooler in statement mode, which breaks row locks.

## 4. Recover

1. Choose who keeps a seat: the oldest registrations by `created_at`.
2. Move the rest to `waitlisted` with a data fix reviewed by a second person.
3. Email the affected users.

## 5. Follow up

Write a blameless postmortem. Add a regression test that reproduces the cause.
