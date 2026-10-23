# App Flow

| | |
|---|---|
| Version | 1.0, issued 2026-10-23 |
| Owner | Massimo Selvi |
| Related | [PRD](01-prd.md), [UX brief](04-ux-design-brief.md), [Architecture guide](../architecture.md) |

The app is a single page. There are no routes: the page shows the workshop list, and staff can switch to the organizer dashboard. The sign-in panel replaces the list for visitors who are not signed in.

## 1. Screen map

```mermaid
flowchart TD
    Start([Open the app]) --> Boot{Token in<br/>local storage?}
    Boot -- No --> Auth[Sign-in panel and public list]
    Boot -- Yes --> Me[GET /api/auth/me/]
    Me -- 200 --> List
    Me -- 401 --> Clear[Clear token] --> Auth
    Auth -- log in or sign up --> List[Workshop list]
    List -- staff only --> Org[Organizer dashboard]
    Org -- Workshops tab --> List
    List -- Log out --> Auth
    Org -- Log out --> Auth
```

| Screen | Who sees it | Content |
|--------|-------------|---------|
| Sign-in panel | Visitor | Log in or create an account. Switch link between the two. |
| Workshop list | Member, staff | Cards with title, time, seats left, status of my registration, Register, Join waitlist or Cancel. |
| Organizer dashboard | Staff | Per workshop: seats taken, waitlist size, list of registrations. |

A visitor sees the sign-in panel **above** the workshop list. The list is public in the API, so a visitor can read seats before making an account. Register, Join waitlist and Cancel appear only after sign-in.

## 2. Sign-up and log-in

```mermaid
sequenceDiagram
    actor U as User
    participant UI as Vue app
    participant API as Django API
    U->>UI: Fill username, email, password
    UI->>API: POST /api/auth/signup/ (or login/)
    alt Valid
        API-->>UI: 201 (or 200) token and user
        UI->>UI: Store token, load workshops
    else Duplicate email, weak password, wrong password
        API-->>UI: 400 field errors
        UI-->>U: Message under the form (role alert)
    else Too many attempts
        API-->>UI: 429
        UI-->>U: "Request was throttled" with wait time
    end
```

## 3. Register for a workshop

```mermaid
sequenceDiagram
    actor U as Member
    participant UI as Vue app
    participant API as Interface (view)
    participant UC as Use case
    participant DB as PostgreSQL
    U->>UI: Press Register
    UI->>API: POST /api/workshops/{id}/register/
    API->>UC: register_for_workshop(user, workshop)
    UC->>DB: BEGIN, lock workshop row
    UC->>DB: read seats taken, existing registration
    alt Already registered
        UC-->>API: the existing registration
    else Seat free
        UC->>DB: insert confirmed
    else Full
        UC->>DB: insert waitlisted
    end
    UC->>DB: COMMIT
    UC-->>API: result
    Note over UC: After commit: invalidate the list cache
    API-->>UI: 200 id, status
    UI-->>U: "You have a seat" or "You are on the waitlist"
```

Two people press Register on the last seat at the same moment: both requests reach step "lock workshop row". The database lets one pass. The second waits, then sees zero seats and is waitlisted. This is the proof the [load test](../load-test.md) checks.

## 4. Cancel and promotion

```mermaid
sequenceDiagram
    actor U as Member
    participant UI as Vue app
    participant UC as Cancel use case
    participant DB as PostgreSQL
    participant Q as Celery worker
    participant M as Email
    U->>UI: Press Cancel
    UI->>UC: POST /api/registrations/{id}/cancel/
    UC->>DB: BEGIN, lock workshop, set cancelled
    UC->>DB: COMMIT
    Note over UC,Q: After commit
    UC->>Q: enqueue workshops.tasks.promote_waitlist
    UC-->>UI: 200 cancelled
    Q->>DB: lock workshop, confirm the oldest waitlisted
    Q->>M: email the promoted member
    Note over UI: The promoted member sees "You have a seat" on the next load
```

## 5. Registration states

```mermaid
stateDiagram-v2
    [*] --> confirmed: register, seat free
    [*] --> waitlisted: register, workshop full
    waitlisted --> confirmed: promoted, a seat was freed
    confirmed --> cancelled: cancel
    waitlisted --> cancelled: cancel
    cancelled --> [*]
```

`confirmed` and `waitlisted` are **active**. A user can have only one active registration per workshop. After `cancelled`, the user can register again, which creates a new row.

## 6. Organizer flow

```mermaid
flowchart LR
    S([Staff signs in]) --> V[Switch to Organizer view]
    V --> L[GET /api/organizer/workshops/]
    L --> C[Cards: seats taken, waitlist size]
    C --> R[Open one: GET .../registrations/]
    R --> T[Table: who, status, when]
    T --> V
```

A non-staff user who calls these endpoints gets 403. The nav item is hidden for them.

## 7. Screen states

| Screen | Loading | Empty | Error | Success |
|--------|---------|-------|-------|---------|
| Workshop list | Three pulsing placeholder cards, `aria-busy` | Inbox icon and "No workshops yet. Check back soon." | Banner with `role="alert"` | Cards |
| Card action | Button disabled while the call runs | n/a | Message under the card | Status text changes, `aria-live` announces it |
| Sign-in panel | Button disabled | n/a | Message under the form | Panel closes |
| Organizer dashboard | Placeholder | "No registrations" | Banner | Numbers and table |

## 8. Error paths

| Case | HTTP | What the user sees | What the user can do |
|------|:----:|--------------------|----------------------|
| Wrong password | 400 | The API message | Retry |
| Duplicate email on sign-up | 400 | The API message | Log in instead |
| Too many attempts | 429 | "Request was throttled. Expected available in N seconds." | Wait |
| Token expired or removed | 401 | Back to the sign-in panel | Log in |
| Workshop deleted meanwhile | 404 | "Workshop not found." | Reload the list |
| Cancel someone else's registration | 404 | "Registration not found." | None. The UI never offers it. |
| Not staff on the organizer API | 403 | Dashboard is not offered | None |
| Network down or server error | 5xx | "Something went wrong" | Retry |

## 9. Cross-cutting rules

- The token is kept in local storage under `seatlock.token`. Logging out deletes it on the server and in the browser.
- A double press is safe: registering twice returns the same registration (FR-06).
- The list is cached for 30 s on the server and is dropped when seats change. A refresh may therefore show a count that is a few seconds old after a change by someone else, never after your own action.
