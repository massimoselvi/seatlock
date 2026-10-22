# Dynamic views: how the parts work together for one request.

dynamic api "flow-register" "Register for a workshop. Before this, the rate limit is checked and the composition root builds the use case. The lock is taken before any seat count is read. The cache is invalidated after the commit." {
    spa -> workshopsApi "POST /api/workshops/{id}/register/ with the token"
    workshopsApi -> registerUseCase "execute(user_id, workshop_id)"
    registerUseCase -> repositories "Locks the workshop"
    repositories -> database "SELECT ... FOR UPDATE"
    registerUseCase -> repositories "Finds an active registration, counts confirmed seats"
    registerUseCase -> entities "Which status does a new registration get?"
    registerUseCase -> repositories "Adds the registration"
    repositories -> database "INSERT"
    registerUseCase -> unitOfWork "Commits and runs the callbacks"
    unitOfWork -> database "COMMIT"
    unitOfWork -> listCache "Invalidates the list (after commit)"
    listCache -> redis "Bumps the version key"
    workshopsApi -> spa "200 with the registration"
    autolayout lr
}

dynamic api "flow-list" "Read the public list. The cache key carries a version, so one bump invalidates every page." {
    spa -> workshopsApi "GET /api/workshops/?page=1"
    workshopsApi -> listCache "Builds the key from the version and the page"
    listCache -> redis "Gets the cached page"
    workshopsApi -> queries "On a miss: queries the list"
    queries -> database "SELECT with seats_taken"
    workshopsApi -> listCache "Stores the page for 30 seconds"
    workshopsApi -> spa "200 with the page"
    autolayout lr
}

dynamic api "flow-signup" "Sign up. Accounts use Django's own auth and the rate limit for the auth scope." {
    spa -> accountsApi "POST /api/auth/signup/"
    accountsApi -> rateLimits "Checks the auth scope"
    rateLimits -> redis "Counts the request"
    accountsApi -> database "Creates the user and the token"
    accountsApi -> spa "201 with the token and the user"
    autolayout lr
}

dynamic seatlock "flow-cancel-promote" "Cancel a seat and promote the oldest waitlisted user. Everything after the commit goes through the queue." {
    attendee -> spa "Clicks Cancel"
    spa -> api "POST /api/registrations/{id}/cancel/"
    api -> database "Locks the workshop, marks the registration cancelled, commits"
    api -> redis "After commit: invalidates the list and queues promote_waitlist"
    api -> spa "200 with the registration"
    worker -> redis "Takes the promote_waitlist task from the queue"
    worker -> database "Locks the workshop, promotes the oldest waitlisted users, commits"
    worker -> redis "After commit: invalidates the list"
    worker -> email "Sends the promotion email"
    autolayout lr
}

dynamic seatlock "flow-load-test" "The load test: 200 simultaneous registrations for 10 seats, then a check of the database." {
    operator -> loadTest "Runs scripts/load_test.py"
    loadTest -> database "Creates users and workshops"
    loadTest -> api "Fires 200 requests at the same moment"
    api -> database "Locks, counts, inserts"
    api -> loadTest "200 answers"
    loadTest -> database "Reads the counts and checks the invariants"
    autolayout lr
}
