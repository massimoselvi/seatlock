# Level 2: containers.

container seatlock "containers" "Level 2. What runs, and how the parts talk to each other." {
    include attendee organizer spa api worker database redis email
    autolayout tb
}

container seatlock "containers-async" "The path through the queue: a freed seat promotes the oldest waitlisted user." {
    include spa api worker database redis email
    exclude "relationship.tag!=Async"
    autolayout lr
}

container seatlock "containers-all" "Everything, including the load test tool and the people who run it." {
    include *
    autolayout tb
}
