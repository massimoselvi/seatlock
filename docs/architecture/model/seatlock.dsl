# The system, its containers and the components inside the three that hold code.

seatlock = softwareSystem "Seatlock" "Workshops with limited seats. A seat is never sold twice, even when requests arrive at the same moment." {
    # The path is relative to this file. The ADRs are listed by hand in documentation/04-decisions.md:
    # the ADR importer reads our "Status:" line as Proposed and dates every ADR as today.
    !docs ../documentation

    spa = container "Single-page app" "Lists workshops, registers and cancels, shows the organizer dashboard. Light and dark theme." "Vue 3, TypeScript, Vite, UnoCSS" "Browser App" {
        url "https://github.com/massimoselvi/seatlock/tree/main/frontend"

        appShell = component "App shell" "Header, view switch for staff, loading and empty states, errors. Loads data and runs register and cancel." "Vue (App.vue)" "Frontend"
        authPanel = component "Auth panel" "Log in and sign up form." "Vue (AuthPanel.vue)" "Frontend"
        workshopList = component "Workshop list" "One card per workshop: date, seat meter, status badge, register and cancel buttons." "Vue (WorkshopCard, SeatMeter, StatusBadge)" "Frontend"
        dashboard = component "Organizer dashboard" "Seats taken, waitlist size and registrations with status filters." "Vue (OrganizerDashboard.vue)" "Frontend"
        themeToggle = component "Theme toggle" "Switches the dark theme. Follows the system setting first. The choice is kept in localStorage." "Vue, VueUse useDark" "Frontend"
        session = component "Session store" "The signed-in user and the token. The token is kept in localStorage." "TypeScript (session.ts)" "Frontend"
        apiClient = component "API client" "Typed fetch wrapper. Sends the token. Turns DRF errors into one readable line." "TypeScript (api.ts)" "Frontend"
    }

    api = container "API" "JSON API under /api/. Runs the register and cancel use cases and serves the reads." "Python 3.13, Django 6, Django REST Framework, gunicorn" "Backend" {
        url "https://github.com/massimoselvi/seatlock/tree/main/backend"

        group "interface/api: HTTP" {
            workshopsApi = component "Workshops API" "Public list (cached), register, the user's registrations, cancel." "DRF viewsets" "Interface" {
                url "https://github.com/massimoselvi/seatlock/tree/main/backend/interface/api/workshops"
            }
            organizerApi = component "Organizer API" "Staff only: seats taken, waitlist size, who registered." "DRF viewset" "Interface" {
                url "https://github.com/massimoselvi/seatlock/tree/main/backend/interface/api/organizer"
            }
            accountsApi = component "Accounts API" "Sign-up, login, logout, current user. Token authentication." "DRF views, Django auth" "Interface" {
                url "https://github.com/massimoselvi/seatlock/tree/main/backend/interface/api/accounts"
            }
            healthApi = component "Health endpoint" "Liveness check used by the load balancer." "Django view" "Interface"
            rateLimits = component "Rate limits" "Scoped throttles: registration, login and sign-up 10 a minute, anonymous 60, signed in 120." "DRF throttling" "Interface"
        }

        group "application: workflows" {
            registerUseCase = component "RegisterForWorkshop" "Locks the workshop, confirms a seat or joins the waitlist. Repeating it returns the same registration." "Python class" "Application" {
                url "https://github.com/massimoselvi/seatlock/blob/main/backend/application/workshops/services.py"
            }
            cancelUseCase = component "CancelRegistration" "Cancels a registration. A freed seat queues a waitlist promotion after commit." "Python class" "Application" {
                url "https://github.com/massimoselvi/seatlock/blob/main/backend/application/workshops/services.py"
            }
            promoteUseCase = component "PromoteWaitlist" "Fills free seats from the waitlist, oldest first. Emails the people promoted after the transaction closes." "Python class" "Application" {
                url "https://github.com/massimoselvi/seatlock/blob/main/backend/application/workshops/services.py"
            }
            ports = component "Ports" "What the use cases need from outside: unit of work, repositories, list cache, promotion queue, notifier." "Python abstract classes" "Application" {
                url "https://github.com/massimoselvi/seatlock/blob/main/backend/application/workshops/interfaces.py"
            }
        }

        group "domain: business rules" {
            entities = component "Seat rules" "Workshop and Registration entities: free seats, the status of a new registration, who gets promoted, legal status changes." "Plain Python, standard library only" "Domain" {
                url "https://github.com/massimoselvi/seatlock/blob/main/backend/domain/workshops/entities.py"
            }
        }

        group "infrastructure: Django, Celery, Redis, email" {
            compositionRoot = component "Composition root" "The one place that picks concrete classes. Builds a fresh use case with its own unit of work for each call." "Python (container.py)" "Infrastructure" {
                url "https://github.com/massimoselvi/seatlock/blob/main/backend/infrastructure/container.py"
            }
            unitOfWork = component "Unit of work" "One transaction. Commits on success, rolls back on error, runs callbacks after the commit." "Django transaction.atomic, on_commit" "Infrastructure"
            repositories = component "Repositories" "Load and save entities. The workshop lock is SELECT ... FOR UPDATE." "Django ORM" "Infrastructure"
            queries = component "Read queries" "Annotated querysets for the public list and the organizer dashboard." "Django ORM" "Infrastructure"
            models = component "ORM models and migrations" "Tables workshops_workshop and workshops_registration. Constraints: capacity above 0, one active registration per user and workshop." "Django models" "Infrastructure"
            listCache = component "List cache" "Versioned cache keys for the public list. Invalidated after commit." "Django cache" "Infrastructure"
            queueAdapter = component "Promotion queue" "Sends the promote_waitlist task to the queue." "Celery" "Infrastructure"
            notifier = component "Email notifier" "Sends the promotion email." "Django send_mail" "Infrastructure"
            adminSite = component "Django admin" "Staff edits rows directly. This bypasses the use cases and the lock. Off in AWS." "Django admin" "Infrastructure,Bypass"
        }
    }

    worker = container "Worker" "Promotes the oldest waitlisted users after a seat is freed and emails them. Same image as the API." "Python, Celery" "Backend,Async" {
        promoteTask = component "promote_waitlist task" "Runs the PromoteWaitlist use case for one workshop. The task name is kept so queued messages stay valid." "Celery shared_task" "Async"
        sharedCode = component "Shared backend code" "The same application and infrastructure code as the API: composition root, use case, repositories, notifier." "Python" "Async"
    }

    database = container "Database" "Workshops, registrations, users and tokens. Row locks serialize seat changes. Constraints back up the rules." "PostgreSQL 17" "Database"
    redis = container "Cache and broker" "Cached workshop list, throttle counters and the Celery queue." "Redis" "Database,Cache"
    loadTest = container "Load test" "Sends 200 simultaneous registrations for 10 seats over HTTP and checks the database. Developer tool, run by hand or in CI." "Python script" "Tooling"
}
