## Overview

Seatlock sells seats for workshops with limited capacity. The one promise it makes is that **a seat is never sold twice**, even when many people press "register" at the same moment.

### Who uses it

- **Attendees** browse workshops, register, join a waitlist when a workshop is full, and cancel.
- **Organizers** are staff. They see seats taken, the waitlist size and who registered.
- **Operators** ship releases and answer alarms.

### Quality goals

| Goal | How the design serves it |
|------|--------------------------|
| Seats are never oversold | Each seat change locks the workshop row in PostgreSQL. The decisions are plain Python and tested without a database. |
| Easy to explain and change | Four layers, dependencies pointing inward, one test that enforces it. |
| Cheap to run | A small demo costs about 0.12 to 0.16 an hour. It is destroyed when not in use. |
| Provable | A load test sends 200 simultaneous registrations for 10 seats and checks the database. |

### Where to read more

The repository holds the rest: `docs/architecture.md` (flows and diagrams in Mermaid), the ADRs, `docs/load-test.md`, `docs/deploy.md` and the runbooks.
