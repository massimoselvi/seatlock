# Product Requirements Document (PRD)

| | |
|---|---|
| Product | Seatlock |
| Version | 1.0, issued 2026-10-23 |
| Owner | Massimo Selvi |
| Related | [Charter](../pm/01-project-charter.md), [Technical requirements](02-technical-requirements.md), [App flow](03-app-flow.md) |

## 1. Summary

Seatlock sells seats in workshops that have a limited number of places. Its one promise: **a seat is never sold twice**, even when many people press "Register" at the same moment. When a workshop is full, new people join a waitlist. When someone cancels, the oldest person waiting gets the seat.

## 2. Problem and goal

| | |
|---|---|
| Problem | Booking systems that read "seats left" and then write a booking oversell under load. Two people can both see one free seat. |
| Goal | A booking flow that stays correct under concurrent load, and that a reader can verify. |
| Not a goal | Payments, ticketing for money, a marketplace of organizers. |

## 3. Personas

| Persona | Needs | Pain today |
|---------|-------|------------|
| **Ada, attendee.** Wants to learn a skill and book a place quickly. | Know if a seat is free. Book in a few taps. Know her status. Cancel without penalty. | Books a seat, then is told it was sold out. Does not know if she is on a waitlist. |
| **Omar, organizer.** Runs workshops with a room of 20. | See seats taken, the waitlist and who registered. Trust the numbers. | Counts seats by hand. Two people arrive for one seat. |
| **Rita, reader.** Reviews the repository to judge engineering quality. | Find proof of the main claim fast. | Claims without evidence. |

## 4. Scope

**In.** Accounts, workshop list, registration, waitlist, cancellation with promotion, organizer dashboard, emails on promotion.
**Out.** Payments, email verification, password reset, social login, mobile apps, **creating workshops in the UI** (see open question Q1).

## 5. User stories

Priority uses MoSCoW: **M**ust, **S**hould, **C**ould, **W**on't (now).

| ID | As a | I want | So that | Priority |
|----|------|--------|---------|:--------:|
| US-01 | visitor | to see the list of workshops with seats left, without signing in | I can decide before I make an account | M |
| US-02 | visitor | to sign up with a username, email and password | I can register | M |
| US-03 | member | to sign in and out | my registrations are mine | M |
| US-04 | member | to register for a workshop | I get a seat | M |
| US-05 | member | to be placed on a waitlist when the workshop is full | I have a chance of a seat | M |
| US-06 | member | to cancel my registration | the seat goes to someone else | M |
| US-07 | member | to be promoted automatically, oldest first, and be told by email | I do not need to watch the page | M |
| US-08 | member | to press Register twice without harm | a double tap or a retry does not create a second booking | M |
| US-09 | organizer | to see seats taken, waitlist size and who registered | I can run the workshop | M |
| US-10 | member | to use the app in a dark theme and on a phone | I can use it anywhere | S |
| US-11 | organizer | to create and edit workshops in the app | I do not need the admin site | **C** (Q1) |
| US-12 | member | to see my own registrations | I know my status | S |
| US-13 | member | to reset my password | I can recover my account | W |

## 6. Functional requirements

| ID | Requirement | Story | Priority |
|----|-------------|-------|:--------:|
| FR-01 | `GET /api/workshops/` lists workshops with `seats_taken` and `seats_left`. It needs no sign-in. | US-01 | M |
| FR-02 | `POST /api/auth/signup/` creates a user and returns a token. It rejects a duplicate email and a weak password. | US-02 | M |
| FR-03 | `POST /api/auth/login/` returns a token for valid credentials. `POST /api/auth/logout/` deletes the token. `GET /api/auth/me/` returns the current user. | US-03 | M |
| FR-04 | `POST /api/workshops/{id}/register/` confirms the user when a seat is free and waitlists the user otherwise. It needs sign-in. | US-04, US-05 | M |
| FR-05 | The number of confirmed registrations of a workshop never exceeds its capacity. | US-04 | M |
| FR-06 | Registering again for the same workshop returns the existing registration and creates nothing. | US-08 | M |
| FR-07 | `POST /api/registrations/{id}/cancel/` cancels the user's own registration. Cancelling twice changes nothing. A user cannot cancel another user's registration (404). | US-06 | M |
| FR-08 | When a confirmed seat is freed, the oldest waitlisted registration becomes confirmed, after the cancellation is committed. | US-07 | M |
| FR-09 | The promoted user receives an email, sent after the transaction closes. | US-07 | M |
| FR-10 | `GET /api/registrations/` lists the signed-in user's own registrations. | US-12 | S |
| FR-11 | `GET /api/organizer/workshops/` and `.../{id}/registrations/` show seats, waitlist and attendees. Staff only. | US-09 | M |
| FR-12 | The UI shows a clear message and a way out for each error: wrong password, rate limit, workshop gone, network failure. | US-03, US-04 | S |
| FR-13 | The UI has a light and a dark theme, follows the system setting and remembers the choice. | US-10 | S |
| FR-14 | Workshops can be created in the UI. | US-11 | C |

## 7. Non-functional requirements

Detailed, measurable targets are in the [technical requirements](02-technical-requirements.md). In short:

| ID | Requirement | Measure |
|----|-------------|---------|
| NFR-01 | **Seat integrity.** No oversell under concurrency. | Exactly 10 confirmed for 10 seats after 200 simultaneous requests. 8 of 8 runs. |
| NFR-02 | Responsiveness | p95 list under 300 ms, p95 register and cancel under 800 ms |
| NFR-03 | Availability | 99.5% of requests are not 5xx |
| NFR-04 | Abuse resistance | Rate limits on login and registration |
| NFR-05 | Accessibility | Keyboard use, visible focus, labels, reduced motion, contrast in both themes |
| NFR-06 | Privacy | No personal data beyond username, email and a password hash |

## 8. Acceptance criteria and traceability

Each Must requirement names a test that fails when the requirement breaks.

| Requirement | Acceptance criterion | Test |
|-------------|----------------------|------|
| FR-01 | A visitor gets 200 and seats left | `tests/api/test_api.py::test_workshop_list_reports_seats_left`, `tests/api/test_auth.py::test_workshops_list_stays_public` |
| FR-02 | Duplicate email and weak password get 400 | `test_signup_rejects_duplicate_email`, `test_signup_rejects_weak_password` |
| FR-03 | Wrong password fails. `me` needs a token. Logout ends it. | `test_login_with_wrong_password`, `test_me_requires_token`, `test_me_and_logout` |
| FR-04 | Seats fill, then waitlist | `tests/api/test_registration_api.py::test_register_confirms_then_waitlists`, `tests/unit/application` `test_seats_fill_then_waitlist` |
| FR-05 | No oversell with threads, and over HTTP | `tests/integration/test_seat_allocation.py::test_concurrent_registrations_never_oversell`, `backend/scripts/load_test.py` |
| FR-06 | Idempotent | `test_register_is_idempotent` (API, integration and application) |
| FR-07 | Cancel is safe and private | `test_cancelling_twice_is_harmless`, `test_cannot_cancel_someone_elses_registration` |
| FR-08 | Oldest first, after commit | `test_promotion_goes_to_the_oldest_waiting_user_and_notifies_them`, `test_cancel_promotes_first_waiting_user` |
| FR-09 | Email after the transaction | `test_notifications_are_sent_after_the_transaction_closes` |
| FR-10 | Only my registrations | `test_list_returns_only_my_registrations` |
| FR-11 | Staff only, correct numbers | `tests/api/test_organizer_api.py` (4 tests) |
| FR-13 | Theme toggle | `frontend/src/components/ThemeToggle.test.ts` |
| NFR-04 | Throttling | `test_registration_endpoint_is_rate_limited`, `test_login_is_rate_limited` |

FR-12 has component tests for the main states. FR-14 is not built.

## 9. Success metrics

| Metric | Target | Source |
|--------|--------|--------|
| Confirmed seats after 200 requests for 10 seats | 10 in every run | Load test, [results](../load-test.md) |
| The same test without the lock | Fails (oversold) | Control run |
| Backend coverage | At least 95% | `pytest --cov` (now 98%) |
| Time for a reader to find the proof | Under 5 minutes | README links to the load test |

## 10. Release plan

See the [implementation plan](06-implementation-plan.md). Released: v0.1 to v0.5. In progress: v0.6 Hardening, baseline 2026-12-09.

## 11. Risks and assumptions

- A public demo before the hardening is done is a risk (charter R5).
- Assumption: no real user data is stored in any environment.
- Assumption: the organizer is a staff user created by an administrator.

## 12. Open questions

| # | Question | Owner | Needed by |
|---|----------|-------|-----------|
| Q1 | Should an organizer create workshops in the app (FR-14)? Today it takes the Django admin, which is turned off in AWS. Without it a public demo has no way to add data. | Sponsor | Before the first demo, phase E |
| Q2 | Should a waitlisted user be able to see their position? | Sponsor | v0.7 |
| Q3 | Should a promotion offer a time window to accept instead of being automatic? | Sponsor | Not planned |
